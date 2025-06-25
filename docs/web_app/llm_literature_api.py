#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini文献分析 Web API集成模块
为Flask Web应用提供Gemini智能分析功能
"""

import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import threading
import queue

# 导入Gemini分析器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from gemini_analysis_module import GeminiChemicalAnalyzer
    GEMINI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Gemini分析模块不可用: {e}")
    GEMINI_AVAILABLE = False

# 创建蓝图
llm_bp = Blueprint('llm_analysis', __name__, url_prefix='/llm')

# 全局任务状态管理
gemini_tasks = {}
gemini_task_queue = queue.Queue()

# Gemini API配置
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def register_llm_routes(app):
    """注册LLM相关路由到Flask应用"""
    if not GEMINI_AVAILABLE:
        print("❌ Gemini功能不可用，跳过路由注册")
        return
    
    app.register_blueprint(llm_bp)
    print("✅ LLM文献分析路由已注册")


@llm_bp.route('/analyze', methods=['POST'])
def start_gemini_analysis():
    """启动Gemini文献分析任务"""
    if not GEMINI_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Gemini分析功能不可用'
        }), 400
    
    if not GEMINI_API_KEY:
        return jsonify({
            'success': False,
            'error': '未配置Gemini API密钥'
        }), 400
    
    try:
        # 获取参数
        data = request.get_json()
        pdf_path = data.get('pdf_path')
        json_path = data.get('json_path')
        target_pages = data.get('target_pages')  # 可选
        
        if not pdf_path or not json_path:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: pdf_path, json_path'
            }), 400
        
        # 验证文件存在
        if not os.path.exists(pdf_path):
            return jsonify({
                'success': False,
                'error': f'PDF文件不存在: {pdf_path}'
            }), 400
        
        if not os.path.exists(json_path):
            return jsonify({
                'success': False,
                'error': f'JSON文件不存在: {json_path}'
            }), 400
        
        # 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        gemini_tasks[task_id] = {
            'id': task_id,
            'status': 'queued',
            'message': '任务已创建，等待处理...',
            'created_at': datetime.now().isoformat(),
            'pdf_path': pdf_path,
            'json_path': json_path,
            'target_pages': target_pages,
            'progress': 0
        }
        
        # 启动后台任务
        thread = threading.Thread(
            target=gemini_analysis_worker,
            args=(task_id, pdf_path, json_path, target_pages)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Gemini分析任务已启动'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'启动分析失败: {str(e)}'
        }), 500


@llm_bp.route('/status/<task_id>')
def get_gemini_analysis_status(task_id):
    """获取Gemini分析任务状态"""
    if task_id not in gemini_tasks:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    task = gemini_tasks[task_id]
    return jsonify({
        'success': True,
        'task': task
    })


@llm_bp.route('/result/<task_id>')
def get_gemini_analysis_result(task_id):
    """获取Gemini分析结果"""
    if task_id not in gemini_tasks:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    task = gemini_tasks[task_id]
    
    if task['status'] != 'completed':
        return jsonify({
            'success': False,
            'error': f'任务尚未完成，当前状态: {task["status"]}'
        }), 400
    
    try:
        # 读取分析结果
        result_file = task.get('result_file')
        if result_file and os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            return jsonify({
                'success': True,
                'result': result_data
            })
        else:
            return jsonify({
                'success': False,
                'error': '结果文件不存在'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'读取结果失败: {str(e)}'
        }), 500


@llm_bp.route('/download/<task_id>/<file_type>')
def download_gemini_result(task_id, file_type):
    """下载Gemini分析结果文件"""
    if task_id not in gemini_tasks:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    task = gemini_tasks[task_id]
    
    if task['status'] != 'completed':
        return jsonify({
            'success': False,
            'error': '任务尚未完成'
        }), 400
    
    try:
        if file_type == 'json':
            file_path = task.get('result_file')
            mimetype = 'application/json'
            filename = f'gemini_analysis_{task_id}.json'
        elif file_type == 'markdown':
            file_path = task.get('markdown_file')
            mimetype = 'text/markdown'
            filename = f'gemini_analysis_{task_id}.md'
        else:
            return jsonify({
                'success': False,
                'error': '不支持的文件类型'
            }), 400
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'下载失败: {str(e)}'
        }), 500


@llm_bp.route('/tasks')
def list_gemini_tasks():
    """列出所有Gemini分析任务"""
    tasks = []
    for task_id, task in gemini_tasks.items():
        # 只返回基本信息
        task_info = {
            'id': task_id,
            'status': task['status'],
            'message': task['message'],
            'created_at': task['created_at'],
            'progress': task.get('progress', 0)
        }
        
        if 'completed_at' in task:
            task_info['completed_at'] = task['completed_at']
        
        tasks.append(task_info)
    
    # 按创建时间倒序排列
    tasks.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify({
        'success': True,
        'tasks': tasks
    })


@llm_bp.route('/config')
def get_gemini_config():
    """获取Gemini配置信息"""
    return jsonify({
        'success': True,
        'config': {
            'gemini_available': GEMINI_AVAILABLE,
            'api_key_configured': bool(GEMINI_API_KEY),
            'supported_models': ['gemini-1.5-pro', 'gemini-1.0-pro'],
            'max_pages': 50,  # 最大处理页面数
            'supported_formats': ['pdf', 'json']
        }
    })


@llm_bp.route('/demo')
def gemini_demo_page():
    """Gemini分析演示页面"""
    return render_template('gemini_demo.html')


def gemini_analysis_worker(task_id, pdf_path, json_path, target_pages=None):
    """Gemini分析后台工作函数"""
    try:
        # 更新任务状态
        gemini_tasks[task_id]['status'] = 'processing'
        gemini_tasks[task_id]['message'] = '正在初始化Gemini分析器...'
        gemini_tasks[task_id]['progress'] = 10
        
        # 创建Gemini分析器
        analyzer = GeminiChemicalAnalyzer(api_key=GEMINI_API_KEY)
        
        # 更新进度
        gemini_tasks[task_id]['message'] = '正在处理PDF和JSON数据...'
        gemini_tasks[task_id]['progress'] = 30
        
        # 准备输出路径
        output_dir = os.path.join('results', 'gemini_analysis')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'gemini_{task_id}')
        
        # 执行分析
        gemini_tasks[task_id]['message'] = '正在调用Gemini进行智能分析...'
        gemini_tasks[task_id]['progress'] = 50
        
        result = analyzer.analyze_chemical_literature(
            pdf_path=pdf_path,
            json_result_path=json_path,
            output_path=output_path,
            target_pages=target_pages
        )
        
        # 更新任务状态
        gemini_tasks[task_id].update({
            'status': 'completed',
            'message': '分析完成！',
            'progress': 100,
            'completed_at': datetime.now().isoformat(),
            'result_file': f'{output_path}.json',
            'markdown_file': f'{output_path}.md',
            'analysis_summary': {
                'pages_analyzed': result['metadata']['total_pages_analyzed'],
                'failed_pages': result['metadata']['failed_pages'],
                'confidence_score': result['database_format']['metadata'].get('confidence_score', 0)
            }
        })
        
        print(f"✅ Gemini分析任务 {task_id} 完成")
        
    except Exception as e:
        # 错误处理
        gemini_tasks[task_id].update({
            'status': 'error',
            'message': f'分析失败: {str(e)}',
            'progress': 0,
            'error_at': datetime.now().isoformat()
        })
        
        print(f"❌ Gemini分析任务 {task_id} 失败: {str(e)}")


def cleanup_old_gemini_tasks(max_age_hours=24):
    """清理旧的Gemini分析任务"""
    current_time = datetime.now()
    expired_tasks = []
    
    for task_id, task in gemini_tasks.items():
        created_at = datetime.fromisoformat(task['created_at'])
        age_hours = (current_time - created_at).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            expired_tasks.append(task_id)
    
    # 删除过期任务
    for task_id in expired_tasks:
        # 删除相关文件
        task = gemini_tasks[task_id]
        if 'result_file' in task and os.path.exists(task['result_file']):
            try:
                os.remove(task['result_file'])
            except:
                pass
        
        if 'markdown_file' in task and os.path.exists(task['markdown_file']):
            try:
                os.remove(task['markdown_file'])
            except:
                pass
        
        # 删除任务记录
        del gemini_tasks[task_id]
    
    print(f"🧹 清理了 {len(expired_tasks)} 个过期的Gemini分析任务")


# 定期清理任务（可以集成到主应用的定时任务中）
def start_cleanup_scheduler():
    """启动清理调度器（简单版本）"""
    import threading
    import time
    
    def cleanup_loop():
        while True:
            try:
                time.sleep(3600)  # 每小时执行一次
                cleanup_old_gemini_tasks()
            except:
                pass
    
    cleanup_thread = threading.Thread(target=cleanup_loop)
    cleanup_thread.daemon = True
    cleanup_thread.start()


# API使用示例和文档
GEMINI_API_USAGE = """
Gemini化学文献分析 API 使用指南

1. 启动分析任务:
POST /llm/analyze
{
    "pdf_path": "/path/to/document.pdf",
    "json_path": "/path/to/results.json",
    "target_pages": [1, 2, 3]  // 可选
}

2. 查询任务状态:
GET /llm/status/<task_id>

3. 获取分析结果:
GET /llm/result/<task_id>

4. 下载结果文件:
GET /llm/download/<task_id>/json
GET /llm/download/<task_id>/markdown

5. 列出所有任务:
GET /llm/tasks

6. 获取配置信息:
GET /llm/config

环境要求:
- 设置环境变量 GEMINI_API_KEY
- 安装依赖: google-generativeai, PyMuPDF, Pillow
"""

if __name__ == "__main__":
    print(GEMINI_API_USAGE) 