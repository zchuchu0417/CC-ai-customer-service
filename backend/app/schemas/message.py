"""消息相关的 Pydantic 数据模型"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any


class MessageCreate(BaseModel):
    """用户发起一条消息"""
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户输入的消息内容",
        examples=["我的订单 ORD20250603 到哪了？"],
    )


class MessageResponse(BaseModel):
    """单条消息（用户或 AI）"""
    id: int
    session_id: int
    role: str
    content: str
    citations: Any = None  # JSON 字段，list[dict] 或 None
    token_count: int | None = None
    model_name: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),  # 允许 model_name 这种字段名
    }


class ChatResponse(BaseModel):
    """POST /messages 的完整响应：包含用户消息 + AI 回复两条记录"""
    user_message: MessageResponse
    assistant_message: MessageResponse
