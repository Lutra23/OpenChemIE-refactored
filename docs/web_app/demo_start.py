#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChemIE v2.0 演示启动脚本
展示现代化Web界面和Gemini AI集成功能
"""

import os
import sys
import webbrowser
import time
from threading import Timer

def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🧪 OpenChemIE v2.0                        ║
║              智能化学信息提取工具 - 现代化版本                    ║
╠══════════════════════════════════════════════════════════════╣
║  🎨 现代化UI设计     | 🤖 Gemini AI集成                      ║
║  ⚡ 性能优化         | 🔧 配置管理                          ║
║  📱 响应式布局       | 🛡️ 安全加密                          ║
║  🌟 动画效果         | 📊 实时监控                          ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_dependencies():
    """检查依赖项"""
    print("🔍 检查系统依赖...")
    
    required_modules = [
        'flask', 'torch', 'werkzeug', 'psutil'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            missing_modules.append(module)
            print(f"  ❌ {module} (缺失)")
    
    if missing_modules:
        print(f"\n⚠️ 缺少依赖项: {', '.join(missing_modules)}")
        print("请运行: pip install " + " ".join(missing_modules))
        return False
    
    print("✅ 所有依赖项检查完成")
    return True

def check_optional_dependencies():
    """检查可选依赖项"""
    print("\n🔍 检查可选功能...")
    
    optional_modules = {
        'fitz': 'PyMuPDF (PDF处理)',
        'google.generativeai': 'Google Gemini API',
        'PIL': 'Pillow (图像处理)',
        'cv2': 'OpenCV (计算机视觉)'
    }
    
    for module, description in optional_modules.items():
        try:
            __import__(module)
            print(f"  ✅ {description}")
        except ImportError:
            print(f"  ⚠️ {description} (未安装，某些功能可能不可用)")

def setup_environment():
    """设置环境"""
    print("\n🛠️ 准备运行环境...")
    
    # 创建必要目录
    directories = [
        'uploads', 'results', 'config', 
        'static/css', 'static/js', 'templates'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  📁 {directory}")
    
    # 检查配置文件
    config_file = 'config/gemini_config.json'
    if not os.path.exists(config_file):
        print(f"  📝 将创建默认Gemini配置: {config_file}")
    else:
        print(f"  📝 发现现有配置: {config_file}")

def open_browser():
    """自动打开浏览器"""
    print("🌐 自动打开浏览器...")
    url = "http://localhost:5002"
    webbrowser.open(url)

def show_features():
    """显示新功能特性"""
    features = """
🎨 UI/UX 改进:
  • 现代化玻璃拟态设计风格
  • 流畅的动画和过渡效果
  • 响应式布局，支持移动设备
  • 深色模式自适应支持
  • 现代化图标和排版

🤖 AI 功能增强:
  • Gemini AI 模型集成
  • 智能文献分析
  • 可配置的AI参数
  • 实时API状态监控
  • 自定义提示词模板

⚡ 性能优化:
  • 并发任务处理
  • 内存使用优化
  • GPU/CPU自动切换
  • 队列管理系统
  • 缓存机制

🔧 管理功能:
  • 配置管理界面
  • 系统监控面板
  • 任务历史记录
  • 日志查看功能
  • 一键重置选项

🔗 访问地址:
  主页: http://localhost:5002/
  设置: http://localhost:5002/settings
  历史: http://localhost:5002/history
    """
    print(features)

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    check_optional_dependencies()
    setup_environment()
    
    # 显示功能特性
    show_features()
    
    print("\n🚀 启动 OpenChemIE v2.0...")
    print("请等待服务器初始化...")
    
    # 5秒后自动打开浏览器
    Timer(5.0, open_browser).start()
    
    # 启动Flask应用
    try:
        # 设置环境变量
        os.environ['FLASK_ENV'] = 'development'
        
        # 导入并运行应用
        from app import app
        print("\n✅ 服务器启动成功!")
        print("📍 访问地址: http://localhost:5002")
        print("🛑 按 Ctrl+C 停止服务器")
        
        app.run(
            host='0.0.0.0',
            port=5002,
            debug=True,
            use_reloader=False  # 避免重复启动
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 感谢使用 OpenChemIE v2.0!")
        print("如有问题请查看文档或联系开发团队")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("请检查依赖项和配置文件")

if __name__ == '__main__':
    main() 