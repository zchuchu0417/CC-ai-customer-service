"""健康检查接口"""
from fastapi import APIRouter
from app.config import settings
from app.db.mysql import check_mysql
from app.db.redis import check_redis
from app.db.qdrant import check_qdrant

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("", summary="服务存活检查")
def health():
    """最简健康检查 - 不查依赖，只看服务进程是否活着"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/full", summary="全栈连通性检查")
def health_full():
    """检查所有依赖的数据库"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "databases": {
            "mysql": check_mysql(),
            "redis": check_redis(),
            "qdrant": check_qdrant(),
        },
    }