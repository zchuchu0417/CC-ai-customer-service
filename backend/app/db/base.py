"""SQLAlchemy 声明性基类"""
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.db.mysql import engine


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


# 创建 session 工厂（注意：跟 SQLAlchemy 的 Session 是数据库会话，与业务的"对话会话" sessions 表无关）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖注入：每个请求开一个数据库会话，请求结束自动关"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()