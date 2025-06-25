"""
系统监控路由模块
处理系统状态、内存清理和任务管理
"""

import psutil
import torch
from fastapi import APIRouter, HTTPException, Depends, Request

from ..deps import get_settings, task_status
from ..models import (SystemStatusResponse, GPUInfo, MemoryInfo, CleanupResponse, 
                   ModelStatusResponse, LoadedModelInfo)
from ..services.extractor import cleanup_old_tasks, model_manager

router = APIRouter()

@router.get("/system/models", response_model=ModelStatusResponse)
async def get_model_status():
    """获取当前加载的模型信息"""
    loaded_models = []
    if model_manager:
        for device, model in model_manager.models.items():
            loaded_models.append(LoadedModelInfo(
                device=device,
                model_class=model.__class__.__name__
            ))
    return ModelStatusResponse(loaded_models=loaded_models)

@router.post("/system/models/unload", response_model=CleanupResponse)
async def unload_models():
    """从内存中卸载所有模型以释放资源"""
    try:
        if model_manager:
            model_manager.cleanup_models()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return CleanupResponse(
            message="成功卸载所有模型并清理内存。",
            memory_freed=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"卸载模型失败: {str(e)}")

@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(request: Request):
    """
    获取系统状态信息
    包括 CPU、内存、GPU 使用情况和任务队列状态
    """
    # 获取 CPU 使用率
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # 获取内存使用情况
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_usage = MemoryInfo(
        rss=memory_info.rss / 1024 / 1024,  # 转换为 MB
        vms=memory_info.vms / 1024 / 1024   # 转换为 MB
    )
    
    # 获取 GPU 信息
    gpu_info = []
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            device_props = torch.cuda.get_device_properties(i)
            device_memory = torch.cuda.memory_stats(i)
            
            total_memory = device_props.total_memory / 1024 / 1024  # MB
            allocated_memory = device_memory.get('allocated_bytes.all.current', 0) / 1024 / 1024
            cached_memory = device_memory.get('reserved_bytes.all.current', 0) / 1024 / 1024
            
            gpu_info.append(GPUInfo(
                device=i,
                name=device_props.name,
                total_memory_mb=total_memory,
                allocated_memory_mb=allocated_memory,
                cached_memory_mb=cached_memory
            ))
    
    # 获取任务队列信息
    queue_size = request.app.state.task_queue.qsize()
    active_tasks = [task_id for task_id, data in task_status.items() 
                    if data.get('status') in ['processing', 'queued']]
    
    return SystemStatusResponse(
        cpu_usage=cpu_usage,
        memory_usage_mb=memory_usage,
        gpu_info=gpu_info,
        task_queue_size=queue_size,
        active_tasks=active_tasks,
        tracked_tasks=len(task_status)
    )

@router.post("/system/cleanup", response_model=CleanupResponse)
async def cleanup_system(force: bool = False):
    """
    清理系统资源
    
    - **force**: 是否强制清理所有任务（默认只清理24小时前的任务）
    """
    try:
        # 清理旧任务
        cleanup_count = cleanup_old_tasks(task_status, max_age_hours=24, force=force)
        
        # 清理模型缓存 (仅当 force=true 时)
        if force and model_manager:
            model_manager.cleanup_models()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            memory_freed = True
        else:
            memory_freed = False
        
        message = f"清理完成：移除了 {cleanup_count} 个旧任务"
        if memory_freed:
            message += "，已释放内存"
        
        return CleanupResponse(
            message=message,
            memory_freed=memory_freed
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

@router.get("/system/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "ok",
        "service": "OpenChemIE API",
        "cuda_available": torch.cuda.is_available(),
        "active_tasks": len([t for t in task_status.values() 
                           if t.get('status') in ['processing', 'queued']])
    } 