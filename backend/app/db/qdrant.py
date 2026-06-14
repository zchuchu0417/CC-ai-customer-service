"""Qdrant 向量库客户端"""
import httpx
from qdrant_client import QdrantClient
from app.config import settings

qdrant_client = QdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
)


def check_qdrant() -> str:
    """
    用 /collections 做健康检查。
    比 /healthz 更稳：Qdrant 任何版本都支持，
    返回 200 即代表服务能响应请求。
    """
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections"
            )
            if resp.status_code == 200:
                return "connected"
            return f"error: HTTP {resp.status_code}"
    except Exception as e:
        return f"error: {str(e)[:60]}"