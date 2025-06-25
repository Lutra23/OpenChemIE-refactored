"""
OpenChemIE FastAPI 主应用
集成所有路由、中间件和启动配置
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import from_url as redis_from_url

from .deps import get_settings, task_status
from .services.extractor import initialize_queue_and_workers
from .routers import upload, tasks, system

# 创建 FastAPI 应用实例
app = FastAPI(
    title="OpenChemIE API",
    description="化学信息提取API服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(upload.router, prefix="/api", tags=["文件上传"])
app.include_router(tasks.router, prefix="/api", tags=["任务管理"])
app.include_router(system.router, prefix="/api", tags=["系统监控"])

@app.get("/")
def read_root():
    """根路径，返回API信息"""
    return {
        "message": "Welcome to OpenChemIE API",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    print("🚀 启动 OpenChemIE API...")
    
    # 获取设置
    settings = get_settings()
    
    # 初始化 Redis 缓存
    print(f"🔌 连接到 Redis: {settings.redis_url}")
    try:
        redis = redis_from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        app.state.redis = redis
        print("✅ Redis 缓存已初始化")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        app.state.redis = None
    
    print(f"📁 上传目录: {settings.upload_folder}")
    print(f"📁 结果目录: {settings.results_folder}")
    print(f"⚙️  最大并发任务: {settings.max_concurrent_tasks}")
    print(f"📦 队列大小: {settings.task_queue_size}")
    
    # 初始化任务队列和工作线程，并将其存储在 app.state 中
    app.state.task_queue = initialize_queue_and_workers(settings, task_status)
    
    print("✅ OpenChemIE API 启动完成!")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    print("🛑 正在关闭 OpenChemIE API...")
    
    # 关闭 Redis 连接
    if hasattr(app.state, 'redis') and app.state.redis:
        await app.state.redis.close()
        print("🔌 Redis 连接已关闭")

    # 这里可以添加清理逻辑，如停止工作线程等
    # 注意：由于使用了daemon线程，应用关闭时线程会自动结束
    
    print("✅ OpenChemIE API 已关闭")

if __name__ == "__main__":
    # 直接运行时的配置
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 