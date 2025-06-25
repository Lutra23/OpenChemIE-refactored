"""
任务管理路由模块
处理任务状态查询、结果查看、下载和历史记录
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import json
from fastapi_cache.decorator import cache

from ..deps import get_settings, task_status
from ..models import TaskStatusResponse, HistoryItem, BatchStatusResponse

router = APIRouter()

@router.get("/status/batch/{batch_id}", response_model=BatchStatusResponse)
@cache(expire=2)
async def get_batch_status(batch_id: str):
    """
    获取批处理任务的状态
    """
    if batch_id not in task_status or task_status[batch_id].get('type') != 'batch':
        raise HTTPException(status_code=404, detail="批处理任务ID不存在")
    
    return BatchStatusResponse(**task_status[batch_id])

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
@cache(expire=2)
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    - **task_id**: 任务ID
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务ID不存在")
    
    task_data = task_status[task_id]
    return TaskStatusResponse(**task_data)

@router.get("/results/batch/{batch_id}")
@cache(expire=3600)
async def get_batch_results(batch_id: str, settings = Depends(get_settings)):
    """
    获取批处理任务的所有结果
    """
    if batch_id not in task_status or task_status[batch_id].get('type') != 'batch':
        raise HTTPException(status_code=404, detail="批处理任务ID不存在")
    
    batch_task = task_status[batch_id]
    if batch_task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="批处理任务尚未完成")

    aggregated_results = []
    for task_id in batch_task['subtasks']:
        task_data = task_status.get(task_id)
        if task_data and task_data.get('status') == 'completed':
            result_file_path = task_data.get('result_file')
            if result_file_path and os.path.exists(result_file_path):
                try:
                    with open(result_file_path, 'r', encoding='utf-8') as f:
                        aggregated_results.append(json.load(f))
                except Exception:
                    # 如果单个文件读取失败，可以跳过或记录错误
                    pass

    return JSONResponse(content=aggregated_results)

@router.get("/results/{task_id}")
@cache(expire=3600)
async def get_results(task_id: str, settings = Depends(get_settings)):
    """
    获取任务结果 (JSON 格式)
    
    - **task_id**: 任务ID
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务ID不存在")
    
    task_data = task_status[task_id]
    if task_data.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    result_file_path = task_data.get('result_file')
    if not result_file_path or not os.path.exists(result_file_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    return FileResponse(
        path=result_file_path, 
        media_type='application/json',
        filename=f"{task_id}_results.json"
    )

@router.get("/download/{task_id}")
async def download_results(task_id: str, settings = Depends(get_settings)):
    """
    下载任务结果文件
    
    - **task_id**: 任务ID
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务ID不存在")
    
    task_data = task_status[task_id]
    if task_data.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    result_file_path = task_data.get('result_file')
    if not result_file_path or not os.path.exists(result_file_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    return FileResponse(
        path=result_file_path,
        media_type='application/octet-stream',
        filename=f"{task_id}_results.json"
    )

@router.get("/history", response_model=List[HistoryItem])
@cache(expire=60)
async def get_history():
    """
    获取任务历史记录
    """
    history_data = []
    
    # 按上传时间倒序排列
    sorted_tasks = sorted(
        task_status.items(), 
        key=lambda item: item[1].get('upload_time', ''), 
        reverse=True
    )
    
    for task_id, data in sorted_tasks:
        if 'results' in data:  # 只返回有结果的任务
            history_item = HistoryItem(
                task_id=task_id,
                status=data.get('status', 'unknown'),
                filename=data.get('filename', 'N/A'),
                start_time=data.get('start_time'),
                completion_time=data.get('completion_time'),
                summary=data.get('results', {}).get('summary', {})
            )
            history_data.append(history_item)
    
    return history_data

@router.get("/api/results/{task_id}")
@cache(expire=3600)
async def get_results_api(task_id: str, settings = Depends(get_settings)):
    """
    API 格式获取任务结果（兼容旧接口）
    
    - **task_id**: 任务ID
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="未找到结果")
    
    task_data = task_status[task_id]
    
    # 如果任务已完成且有缓存结果，直接返回
    if 'results' in task_data:
        return JSONResponse(content=task_data['results'])
    
    # 否则尝试从文件读取
    result_file_path = task_data.get('result_file')
    if result_file_path and os.path.exists(result_file_path):
        return FileResponse(
            path=result_file_path, 
            media_type='application/json'
        )
    
    raise HTTPException(status_code=404, detail="未找到结果") 