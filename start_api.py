#!/usr/bin/env python3
"""
OpenChemIE FastAPI 服务启动脚本
"""

import uvicorn
import sys
import os
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.api.deps import get_settings

def main():
    """启动 FastAPI 服务"""
    print("🚀 启动 OpenChemIE FastAPI 服务...")
    
    settings = get_settings()
    
    # 使用 uvicorn.Config 进行详细配置
    config = uvicorn.Config(
        app="app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        # 尝试使用 h11 协议实现来解决兼容性问题
        http="h11",
        # 增加各种限制以处理大文件上传
        limit_max_requests=1000,
        timeout_keep_alive=5,
        # 增加请求体大小限制
        h11_max_incomplete_event_size=settings.max_content_length,
        # 启用更多调试信息
        access_log=True
    )
    
    server = uvicorn.Server(config)

    try:
        # 启动服务
        server.run()
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 