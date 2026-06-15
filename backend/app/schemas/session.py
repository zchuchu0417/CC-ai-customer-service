"""会话相关的 Pydantic 数据模型

Pydantic 模型负责"对外的接口契约":
- Request 模型：检查前端传进来的数据格式
- Response 模型：决定接口返回什么字段
和 SQLAlchemy ORM 模型解耦，避免数据库结构泄露给前端。
"""
from datetime import datetime
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """创建会话的请求体"""
    user_id: int = Field(
        default=1,
        description="用户 ID（MVP 暂用 1，未来接入鉴权后从 JWT 拿）",
        examples=[1],
    )
    title: str | None = Field(
        default=None,
        description="会话标题，不传则默认「新对话」",
        examples=["关于退换货的咨询"],
        max_length=128,
    )


class SessionResponse(BaseModel):
    """会话信息的响应体"""
    id: int
    user_id: int
    title: str
    status: str
    emotion_label: str | None
    created_at: datetime
    last_message_at: datetime | None

    # Pydantic v2 允许从 ORM 对象自动转换
    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """会话列表响应（包装一层方便扩展分页字段）"""
    total: int
    items: list[SessionResponse]
