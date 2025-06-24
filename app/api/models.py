"""
Pydantic 数据模型
定义 FastAPI 的请求和响应格式
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

class UploadResponse(BaseModel):
    """文件上传响应"""
    task_id: str

class BatchUploadResponse(BaseModel):
    batch_id: str
    task_ids: List[str]

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    status: str
    message: Optional[str] = None
    result_file: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    completion_time: Optional[str] = None
    error: Optional[str] = None

class BatchStatusResponse(BaseModel):
    status: str
    total_files: int
    completed_files: int
    failed_files: int
    subtasks: Dict[str, Dict[str, str]]

class HistoryItem(BaseModel):
    """历史记录项"""
    task_id: str
    status: str
    filename: str
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None

class GPUInfo(BaseModel):
    """GPU 信息"""
    device: int
    name: str
    total_memory_mb: float
    allocated_memory_mb: float
    cached_memory_mb: float

class MemoryInfo(BaseModel):
    """内存信息"""
    rss: float
    vms: float

class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    cpu_usage: float
    memory_usage_mb: MemoryInfo
    gpu_info: List[GPUInfo]
    task_queue_size: int
    active_tasks: List[str]
    tracked_tasks: int

class CleanupResponse(BaseModel):
    """清理响应"""
    message: str
    memory_freed: bool

class LoadedModelInfo(BaseModel):
    """已加载模型的信息"""
    device: str
    model_class: str

class ModelStatusResponse(BaseModel):
    """模型状态响应"""
    loaded_models: List[LoadedModelInfo] 