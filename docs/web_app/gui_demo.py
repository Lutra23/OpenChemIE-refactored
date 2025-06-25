#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChemIE GUI演示脚本
展示新的可视化组件和界面功能
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 创建演示应用
app = Flask(__name__)
app.secret_key = 'gui-demo-key'

# 演示数据
DEMO_DATA = {
    "schema_version": "2.0.0",
    "metadata": {
        "extraction_info": {
            "timestamp": datetime.now().isoformat(),
            "extractor_version": "2.0.0",
            "device_used": "cpu",
            "processing_time_seconds": 45.2
        },
        "document_info": {
            "file_name": "demo_paper.pdf",
            "file_type": "pdf",
            "file_size_mb": 2.5,
            "total_pages": 12
        }
    },
    "chemical_entities": {
        "molecules": {
            "mol_001": {
                "name": "苯甲酸",
                "smiles": "C1=CC=C(C=C1)C(=O)O",
                "confidence": 0.95,
                "source": "figure",
                "formula": "C7H6O2",
                "molecular_weight": 122.12
            },
            "mol_002": {
                "name": "吡啶",
                "smiles": "C1=CC=NC=C1",
                "confidence": 0.88,
                "source": "figure",
                "formula": "C5H5N",
                "molecular_weight": 79.10
            },
            "mol_003": {
                "name": "乙醇",
                "smiles": "CCO",
                "confidence": 0.92,
                "source": "text",
                "formula": "C2H6O",
                "molecular_weight": 46.07
            },
            "mol_004": {
                "name": "苯",
                "smiles": "C1=CC=CC=C1",
                "confidence": 0.96,
                "source": "figure",
                "formula": "C6H6",
                "molecular_weight": 78.11
            },
            "mol_005": {
                "name": "甲苯",
                "smiles": "CC1=CC=CC=C1",
                "confidence": 0.89,
                "source": "figure",
                "formula": "C7H8",
                "molecular_weight": 92.14
            }
        },
        "reactions": {
            "rxn_001": {
                "reactants": [
                    {
                        "name": "苯甲酸",
                        "smiles": "C1=CC=C(C=C1)C(=O)O",
                        "formula": "C7H6O2"
                    },
                    {
                        "name": "乙醇",
                        "smiles": "CCO",
                        "formula": "C2H6O"
                    }
                ],
                "products": [
                    {
                        "name": "苯甲酸乙酯",
                        "smiles": "CCOC(=O)C1=CC=CC=C1",
                        "formula": "C9H10O2"
                    }
                ],
                "conditions": [
                    {
                        "name": "硫酸",
                        "text": "H2SO4"
                    }
                ],
                "temperature": "78°C",
                "time": "4h",
                "yield": "85%",
                "confidence": 0.91
            },
            "rxn_002": {
                "reactants": [
                    {
                        "name": "苯",
                        "smiles": "C1=CC=CC=C1",
                        "formula": "C6H6"
                    }
                ],
                "products": [
                    {
                        "name": "甲苯",
                        "smiles": "CC1=CC=CC=C1",
                        "formula": "C7H8"
                    }
                ],
                "conditions": [
                    {
                        "name": "甲基化试剂",
                        "text": "CH3I, AlCl3"
                    }
                ],
                "temperature": "25°C",
                "time": "2h",
                "yield": "72%",
                "confidence": 0.87
            }
        }
    },
    "document_content": {
        "figures": {
            "figure_001": {
                "page": 3,
                "caption": "反应机理示意图",
                "molecules_detected": 3,
                "bbox": [100, 150, 400, 350]
            },
            "figure_002": {
                "page": 5,
                "caption": "产物结构确认",
                "molecules_detected": 2,
                "bbox": [80, 200, 450, 380]
            }
        },
        "tables": {
            "table_001": {
                "page": 7,
                "caption": "反应条件优化",
                "rows": 6,
                "columns": 4,
                "data_extracted": True
            }
        }
    },
    "statistics": {
        "total_molecules": 5,
        "total_reactions": 2,
        "total_figures": 2,
        "total_tables": 1,
        "confidence_distribution": {
            "high": 3,
            "medium": 2,
            "low": 0
        },
        "processing_time": 45.2
    }
}

# 模拟任务状态
demo_tasks = {
    "demo_001": {
        "task_id": "demo_001",
        "filename": "demo_paper.pdf",
        "timestamp": datetime.now().isoformat(),
        "file_size": 2.5,
        "status": "completed",
        "results": DEMO_DATA
    },
    "demo_002": {
        "task_id": "demo_002", 
        "filename": "synthesis_paper.pdf",
        "timestamp": datetime.now().isoformat(),
        "file_size": 3.2,
        "status": "completed",
        "results": DEMO_DATA
    }
}

@app.route('/')
def index():
    """主页 - 重定向到可视化页面"""
    return render_template('visualization.html')

@app.route('/visualization')
def visualization():
    """可视化演示页面"""
    return render_template('visualization.html')

@app.route('/api/history')
def api_history():
    """获取演示历史数据"""
    return jsonify(list(demo_tasks.values()))

@app.route('/api/results/<task_id>')
def get_results(task_id):
    """获取演示结果数据"""
    if task_id in demo_tasks:
        return jsonify(demo_tasks[task_id]['results'])
    else:
        return jsonify({"error": "Task not found"}), 404

@app.route('/api/report/<task_id>')
def generate_report(task_id):
    """生成演示报告"""
    if task_id not in demo_tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task_info = demo_tasks[task_id]
    results = task_info['results']
    
    report_html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>OpenChemIE GUI 演示报告</title>
        <style>
            body {{ font-family: 'Inter', Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            }}
            .section {{ 
                margin: 20px 0; padding: 25px; 
                background: white; border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            }}
            .stats {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 20px; margin: 20px 0;
            }}
            .stat-item {{ 
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                padding: 20px; border-radius: 10px; text-align: center;
                border: 1px solid rgba(102, 126, 234, 0.1);
            }}
            .stat-item h3 {{ color: #667eea; margin: 10px 0; }}
            .demo-badge {{ 
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white; padding: 5px 15px; border-radius: 20px;
                font-size: 12px; font-weight: bold; display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎨 OpenChemIE GUI 可视化演示报告</h1>
            <p>任务ID: {task_id}</p>
            <p>文件: {task_info['filename']}</p>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <span class="demo-badge">GUI 演示模式</span>
        </div>
        
        <div class="section">
            <h2>🔬 化学信息提取统计</h2>
            <div class="stats">
                <div class="stat-item">
                    <h3>{results['statistics']['total_molecules']}</h3>
                    <p>检测分子</p>
                </div>
                <div class="stat-item">
                    <h3>{results['statistics']['total_reactions']}</h3>
                    <p>化学反应</p>
                </div>
                <div class="stat-item">
                    <h3>{results['statistics']['total_figures']}</h3>
                    <p>图表数据</p>
                </div>
                <div class="stat-item">
                    <h3>{results['statistics']['total_tables']}</h3>
                    <p>表格信息</p>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🎨 GUI 功能展示</h2>
            <ul>
                <li>✅ 交互式分子结构查看器</li>
                <li>✅ 动态反应流程图</li>
                <li>✅ 现代化玻璃拟态界面设计</li>
                <li>✅ 响应式布局和动画效果</li>
                <li>✅ 多主题支持</li>
                <li>✅ 实时数据过滤和分析</li>
                <li>✅ SVG导出功能</li>
                <li>✅ 智能布局算法</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>⚡ 处理信息</h2>
            <p><strong>处理时间:</strong> {results['statistics']['processing_time']}秒</p>
            <p><strong>设备:</strong> {results['metadata']['extraction_info']['device_used'].upper()}</p>
            <p><strong>提取器版本:</strong> {results['metadata']['extraction_info']['extractor_version']}</p>
            <p><strong>页面数量:</strong> {results['metadata']['document_info']['total_pages']}</p>
        </div>
        
        <div class="section">
            <h2>🚀 技术特色</h2>
            <div class="stats">
                <div class="stat-item">
                    <h3>SVG</h3>
                    <p>矢量图形渲染</p>
                </div>
                <div class="stat-item">
                    <h3>CSS3</h3>
                    <p>现代动画效果</p>
                </div>
                <div class="stat-item">
                    <h3>ES6+</h3>
                    <p>模块化JavaScript</p>
                </div>
                <div class="stat-item">
                    <h3>Bootstrap 5</h3>
                    <p>响应式设计</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return report_html, 200, {'Content-Type': 'text/html; charset=utf-8'}

def print_demo_info():
    """打印演示信息"""
    print("\n" + "="*60)
    print("🎨 OpenChemIE GUI 可视化演示")
    print("="*60)
    print("🚀 启动信息:")
    print(f"   - 演示端口: http://localhost:5003")
    print(f"   - 可视化页面: http://localhost:5003/visualization")
    print(f"   - 演示数据: {len(DEMO_DATA['chemical_entities']['molecules'])} 个分子, {len(DEMO_DATA['chemical_entities']['reactions'])} 个反应")
    print("\n🎯 功能演示:")
    print("   ✅ 交互式分子结构查看器")
    print("   ✅ 动态反应流程图")
    print("   ✅ 现代化界面设计")
    print("   ✅ 主题切换功能")
    print("   ✅ 数据过滤和导出")
    print("   ✅ 实时统计面板")
    print("\n💡 使用说明:")
    print("   1. 访问可视化页面")
    print("   2. 在数据控制面板选择演示数据源")
    print("   3. 点击'加载可视化'按钮")
    print("   4. 交互探索分子和反应")
    print("   5. 尝试不同主题和导出功能")
    print("\n" + "="*60)

def run_demo():
    """运行演示"""
    print_demo_info()
    
    # 在新线程中启动Flask应用
    def start_app():
        app.run(host='0.0.0.0', port=5003, debug=False, use_reloader=False)
    
    app_thread = threading.Thread(target=start_app, daemon=True)
    app_thread.start()
    
    try:
        print("\n⌨️  按 Ctrl+C 退出演示")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 演示结束，感谢使用！")

if __name__ == '__main__':
    run_demo() 