"""消息相关的业务逻辑

核心流程（chat 函数）：
    用户发消息 → 验证 session → 保存用户消息
                                   ↓
                          取最近 N 条上下文
                                   ↓
                            调用 LLM 生成回复
                                   ↓
              保存 AI 消息（含 tokens / latency / model）
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


# 系统提示词：定义 AI 的角色和约束
# 后续会移到数据库 / 配置中心方便运营调
SYSTEM_PROMPT = """你是 CC 商城的智能客服助手。请严格遵守：

1. 友好、克制、专业。用中文，简洁明了。
2. 涉及具体政策（退换货、物流、优惠券、商品参数）时，如果你不确定，告诉用户「让我帮您核实一下」，绝不编造。
3. 用户语气激烈或带负面情绪时，**先共情、再给方案**。
4. 严禁泄露内部信息（员工姓名、内部价格策略、系统配置等）。
5. 回答如超过 3 句话，用编号或分点列出，便于阅读。
"""

# 上下文窗口：给 LLM 最多取最近 10 条历史
# 太多会增加 token 成本和延迟；太少 AI 会失忆
MAX_HISTORY_MESSAGES = 10


def chat(
    db: DbSession,
    session_id: int,
    user_content: str,
) -> tuple[Message, Message]:
    """处理一轮"用户问 → AI 答"的完整对话"""

    # === Step 1: 验证 session 存在 ===
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

    # === Step 3: 构建 LLM 输入（system + 最近 N 条历史 + 当前问题）===
    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    history.reverse()  # 时间正序

    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        llm_messages.append({"role": msg.role, "content": msg.content})

    # === Step 4: 调 LLM ===
    try:
        result = llm_client.chat(messages=llm_messages)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 调用失败：{str(e)[:100]}",
        )

    # === Step 5: 保存 AI 消息 ===
    ai_msg = Message(
        session_id=session_id,
        role="assistant",
        content=result["content"],
        token_count=result["tokens"],
        model_name=result["model"],
        latency_ms=result["latency_ms"],
    )
    db.add(ai_msg)

    # === Step 6: 更新 session ===
    session.last_message_at = datetime.now()
    # 如果是首条消息，用用户问题做会话标题（前 30 字）
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
