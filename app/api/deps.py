"""
FastAPI 依赖注入模块
提供全局配置、ModelManager 单例等共享资源
"""

import os
from pathlib import Path
from typing import Dict, Any
from functools import lru_cache

# 全局任务状态存储
task_status: Dict[str, Dict[str, Any]] = {}

class Settings:
    """全局配置"""
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent  # OpenChemIE-good copy/
        self.upload_folder = self.base_dir / "uploads"
        self.results_folder = self.base_dir / "results" 
        self.max_content_length = 50 * 1024 * 1024  # 50MB
        self.max_concurrent_tasks = 2
        self.task_queue_size = 10
        self.cache_size = 100
        self.allowed_extensions = {'pdf'}
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # 确保目录存在
        self.upload_folder.mkdir(exist_ok=True)
        self.results_folder.mkdir(exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()

# 导入 ModelManager
from .services.extractor import model_manager

def get_model_manager():
    """获取 ModelManager 单例实例"""
    return model_manager 