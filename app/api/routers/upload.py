"""
文件上传路由模块
处理 PDF 文件上传和任务提交
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from typing import Optional, List
import uuid
from datetime import datetime

from ..deps import get_settings, task_status
from ..models import UploadResponse, BatchUploadResponse
from ..services.extractor import submit_task, task_status_lock

router = APIRouter()

def allowed_file(filename: str, settings):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in settings.allowed_extensions

@router.post("/upload/batch/", response_model=BatchUploadResponse)
async def upload_batch_files(
    request: Request,
    files: List[UploadFile] = File(...),
    device: Optional[str] = Form('auto'),
    output_images: Optional[bool] = Form(False),
    output_bbox: Optional[bool] = Form(True),
    extract_corefs: Optional[bool] = Form(False),
    settings = Depends(get_settings)
):
    """
    上传一批 PDF 文件并为每个文件开始提取任务
    """
    batch_id = str(uuid.uuid4())
    task_ids = []
    
    # 准备选项
    options = {
        'device': device,
        'output_images': output_images,
        'output_bbox': output_bbox,
        'extract_corefs': extract_corefs
    }
    
    # 创建批处理任务条目
    batch_task_details = {
        'id': batch_id,
        'type': 'batch',
        'status': 'queued',
        'submitted_at': datetime.now().isoformat(),
        'total_files': len(files),
        'completed_files': 0,
        'failed_files': 0,
        'subtasks': {}
    }
    
    task_queue = request.app.state.task_queue

    for file in files:
        if not file.filename or not allowed_file(file.filename, settings):
            # 简单跳过无效文件，或者可以引发异常
            continue
        
        # 可以在这里添加文件大小检查
        
        task_id = submit_task(
            pdf_file=file,
            options=options,
            task_status_dict=task_status,
            upload_folder=settings.upload_folder,
            results_folder=settings.results_folder,
            task_queue=task_queue,
            batch_id=batch_id
        )
        task_ids.append(task_id)
        batch_task_details['subtasks'][task_id] = {'filename': file.filename, 'status': 'queued'}

    if not task_ids:
        raise HTTPException(status_code=400, detail="没有有效的文件可处理")

    with task_status_lock:
        batch_task_details['status'] = 'processing'
        task_status[batch_id] = batch_task_details

    return BatchUploadResponse(batch_id=batch_id, task_ids=task_ids)

@router.post("/upload/", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    device: Optional[str] = Form('auto'),
    output_images: Optional[bool] = Form(False),
    output_bbox: Optional[bool] = Form(True),
    extract_corefs: Optional[bool] = Form(False),
    settings = Depends(get_settings)
):
    """
    上传 PDF 文件并开始提取任务
    
    - **file**: PDF 文件
    - **device**: 计算设备 ('auto', 'cpu', 'cuda')
    - **output_images**: 是否输出图像
    - **output_bbox**: 是否输出边界框
    - **extract_corefs**: 是否提取共指信息
    """
    
    # 检查文件
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")
    
    if not allowed_file(file.filename, settings):
        raise HTTPException(status_code=400, detail="文件类型不允许，仅支持 PDF 文件")
    
    # 检查文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到开头
    
    if file_size > settings.max_content_length:
        raise HTTPException(status_code=413, detail="文件太大")
    
    # 准备选项
    options = {
        'device': device,
        'output_images': output_images,
        'output_bbox': output_bbox,
        'extract_corefs': extract_corefs
    }
    
    try:
        # 从 app.state 获取任务队列
        task_queue = request.app.state.task_queue
        
        # 提交任务
        task_id = submit_task(
            pdf_file=file,
            options=options,
            task_status_dict=task_status,
            upload_folder=settings.upload_folder,
            results_folder=settings.results_folder,
            task_queue=task_queue
        )
        
        return UploadResponse(task_id=task_id)
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) 