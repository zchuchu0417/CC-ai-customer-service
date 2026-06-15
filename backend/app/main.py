"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, sessions

app = FastAPI(
    title="CC 商城 AI 客服 API",
    description="Enterprise AI Customer Service Q&A System",
    version=settings.app_version,
    docs_url="/docs",      # Swagger 文档
    redoc_url="/redoc",    # ReDoc 文档
)

# 跨域配置（前端调后端时需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router)
app.include_router(sessions.router)


@app.get("/", tags=["根路径"])
def root():
    return {
        "message": "Hello from CC AI Customer Service",
        "docs": "/docs",
        "health": "/health",
    }