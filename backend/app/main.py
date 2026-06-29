"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, sessions, messages

app = FastAPI(
    title="CC 商城 AI 客服 API",
    description="Enterprise AI Customer Service Q&A System",
    version=settings.app_version,
    docs_url="/docs",      # Swagger 文档
    redoc_url="/redoc",    # ReDoc 文档
)

# 跨域配置（开发环境放开所有 origin；生产前必须改回白名单）
# 注意：allow_credentials=True 与 allow_origins=["*"] 不能同时用
# 双击本地 HTML 文件时浏览器 origin = "null"，所以走"放开所有"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(messages.router)


@app.get("/", tags=["根路径"])
def root():
    return {
        "message": "Hello from CC AI Customer Service",
        "docs": "/docs",
        "health": "/health",
    }