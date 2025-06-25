#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChemIE Web界面 - 性能优化版
基于Flask的前端应用，方便使用化学信息提取工具
"""

import os
import json
import uuid
import shutil
import gc
import torch
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import threading
import time
import queue
import concurrent.futures
from functools import lru_cache

# 导入我们的提取器
import sys
# 将项目根目录添加到Python路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openchemie_extractor_v2 import OpenChemIEExtractorV2

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生产环境中请更改此密钥

# 获取app.py所在的目录
_basedir = os.path.abspath(os.path.dirname(__file__))

# 配置
UPLOAD_FOLDER = os.path.join(_basedir, 'uploads')
RESULTS_FOLDER = os.path.join(_basedir, 'results')
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# 性能优化配置
MAX_CONCURRENT_TASKS = 2
TASK_QUEUE_SIZE = 10
CACHE_SIZE = 100

# 创建必要的目录
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# 全局变量
task_status = {}
task_queue = queue.Queue(maxsize=TASK_QUEUE_SIZE)
processing_threads = {}

# 全局模型单例管理
class ModelManager:
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
                self.models[device] = OpenChemIEExtractorV2(device=device, verbose=False)
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

model_manager = ModelManager()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@lru_cache(maxsize=CACHE_SIZE)
def get_cached_results(task_id):
    if task_id in task_status and task_status[task_id].get('status') == 'completed':
        return task_status[task_id].get('results')
    return None

def cleanup_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def extract_task_optimized(task_id, pdf_path, options):
    try:
        task_status[task_id]['status'] = 'processing'
        task_status[task_id]['message'] = '正在获取模型...'
        
        device = options.get('device', 'auto')
        extractor = model_manager.get_model(device)
        
        task_status[task_id]['message'] = '正在提取化学信息...'
        
        results = extractor.extract_from_pdf(
            pdf_path,
            output_images=options.get('output_images', False),
            output_bbox=options.get('output_bbox', True),
            extract_corefs=options.get('extract_corefs', False)
        )
        
        result_file = os.path.join(RESULTS_FOLDER, f"{task_id}_results.json")
        extractor.save_results(results, result_file)
        
        summary_results = create_result_summary(results)
        
        task_status[task_id].update({
            'status': 'completed',
            'message': '提取完成',
            'result_file': result_file,
            'results': summary_results,
            'completion_time': datetime.now().isoformat()
        })
        
        del results
        cleanup_memory()
        
        try:
            os.remove(pdf_path)
        except:
            pass
            
    except Exception as e:
        task_status[task_id]['status'] = 'error'
        task_status[task_id]['message'] = f'提取失败: {str(e)}'
        cleanup_memory()

def create_result_summary(results):
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

def task_worker():
    while True:
        try:
            task_data = task_queue.get(timeout=1)
            if task_data is None:
                break
            task_id, pdf_path, options = task_data
            extract_task_optimized(task_id, pdf_path, options)
            task_queue.task_done()
        except queue.Empty:
            continue

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon_ico():
    return send_file(os.path.join(app.root_path, 'static', 'favicon.svg'), mimetype='image/svg+xml')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        task_id = str(uuid.uuid4())
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(upload_path)
        
        options = {
            'device': request.form.get('device', 'auto'),
            'output_images': request.form.get('output_images') == 'true',
            'output_bbox': request.form.get('output_bbox') == 'true',
            'extract_corefs': request.form.get('extract_corefs') == 'true'
        }
        
        task_status[task_id] = {
            'status': 'queued',
            'message': '任务已进入队列',
            'filename': filename,
            'upload_time': datetime.now().isoformat(),
            'start_time': None,
            'completion_time': None,
            'options': options
        }
        
        try:
            task_queue.put_nowait((task_id, upload_path, options))
            return jsonify({'task_id': task_id})
        except queue.Full:
            os.remove(upload_path)
            return jsonify({'error': '服务器正忙，请稍后再试'}), 503
            
    return jsonify({'error': '文件类型不允许'}), 400

@app.route('/status/<task_id>')
def get_task_status(task_id):
    status_info = task_status.get(task_id, {'status': 'not_found', 'message': '任务ID不存在'})
    return jsonify(status_info)

@app.route('/results/<task_id>')
def view_results(task_id):
    if task_id in task_status and task_status[task_id].get('status') == 'completed':
        return render_template('results.html', task_id=task_id, task=task_status[task_id])
    return "结果不存在或仍在处理中。", 404

@app.route('/download/<task_id>')
def download_results(task_id):
    if task_id in task_status and task_status[task_id].get('status') == 'completed':
        result_file_path = task_status[task_id].get('result_file')
        if result_file_path and os.path.exists(result_file_path):
            return send_file(result_file_path, as_attachment=True)
    return "结果文件不存在。", 404

@app.route('/api/results/<task_id>')
def get_results_api(task_id):
    result_file_path = os.path.join(RESULTS_FOLDER, f"{task_id}_results.json")
    if os.path.exists(result_file_path):
        return send_file(result_file_path, mimetype='application/json')
    cached_results = get_cached_results(task_id)
    if cached_results:
        return jsonify(cached_results)
    return jsonify({'error': '未找到结果'}), 404

@app.route('/history')
def history():
    sorted_tasks = sorted(task_status.items(), key=lambda item: item[1]['upload_time'], reverse=True)
    return render_template('history.html', tasks=sorted_tasks)

@app.route('/api/history')
def api_history():
    history_data = []
    for task_id, data in sorted(task_status.items(), key=lambda item: item[1].get('upload_time'), reverse=True):
        if 'results' in data:
            history_data.append({
                'task_id': task_id,
                'status': data.get('status'),
                'filename': data.get('filename', 'N/A'),
                'start_time': data.get('start_time'),
                'completion_time': data.get('completion_time'),
                'summary': data.get('results', {}).get('summary', {})
            })
    return jsonify(history_data)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    try:
        cleanup_count = cleanup_old_tasks(force=True)
        model_manager.cleanup_models()
        cleanup_memory()
        return jsonify({'message': f'清理完成，删除了 {cleanup_count} 个任务', 'memory_freed': True})
    except Exception as e:
        return jsonify({'error': f'清理失败: {str(e)}'}), 500

@app.route('/system/status')
def system_status():
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return jsonify({
            'cpu_usage': psutil.cpu_percent(interval=0.1),
            'memory_usage_mb': {'rss': mem_info.rss / 1024**2, 'vms': mem_info.vms / 1024**2},
            'gpu_info': get_gpu_memory_info(),
            'task_queue_size': task_queue.qsize(),
            'active_tasks': [tid for tid, t in task_status.items() if t.get('status') == 'processing'],
            'tracked_tasks': len(task_status)
        })
    except Exception as e:
        return jsonify({'error': f"无法获取系统状态: {str(e)}"}), 500

def cleanup_old_tasks(max_age_hours=24, force=False):
    cleanup_count = 0
    now = datetime.now()
    for task_id, data in list(task_status.items()):
        upload_time_str = data.get('upload_time')
        if upload_time_str:
            upload_time = datetime.fromisoformat(upload_time_str)
            age = now - upload_time
            if age.total_seconds() > max_age_hours * 3600 or force:
                result_file = data.get('result_file')
                if result_file and os.path.exists(result_file):
                    os.remove(result_file)
                del task_status[task_id]
                cleanup_count += 1
    return cleanup_count

def get_gpu_memory_info():
    if not torch.cuda.is_available():
        return "N/A"
    info = []
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        info.append({
            'device': i,
            'name': props.name,
            'total_memory_mb': props.total_memory / 1024**2,
            'allocated_memory_mb': torch.cuda.memory_allocated(i) / 1024**2,
            'cached_memory_mb': torch.cuda.memory_reserved(i) / 1024**2
        })
    return info

def warm_up_models():
    print("🔥 正在预热模型...")
    try:
        model_manager.get_model('cpu')
        if torch.cuda.is_available():
            model_manager.get_model('cuda')
        print("✅ 模型预热完成")
    except Exception as e:
        print(f"❌ 模型预热失败: {e}")

if __name__ == '__main__':
    cleanup_thread = threading.Thread(target=cleanup_old_tasks, daemon=True)
    cleanup_thread.start()
    
    for i in range(MAX_CONCURRENT_TASKS):
        worker_thread = threading.Thread(target=task_worker, daemon=True)
        worker_thread.start()
    
    warm_up_models()
    
    app.run(host='0.0.0.0', port=8000, debug=True) 