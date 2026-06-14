"""MySQL 连接池（SQLAlchemy）"""
from sqlalchemy import create_engine, text
from app.config import settings

# 创建数据库引擎（连接池）
engine = create_engine(
    settings.mysql_url,
    pool_size=5,
    pool_pre_ping=True,  # 用前 ping 一下，避免连接失效
    echo=False,
)


def check_mysql() -> str:
    """连通性测试"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as e:
        return f"error: {str(e)[:60]}"