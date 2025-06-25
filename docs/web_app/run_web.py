#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChemIE Web服务启动脚本 - 性能优化版
"""

import os
import sys
import torch
import psutil
from pathlib import Path

def check_system_requirements():
    """检查系统要求和性能配置"""
    print("🔍 系统环境检查...")
    
    # Python版本检查
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"⚠️ Python版本 {python_version.major}.{python_version.minor} 可能不兼容，建议使用Python 3.8+")
    else:
        print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # CUDA检查
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"✅ CUDA可用: {gpu_count}块GPU")
        print(f"   📱 主GPU: {gpu_name} ({gpu_memory:.1f}GB)")
    else:
        print("⚠️ CUDA不可用，将使用CPU（较慢）")
        print("   💡 建议：安装CUDA版本的PyTorch以获得更好性能")
    
    # 内存检查
    memory = psutil.virtual_memory()
    memory_gb = memory.total / 1024**3
    print(f"💾 系统内存: {memory_gb:.1f}GB (可用: {memory.available/1024**3:.1f}GB)")
    
    if memory_gb < 8:
        print("⚠️ 内存较少，建议关闭图片输出和共指关系提取")
    elif memory_gb < 16:
        print("💡 内存适中，建议适度使用高级功能")
    else:
        print("✅ 内存充足，支持所有功能")
    
    # CPU检查
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    print(f"🚀 CPU: {cpu_count}核心")
    if cpu_freq:
        print(f"   ⚡ 频率: {cpu_freq.current:.0f}MHz")
    
    return cuda_available, memory_gb

def optimize_torch_settings():
    """优化PyTorch设置"""
    print("\n⚙️ 优化PyTorch设置...")
    
    # 设置线程数
    cpu_count = psutil.cpu_count()
    torch.set_num_threads(min(cpu_count, 8))  # 限制线程数避免过载
    print(f"🔧 PyTorch线程数: {torch.get_num_threads()}")
    
    # 内存优化
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True  # 优化卷积性能
        torch.cuda.empty_cache()  # 清理GPU缓存
        print("🎯 启用CUDNN优化")
    
    # 设置环境变量
    os.environ['OMP_NUM_THREADS'] = str(min(cpu_count, 8))
    os.environ['MKL_NUM_THREADS'] = str(min(cpu_count, 8))
    
def show_performance_tips(cuda_available, memory_gb):
    """显示性能优化建议"""
    print("\n💡 性能优化建议:")
    
    if not cuda_available:
        print("   📱 安装CUDA版本PyTorch可大幅提升速度")
        print("   🔗 https://pytorch.org/get-started/locally/")
    
    if memory_gb < 16:
        print("   💾 内存不足时建议:")
        print("      • 关闭'保存提取图片'选项")
        print("      • 关闭'提取分子共指关系'选项")
        print("      • 单个文件处理，避免批量上传")
    
    print("   ⚡ 性能设置建议:")
    print("      • 设备选择: " + ("GPU (推荐)" if cuda_available else "CPU"))
    print("      • 并发任务: 建议不超过2个")
    print("      • 定期清理缓存和旧任务")
    
def main():
    """主函数"""
    print("🚀 启动 OpenChemIE Web界面 (性能优化版)...")
    print("=" * 50)
    
    # 系统检查
    cuda_available, memory_gb = check_system_requirements()
    
    # 优化设置
    optimize_torch_settings()
    
    # 性能建议
    show_performance_tips(cuda_available, memory_gb)
    
    print("\n" + "=" * 50)
    print("🌐 Web服务信息:")
    print("📱 访问地址: http://localhost:5001")
    print("📊 性能监控: http://localhost:5001 -> 性能监控")
    print("📝 历史记录: http://localhost:5001/history")
    print("🔧 系统状态API: http://localhost:5001/system/status")
    print("\n💡 使用技巧:")
    print("   • 首次启动会预载模型，需要等待")
    print("   • 建议先上传小文件测试系统性能")
    print("   • 可通过性能监控查看资源使用情况")
    print("   • 使用 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 设置环境变量
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # 启动应用
    try:
        from app import app
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,  # 生产模式，提升性能
            threaded=True,
            use_reloader=False  # 禁用自动重载
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        print("💫 感谢使用 OpenChemIE!")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n🔧 故障排除:")
        print("   1. 检查端口5001是否被占用")
        print("   2. 确认所有依赖包已正确安装")
        print("   3. 检查Python环境和CUDA配置")
        sys.exit(1)

if __name__ == '__main__':
    main() 