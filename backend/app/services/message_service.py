"""消息相关的业务逻辑（RAG 增强版）

V2 流程（接入 RAG）：
    用户问 → 验证 session → 保存用户消息
                              ↓
                    🆕 RAG 检索（Top 5 chunks）
                              ↓
                    构造 system + 参考资料 + 历史 + 当前问题
                              ↓
                          调用 LLM
                              ↓
              🆕 保存 AI 消息（含 citations 字段）
                              ↓
                    更新 session.last_message_at
                              ↓
                    返回 (用户消息, AI 消息)
"""
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.models import Message, Session as SessionModel
from app.services.llm_client import llm_client
from app.services import rag_service


# =============== System Prompt (RAG 版) ===============
# 关键约束：
# 1. 强制基于"参考资料"回答
# 2. 强制用【1】【2】格式引用
# 3. 缺资料时主动承认，绝不编造
RAG_SYSTEM_PROMPT = """你是 CC 商城的智能客服助手。请严格遵守以下规则：

## 回答规则
1. **必须基于下方"参考资料"回答**，不允许编造任何信息（金额、日期、政策、流程等）
2. **必须用【1】【2】格式标注引用**，回答中出现的每个具体事实都要对应到参考资料的编号
3. 涉及金额、天数、百分比等数字时，**原文复述**，不要近似（如"7 天"不要说成"一周"）
4. 如果参考资料**无法回答**用户问题，明确告诉用户："抱歉，这个问题我没有找到准确依据，建议您联系人工客服。"
5. 用户语气激烈或带负面情绪时，**先共情、再给方案**
6. 回答用 markdown 格式，超过 3 句话时分点列出

## 参考资料

{rag_context}

---

请基于以上参考资料回答用户问题。
"""


# 上下文窗口：最近 10 条对话历史
MAX_HISTORY_MESSAGES = 10


def chat(
    db: DbSession,
    session_id: int,
    user_content: str,
) -> tuple[Message, Message]:
    """处理一轮 用户问 → RAG 检索 → AI 答 的完整流程"""

    # === Step 1: 验证 session ===
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在",
        )

    # === Step 2: 保存用户消息 ===
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # === Step 3 (🆕): RAG 检索 ===
    try:
        relevant_chunks = rag_service.retrieve(user_content, top_k=5)
    except Exception as e:
        # 检索失败时降级到无 RAG 回答（保可用性）
        print(f"⚠️ RAG 检索失败，降级为纯 LLM 回答: {e}")
        relevant_chunks = []

    # === Step 4: 构造 LLM 输入（system + 历史 + 当前）===
    rag_context = rag_service.format_context(relevant_chunks)
    system_prompt = RAG_SYSTEM_PROMPT.format(rag_context=rag_context)

    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    history.reverse()

    llm_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        llm_messages.append({"role": msg.role, "content": msg.content})

    # === Step 5: 调 LLM ===
    try:
        result = llm_client.chat(messages=llm_messages)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 调用失败：{str(e)[:100]}",
        )

    # === Step 6 (🆕): 保存 AI 消息（含 citations）===
    citations = rag_service.build_citations(relevant_chunks)

    ai_msg = Message(
        session_id=session_id,
        role="assistant",
        content=result["content"],
        citations=citations if citations else None,
        token_count=result["tokens"],
        model_name=result["model"],
        latency_ms=result["latency_ms"],
    )
    db.add(ai_msg)

    # === Step 7: 更新 session ===
    session.last_message_at = datetime.now()
    if session.title == "新对话" and len(history) <= 1:
        session.title = user_content[:30] + ("…" if len(user_content) > 30 else "")

    db.commit()
    db.refresh(ai_msg)

    return user_msg, ai_msg


def list_messages(db: DbSession, session_id: int) -> list[Message]:
    """获取一个会话的所有消息（时间正序）"""
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )


def chat_stream(
    db: DbSession,
    session_id: int,
    user_content: str,
):
    """流式对话生成器（V3 · SSE 版）

    Yields 事件序列：
        {"event": "start", "data": {"user_message_id": 123, "citations": [...]}}
        {"event": "token", "data": "你"}
        {"event": "token", "data": "好"}
        ...
        {"event": "done", "data": {"assistant_message_id": 124, "tokens": 357, ...}}
        {"event": "error", "data": {"message": "..."}}  ← 异常分支
    """
    # === Step 1: 验证 session ===
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id)
        .first()
    )
    if not session:
        yield {"event": "error", "data": {"message": f"会话 {session_id} 不存在"}}
        return

    # === Step 2: 保存用户消息 ===
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # === Step 3: RAG 检索 ===
    try:
        relevant_chunks = rag_service.retrieve(user_content, top_k=5)
    except Exception as e:
        print(f"⚠️ RAG 检索失败: {e}")
        relevant_chunks = []

    citations = rag_service.build_citations(relevant_chunks)

    # 先推送一帧：告诉前端"用户消息已存 + 引用拿到了"
    yield {
        "event": "start",
        "data": {
            "user_message_id": user_msg.id,
            "citations": citations,
        },
    }

    # === Step 4: 构造 LLM 输入 ===
    rag_context = rag_service.format_context(relevant_chunks)
    system_prompt = RAG_SYSTEM_PROMPT.format(rag_context=rag_context)

    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    history.reverse()
    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        llm_messages.append({"role": m.role, "content": m.content})

    # === Step 5: 流式调 LLM，逐 token 转发 ===
    full_content = ""
    tokens = 0
    latency_ms = 0
    model_name = ""

    try:
        for event in llm_client.chat_stream(messages=llm_messages):
            if event["type"] == "token":
                full_content += event["content"]
                yield {"event": "token", "data": event["content"]}
            elif event["type"] == "done":
                tokens = event["tokens"]
                latency_ms = event["latency_ms"]
                model_name = event["model"]
    except Exception as e:
        yield {"event": "error", "data": {"message": f"LLM 调用失败: {str(e)[:100]}"}}
        return

    # === Step 6: 流式结束，保存 AI 消息 ===
    ai_msg = Message(
        session_id=session_id,
        role="assistant",
        content=full_content,
        citations=citations if citations else None,
        token_count=tokens,
        model_name=model_name,
        latency_ms=latency_ms,
    )
    db.add(ai_msg)

    session.last_message_at = datetime.now()
    if session.title == "新对话" and len(history) <= 1:
        session.title = user_content[:30] + ("…" if len(user_content) > 30 else "")

    db.commit()
    db.refresh(ai_msg)

    # 最终 done 帧
    yield {
        "event": "done",
        "data": {
            "assistant_message_id": ai_msg.id,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "model": model_name,
        },
    }
