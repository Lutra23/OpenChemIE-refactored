/* OpenChemIE v2.0 前端逻辑 */

// 全局变量
let currentTaskId = null;
let uploadInProgress = false;
let statusCheckInterval = null;

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupDragAndDrop();
    setupFileInput();
    setupUploadButton();
    setupProgressButtons();
    updateSystemStatus();
    
    // 定期更新系统状态
    setInterval(updateSystemStatus, 30000);

    console.log('🚀 OpenChemIE v2.0 初始化完成');
}

// ==================== 文件上传相关 ====================

function setupDragAndDrop() {
    const dropZone = document.getElementById('dropZone');
    
    if (!dropZone) return;

    // 防止默认拖拽行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // 拖拽高亮效果
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // 处理文件放置
    dropZone.addEventListener('drop', handleDrop, false);
    dropZone.addEventListener('click', () => {
        document.getElementById('fileInput').click();
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    document.getElementById('dropZone').classList.add('dragover');
}

function unhighlight(e) {
    document.getElementById('dropZone').classList.remove('dragover');
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function setupFileInput() {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput) return;

    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
    });
}

function handleFiles(files) {
    if (files.length === 0) return;
    
    const file = files[0];
    
    // 验证文件类型
    if (!file.type.includes('pdf')) {
        showAlert('请选择PDF文件', 'warning');
        return;
    }
    
    // 验证文件大小 (50MB)
    if (file.size > 50 * 1024 * 1024) {
        showAlert('文件大小不能超过50MB', 'warning');
        return;
    }
    
    displayFileInfo(file);
    enableUploadButton();
}

function displayFileInfo(file) {
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');  
    const fileSize = document.getElementById('fileSize');
    
    if (fileInfo && fileName && fileSize) {
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        fileInfo.style.display = 'block';
        
        // 添加动画效果
        fileInfo.classList.add('fade-in');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function enableUploadButton() {
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) {
        uploadBtn.disabled = false;
        uploadBtn.classList.add('glow-effect');
    }
}

function setupUploadButton() {
    const uploadBtn = document.getElementById('uploadBtn');
    if (!uploadBtn) return;

    uploadBtn.addEventListener('click', function() {
        if (uploadInProgress) return;
        
        const fileInput = document.getElementById('fileInput');
        if (!fileInput.files.length) {
            showAlert('请先选择PDF文件', 'warning');
            return;
        }
        
        startUpload();
    });
}

function startUpload() {
    uploadInProgress = true;
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    
    // 更新按钮状态
    uploadBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>上传中...';
    uploadBtn.disabled = true;
    
    // 收集表单数据
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('device', document.getElementById('device').value);
    formData.append('output_bbox', document.getElementById('output_bbox').checked);
    formData.append('output_images', document.getElementById('output_images').checked);
    formData.append('extract_corefs', document.getElementById('extract_corefs').checked);
    
    // 上传文件
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentTaskId = data.task_id;
            showProgressContainer();
            startStatusMonitoring();
        } else {
            showAlert('上传失败: ' + data.message, 'danger');
            resetUploadButton();
        }
    })
    .catch(error => {
        showAlert('上传过程中出现错误: ' + error.message, 'danger');
        resetUploadButton();
    });
}

function resetUploadButton() {
    uploadInProgress = false;
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) {
        uploadBtn.innerHTML = '<i class="bi bi-rocket-takeoff me-2"></i>开始智能提取';
        uploadBtn.disabled = false;
    }
}

// ==================== 进度监控 ====================

function showProgressContainer() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.style.display = 'block';
        progressContainer.classList.add('fade-in');
        progressContainer.scrollIntoView({ behavior: 'smooth' });
    }
}

function hideProgressContainer() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
}

function startStatusMonitoring() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    statusCheckInterval = setInterval(checkTaskStatus, 2000);
    checkTaskStatus(); // 立即检查一次
}

function stopStatusMonitoring() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

function checkTaskStatus() {
    if (!currentTaskId) return;
    
    fetch(`/status/${currentTaskId}`)
        .then(response => response.json())
        .then(data => {
            updateProgressUI(data);
            
            if (data.status === 'completed') {
                stopStatusMonitoring();
                showResults(data);
            } else if (data.status === 'error') {
                stopStatusMonitoring();
                showAlert('处理失败: ' + data.message, 'danger');
                resetUploadButton();
                hideProgressContainer();
            }
        })
        .catch(error => {
            console.error('状态检查失败:', error);
        });
}

function updateProgressUI(data) {
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');
    const progressPercent = document.getElementById('progressPercent');
    const progressTitle = document.getElementById('progressTitle');
    
    let progress = 0;
    let message = data.message || '处理中...';
    
    // 根据状态计算进度
    switch(data.status) {
        case 'queued':
            progress = 10;
            message = '排队等待中...';
            break;
        case 'processing':
            progress = 50;
            message = '正在提取化学信息...';
            break;
        case 'completed':
            progress = 100;
            message = '提取完成!';
            break;
        case 'error':
            progress = 0;
            message = '处理失败';
            break;
    }
    
    if (progressBar) {
        progressBar.style.width = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
    }
    
    if (progressMessage) progressMessage.textContent = message;
    if (progressPercent) progressPercent.textContent = progress + '%';
    if (progressTitle) progressTitle.textContent = data.status === 'completed' ? '处理完成' : '处理中...';
}

function showResults(data) {
    hideProgressContainer();
    
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsPreview = document.getElementById('resultsPreview');
    
    if (resultsContainer && resultsPreview) {
        // 显示结果摘要
        const results = data.results || {};
        const entitiesCount = results.entities_count || {};
        
        resultsPreview.innerHTML = `
            <div class="row">
                <div class="col-md-3 text-center">
                    <div class="card glass-effect">
                        <div class="card-body">
                            <i class="bi bi-hexagon display-6 text-primary"></i>
                            <h4 class="mt-2">${entitiesCount.molecules || 0}</h4>
                            <small class="text-muted">分子结构</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="card glass-effect">
                        <div class="card-body">
                            <i class="bi bi-arrow-left-right display-6 text-success"></i>
                            <h4 class="mt-2">${entitiesCount.reactions || 0}</h4>
                            <small class="text-muted">反应方程</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="card glass-effect">
                        <div class="card-body">
                            <i class="bi bi-image display-6 text-info"></i>
                            <h4 class="mt-2">${entitiesCount.figures || 0}</h4>
                            <small class="text-muted">图表</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="card glass-effect">
                        <div class="card-body">
                            <i class="bi bi-table display-6 text-warning"></i>
                            <h4 class="mt-2">${entitiesCount.tables || 0}</h4>
                            <small class="text-muted">表格</small>
                        </div>
                    </div>
                </div>
            </div>
            <div class="mt-3">
                <p class="text-muted">
                    <i class="bi bi-clock"></i> 处理时间: ${results.processing_time || 0} 秒 | 
                    <i class="bi bi-star"></i> 质量评分: ${results.quality || 0}/100
                </p>
            </div>
        `;
        
        resultsContainer.style.display = 'block';
        resultsContainer.classList.add('fade-in');
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }
    
    setupResultButtons();
    resetUploadButton();
}

function setupResultButtons() {
    const viewBtn = document.getElementById('viewResultsBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    
    if (viewBtn) {
        viewBtn.onclick = () => {
            if (currentTaskId) {
                window.open(`/results/${currentTaskId}`, '_blank');
            }
        };
    }
    
    if (downloadBtn) {
        downloadBtn.onclick = () => {
            if (currentTaskId) {
                window.location.href = `/download/${currentTaskId}`;
            }
        };
    }
}

function setupProgressButtons() {
    // 设置进度相关按钮事件
    document.addEventListener('click', function(e) {
        if (e.target.id === 'viewResultsBtn' || e.target.closest('#viewResultsBtn')) {
            if (currentTaskId) {
                window.open(`/results/${currentTaskId}`, '_blank');
            }
        }
        
        if (e.target.id === 'downloadBtn' || e.target.closest('#downloadBtn')) {
            if (currentTaskId) {
                window.location.href = `/download/${currentTaskId}`;
            }
        }
    });
}

// ==================== 系统状态监控 ====================

function updateSystemStatus() {
    fetch('/system/status')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.warn('无法更新系统状态:', data.error);
                return;
            }

            const statusEl = document.getElementById('systemStatus');
            if (statusEl) {
                const gpuInfo = data.gpu_info !== 'N/A' 
                    ? ` | <i class="bi bi-gpu-card"></i> GPU: ${data.gpu_info[0].name.substring(0, 20)}...`
                    : '';

                statusEl.innerHTML = `
                    <span class="badge status-success me-2">在线</span>
                    <i class="bi bi-cpu"></i> CPU: ${data.cpu_usage.toFixed(1)}%
                    ${gpuInfo}
                `;
            }
        })
        .catch(error => console.warn('系统状态更新失败:', error));
}

// ==================== 监控面板 ====================

function showUploadTab() {
    const uploadTab = document.getElementById('uploadTab');
    const monitorTab = document.getElementById('monitorTab');
    
    if (uploadTab) uploadTab.style.display = 'block';
    if (monitorTab) monitorTab.style.display = 'none';
}

function showSystemMonitor() {
    const uploadTab = document.getElementById('uploadTab');
    const monitorTab = document.getElementById('monitorTab');
    
    if (uploadTab) uploadTab.style.display = 'none';
    if (monitorTab) {
        monitorTab.style.display = 'block';
        loadSystemMonitor();
    }
}

function loadSystemMonitor() {
    fetch('/system/status')
        .then(response => response.json())
        .then(data => {
            updateSystemResourcesDisplay(data);
            updateTaskStatsDisplay(data);
            updateQueueDetailsDisplay(data);
        })
        .catch(error => {
            console.error('加载系统监控失败:', error);
        });
}

function updateSystemResourcesDisplay(data) {
    const systemDiv = document.getElementById('systemResources');
    if (!systemDiv || !data.system) return;
    
    systemDiv.innerHTML = `
        <div class="mb-3">
            <div class="d-flex justify-content-between">
                <label class="form-label">CPU使用率</label>
                <span class="badge bg-primary">${data.system.cpu_percent}%</span>
            </div>
            <div class="progress">
                <div class="progress-bar" style="width: ${data.system.cpu_percent}%"></div>
            </div>
        </div>
        <div class="mb-3">
            <div class="d-flex justify-content-between">
                <label class="form-label">内存使用率</label>
                <span class="badge bg-info">${data.system.memory_percent}%</span>
            </div>
            <div class="progress">
                <div class="progress-bar bg-info" style="width: ${data.system.memory_percent}%"></div>
            </div>
        </div>
        <div class="mb-3">
            <label class="form-label">GPU状态</label>
            <p class="small mb-2">${data.system.gpu_available ? '✅ CUDA可用' : '❌ 仅CPU模式'}</p>
            ${data.system.gpu_memory ? `
                <div class="progress">
                    <div class="progress-bar bg-success" style="width: ${(data.system.gpu_memory.allocated_mb / data.system.gpu_memory.total_mb * 100)}%">
                        ${data.system.gpu_memory.allocated_mb}MB / ${data.system.gpu_memory.total_mb}MB
                    </div>
                </div>
            ` : ''}
        </div>
        <div>
            <label class="form-label">已加载模型</label>
            <p class="small"><span class="badge bg-secondary">${data.models_loaded}</span> 个模型实例</p>
        </div>
    `;
}

function updateTaskStatsDisplay(data) {
    const taskDiv = document.getElementById('taskStats');
    if (!taskDiv || !data.tasks) return;
    
    taskDiv.innerHTML = `
        <div class="row text-center">
            <div class="col-6 mb-3">
                <div class="h4 text-primary">${data.tasks.total}</div>
                <small class="text-muted">总任务数</small>
            </div>
            <div class="col-6 mb-3">
                <div class="h4 text-success">${data.tasks.completed}</div>
                <small class="text-muted">已完成</small>
            </div>
            <div class="col-6">
                <div class="h4 text-warning">${data.tasks.processing}</div>
                <small class="text-muted">处理中</small>
            </div>
            <div class="col-6">
                <div class="h4 text-danger">${data.tasks.error}</div>
                <small class="text-muted">失败</small>
            </div>
        </div>
    `;
}

function updateQueueDetailsDisplay(data) {
    const queueDiv = document.getElementById('queueDetails');
    if (!queueDiv || !data.queue) return;
    
    queueDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <strong>队列状态</strong>
                <p class="mb-0 text-muted">
                    当前队列: ${data.queue.queue_size} / ${data.queue.max_size}
                </p>
            </div>
            <span class="badge ${data.queue.is_full ? 'bg-danger' : 'bg-success'}">
                ${data.queue.is_full ? '队列已满' : '正常运行'}
            </span>
        </div>
    `;
}

// ==================== 工具函数 ====================

function showAlert(message, type = 'info') {
    // 创建alert元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 插入到页面顶部
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // 自动消失
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

function clearCache() {
    if (confirm('确定要清理缓存吗？这将删除所有历史任务数据。')) {
        fetch('/cleanup', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            showAlert(data.message || '缓存清理完成', 'success');
            updateSystemStatus();
        })
        .catch(error => {
            showAlert('清理缓存时出错: ' + error.message, 'danger');
        });
    }
}

// 导出函数供全局使用
window.showUploadTab = showUploadTab;
window.showSystemMonitor = showSystemMonitor;
window.clearCache = clearCache; 