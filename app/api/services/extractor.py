"""
提取器服务模块
包含模型管理、异步任务处理等核心业务逻辑
"""

import os
import gc
import json
import uuid
import threading
import time
import queue
import torch
from datetime import datetime
from pathlib import Path
from functools import lru_cache
from werkzeug.utils import secure_filename
import concurrent.futures
import shutil
from fastapi import HTTPException

# 导入我们的提取器
from ...openchemie.extractor import OpenChemIEExtractorV2

# 全局变量
model_manager = None
executor = None
task_status = {}
task_status_lock = threading.Lock() # 引入一个锁

class ModelManager:
    """模型管理器 - 单例模式"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.models = {}
            self._model_lock = threading.Lock()
            self._initialized = True
    
    def get_model(self, device='auto'):
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        with self._model_lock:
            if device not in self.models:
                print(f"📱 初始化模型 (设备: {device})...")
                self.models[device] = OpenChemIEExtractorV2(device=device)
                if device == 'cuda' and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            return self.models[device]
    
    def cleanup_models(self):
        with self._model_lock:
            for device, model in self.models.items():
                del model
                if device == 'cuda' and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            self.models.clear()
            gc.collect()

def cleanup_memory():
    """清理内存"""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def create_result_summary(results):
    """创建结果摘要"""
    try:
        stats = results.get('statistics', {})
        return {
            'summary': stats.get('document_overview', {}),
            'quality': results.get('quality_metrics', {}).get('overall_score', 0),
            'processing_time': results.get('metadata', {}).get('extraction_info', {}).get('processing_time_seconds', 0),
            'entities_count': {
                'molecules': len(results.get('chemical_entities', {}).get('molecules', {})),
                'reactions': len(results.get('chemical_entities', {}).get('reactions', {})),
                'figures': len(results.get('document_content', {}).get('figures', {})),
                'tables': len(results.get('document_content', {}).get('tables', {}))
            }
        }
    except:
        return {}

def update_batch_status(batch_id, task_status_dict):
    """更新批处理任务的总体状态（线程安全）"""
    with task_status_lock:
        if batch_id in task_status_dict and task_status_dict[batch_id]['type'] == 'batch':
            batch_task = task_status_dict[batch_id]
            
            completed_count = 0
            failed_count = 0
            
            for task_id, subtask_info in batch_task['subtasks'].items():
                # 从主状态字典获取最新的子任务状态
                subtask_status = task_status_dict.get(task_id, {}).get('status')
                if subtask_status:
                    batch_task['subtasks'][task_id]['status'] = subtask_status

                if subtask_status == 'completed':
                    completed_count += 1
                elif subtask_status == 'error' or subtask_status == 'failed': # 假设 'error' 和 'failed' 都是失败状态
                    failed_count += 1
            
            batch_task['completed_files'] = completed_count
            batch_task['failed_files'] = failed_count
            
            if (completed_count + failed_count) == batch_task['total_files']:
                batch_task['status'] = 'completed'
                batch_task['completion_time'] = datetime.now().isoformat()

def extract_task_optimized(task_id, pdf_path, options, task_status_dict, results_folder):
    """优化的提取任务处理"""
    batch_id = None
    try:
        with task_status_lock:
            task_status_dict[task_id]['status'] = 'processing'
            task_status_dict[task_id]['message'] = '正在获取模型...'
            batch_id = task_status_dict[task_id].get('batch_id')

        device = options.get('device', 'auto')
        extractor = model_manager.get_model(device)
        
        task_status_dict[task_id]['message'] = '正在提取化学信息...'
        
        results = extractor.extract_from_pdf(
            pdf_path,
            output_images=options.get('output_images', False),
            output_bbox=options.get('output_bbox', True),
            extract_corefs=options.get('extract_corefs', False)
        )
        
        result_file = os.path.join(results_folder, f"{task_id}_results.json")
        # 保存结果到文件
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        summary_results = create_result_summary(results)
        
        task_status_dict[task_id].update({
            'status': 'completed',
            'message': '提取完成',
            'result_file': result_file,
            'results': summary_results,
            'completion_time': datetime.now().isoformat()
        })
        
        del results
        cleanup_memory()
        
    except Exception as e:
        with task_status_lock:
            task_status_dict[task_id]['status'] = 'failed' # 使用 'failed' 状态
            task_status_dict[task_id]['error'] = f'提取失败: {str(e)}' # 添加 error 字段
            batch_id = task_status_dict[task_id].get('batch_id')
        cleanup_memory()
    finally:
        # 确保总会更新批处理状态
        if batch_id:
            update_batch_status(batch_id, task_status_dict)
            
        # 清理上传的文件
        try:
            os.remove(pdf_path)
        except:
            pass

def task_worker(task_queue, task_status_dict, results_folder):
    """任务工作线程"""
    while True:
        try:
            task_data = task_queue.get(timeout=1)
            if task_data is None:
                break
            task_id, pdf_path, options = task_data
            extract_task_optimized(task_id, pdf_path, options, task_status_dict, results_folder)
            task_queue.task_done()
        except queue.Empty:
            continue

def initialize_queue_and_workers(settings, task_status_dict):
    """初始化任务队列和工作线程池"""
    global model_manager, executor
    
    # 创建模型管理器
    model_manager = ModelManager()

    # 创建任务队列
    task_queue = queue.Queue(maxsize=settings.task_queue_size)

    # 创建线程池
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=settings.max_concurrent_tasks,
        thread_name_prefix='Extractor'
    )

    # 启动工作线程
    for i in range(settings.max_concurrent_tasks):
        executor.submit(worker, task_queue, model_manager, task_status_dict, settings.results_folder)
    
    print(f"✅ {settings.max_concurrent_tasks} 个工作线程已启动")
    return task_queue # 返回队列实例

def submit_task(pdf_file, options, task_status_dict, upload_folder, results_folder, task_queue, batch_id=None):
    """
    将提取任务提交到队列
    
    返回:
        str: 任务ID
    """
    if task_queue is None:
        raise ValueError("任务队列未初始化")

    task_id = str(uuid.uuid4())
    filename = f"{task_id}_{secure_filename(pdf_file.filename)}"
    pdf_path = os.path.join(upload_folder, filename)
    
    # 保存上传的文件
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(pdf_file.file, buffer)
    
    # 准备任务详情
    task_details = {
        'id': task_id,
        'type': 'single', # 添加类型字段
        'batch_id': batch_id, # 添加 batch_id
        'filename': pdf_file.filename,
        'saved_path': pdf_path,
        'options': options,
        'status': 'queued',
        'submitted_at': datetime.now().isoformat(),
        'result': None,
        'error': None
    }
    
    # 将任务放入队列
    try:
        task_queue.put_nowait((task_id, pdf_path, options))
        with task_status_lock:
            task_status_dict[task_id] = task_details
        print(f"✅ 任务 {task_id} 已提交到队列 (批处理: {batch_id or '无'})")
        return task_id
    except queue.Full:
        raise HTTPException(status_code=503, detail="服务正忙，任务队列已满，请稍后再试")

def worker(task_queue, model_manager, task_status_dict, results_folder):
    """任务工作线程"""
    while True:
        try:
            task_data = task_queue.get(timeout=1)
            if task_data is None:
                break
            task_id, pdf_path, options = task_data
            extract_task_optimized(task_id, pdf_path, options, task_status_dict, results_folder)
            task_queue.task_done()
        except queue.Empty:
            continue

def cleanup_old_tasks(task_status_dict, max_age_hours=24, force=False):
    """清理旧任务"""
    cleanup_count = 0
    now = datetime.now()
    for task_id, data in list(task_status_dict.items()):
        upload_time_str = data.get('upload_time')
        if upload_time_str:
            upload_time = datetime.fromisoformat(upload_time_str)
            age = now - upload_time
            if age.total_seconds() > max_age_hours * 3600 or force:
                result_file = data.get('result_file')
                if result_file and os.path.exists(result_file):
                    os.remove(result_file)
                del task_status_dict[task_id]
                cleanup_count += 1
    return cleanup_count 