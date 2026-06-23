"""消息相关的 HTTP 接口（嵌套在 sessions 下）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.db.base import get_db
from app.schemas.message import MessageCreate, MessageResponse, ChatResponse
from app.services import message_service

router = APIRouter(prefix="/api/v1/sessions", tags=["消息对话"])


@router.post(
    "/{session_id}/messages",
    response_model=ChatResponse,
    summary="发送消息（用户问 → AI 答）",
    description="""
在指定会话中发送一条用户消息，系统执行完整对话流程：

1. **保存用户消息** 到 messages 表
2. **取最近 10 条上下文**（支持多轮对话）
3. **调用 LLM** 生成回复
4. **保存 AI 回复**（含 tokens / latency / model_name 用于运营分析）
5. **更新 session** 的 last_message_at 和 title（首条消息）
6. 返回用户消息 + AI 回复两条记录

⚠️ 当前版本未接 RAG，AI 回答可能含模型幻觉。W3 接入知识库后会显著好转。
""",
)
def send_message(
    session_id: int,
    payload: MessageCreate,
    db: DbSession = Depends(get_db),
):
    user_msg, ai_msg = message_service.chat(db, session_id, payload.content)
    return ChatResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(ai_msg),
    )


@router.get(
    "/{session_id}/messages",
    response_model=list[MessageResponse],
    summary="获取会话内所有消息",
    description="按时间正序返回。前端打开会话时调用一次，加载历史对话。",
)
def list_messages(
    session_id: int,
    db: DbSession = Depends(get_db),
):
    return message_service.list_messages(db, session_id)
