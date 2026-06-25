"""消息相关的 HTTP 接口（嵌套在 sessions 下）"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
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


@router.post(
    "/{session_id}/messages/stream",
    summary="🚀 流式发送消息（SSE）",
    description="""
**SSE (Server-Sent Events) 接口** —— AI 逐 token 推送，用户体感快 10 倍。

返回事件流（每行 `event: xxx` + `data: xxx`）：

```
event: start
data: {"user_message_id": 123, "citations": [...]}

event: token
data: 你

event: token
data: 好

...

event: done
data: {"assistant_message_id": 124, "tokens": 357, "latency_ms": 7158, "model": "..."}
```

⚠️ Swagger 不渲染 SSE 流。请用 curl 测试：
```bash
curl -N -X POST http://localhost:8000/api/v1/sessions/1/messages/stream \\
  -H "Content-Type: application/json" \\
  -d '{"content":"你好"}'
```
""",
)
def send_message_stream(
    session_id: int,
    payload: MessageCreate,
    db: DbSession = Depends(get_db),
):
    def event_generator():
        try:
            for event in message_service.chat_stream(db, session_id, payload.content):
                event_type = event["event"]
                data = event["data"]
                # SSE 标准格式：event: <type>\ndata: <json>\n\n
                if isinstance(data, str):
                    # token 是纯字符串，直接发
                    yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)[:200]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲（如有反代）
            "Connection": "keep-alive",
        },
    )
