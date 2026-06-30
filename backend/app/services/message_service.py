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
import json
import re
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.models import Message, Session as SessionModel
from app.services.llm_client import llm_client
from app.services import rag_service
from app.services.agent_tools import TOOL_SCHEMAS, execute_tool
from app.services.emotion_detector import detect_emotion, build_emotion_prompt


# 订单号正则（ORD + 至少 6 位数字）
ORDER_PATTERN = re.compile(r"\bORD\d{6,}\b", re.IGNORECASE)
# 转人工关键词
HUMAN_KEYWORDS = ["转人工", "转客服", "找客服", "找真人", "真人客服", "人工服务"]


def detect_forced_tool(user_content: str):
    """检测用户意图是否明确要求某个工具，返回 tool_choice 覆盖配置

    返回值：
        - dict 形如 {"type":"function","function":{"name":"..."}}：强制调某工具
        - "required"：强制调任意工具（让模型选）
        - None：不干预，让模型自由判断（tool_choice="auto"）
    """
    # 转人工是最强信号
    if any(kw in user_content for kw in HUMAN_KEYWORDS):
        return {"type": "function", "function": {"name": "escalate_to_human"}}

    has_order = bool(ORDER_PATTERN.search(user_content))
    has_refund_intent = any(kw in user_content for kw in ["退货", "退掉", "退款", "不要了", "退一下"])

    # 退货 + 订单号 → 强制调（先查后退是 AI 的事）
    if has_refund_intent and has_order:
        return "required"

    # 单纯含订单号 → 强制查订单
    if has_order:
        return {"type": "function", "function": {"name": "query_order"}}

    return None


# =============== System Prompt (RAG 版) ===============
# 关键约束：
# 1. 强制基于"参考资料"回答
# 2. 强制用【1】【2】格式引用
# 3. 缺资料时主动承认，绝不编造
RAG_SYSTEM_PROMPT = """你是 CC 商城智能客服。你的工作流程严格按以下决策树：

# 决策树（按顺序判断）

## 步骤 1：识别意图，决定是否调工具

如果用户的话**满足以下任一条件**，**必须立即调用对应工具**（不要先解释，不要说"稍等"，直接调）：

| 触发条件 | 必调工具 |
|---|---|
| 提到订单号（格式 ORD + 8 位数字，如 ORD20250603）| `query_order` |
| 明确要退货 / 退款 / 不想要了 + 有订单号 | 先 `query_order`，再 `create_return_request` |
| 说"转人工""找客服""真人"，或情绪非常激烈（辱骂/威胁/极度不满）| `escalate_to_human` |

⚠️ **铁律**：
- **绝不要说"正在调用工具""工具调用失败"这种话** —— 不存在的事不要编
- **绝不要凭空编造订单状态/物流位置/退货单号** —— 没调工具就如实说不知道
- 不知道订单号就问用户："请提供您的订单号（ORD 开头）"

## 步骤 2：不需要工具的问题，用知识库回答

如果不满足上面任何触发条件（如咨询政策、商品参数、客服时间等），用下方"参考资料"回答：
- 每条事实标【1】【2】引用
- 数字/日期/金额**原文复述**
- 答案简短（≤ 250 字）
- 参考资料没覆盖时直接说"未找到准确依据，建议联系人工客服"

## 步骤 3：用户有负面情绪时

不管走步骤 1 还是 2，回答开头**先共情一句**，再给方案。

---

# 参考资料（仅供步骤 2 使用，订单类问题用工具不用这里）

{rag_context}
"""

MAX_AGENT_TURNS = 4  # 防止工具调用死循环


# 上下文窗口：最近 10 条对话历史
MAX_HISTORY_MESSAGES = 10

# 招呼语关键词（命中则跳过 RAG，省 1 秒）
GREETING_PATTERNS = {
    "你好", "您好", "hi", "hello", "嗨", "在吗", "有人吗",
    "在么", "你是谁", "介绍一下", "测试", "test"
}


def is_simple_greeting(content: str) -> bool:
    """判断是否为简单问候，命中则跳过 RAG"""
    text = content.strip().lower()
    if len(text) > 15:  # 太长肯定不是单纯问候
        return False
    for pattern in GREETING_PATTERNS:
        if pattern in text:
            return True
    return False


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

    # 🚀 优化：立即推一帧 status，让用户 0ms 就看到反馈
    yield {
        "event": "status",
        "data": {"stage": "received", "message": "✓ 收到问题"},
    }

    # === 🆕 Step 2.5: 情绪检测（毫秒级，关键词词库匹配）===
    emotion = detect_emotion(user_content)
    if emotion["intensity"] >= 4:
        # 推 SSE 事件让前端/PM 可视化
        yield {
            "event": "emotion",
            "data": {
                "label": emotion["label"],
                "label_cn": emotion["label_cn"],
                "intensity": emotion["intensity"],
                "matched_keywords": emotion["matched_keywords"],
            },
        }
        # 更新 session 的 emotion_label 字段（运营回溯用）
        session.emotion_label = emotion["label"]
        # 强情绪自动升级 session 状态
        if emotion["intensity"] >= 7:
            session.status = "escalated"

    # === Step 3: RAG 检索（招呼语跳过）===
    relevant_chunks = []
    skip_rag = is_simple_greeting(user_content)

    if skip_rag:
        yield {
            "event": "status",
            "data": {"stage": "skip_rag", "message": "💬 简单问候，直接回答..."},
        }
    else:
        yield {
            "event": "status",
            "data": {"stage": "retrieving", "message": "🔍 检索知识库中..."},
        }
        try:
            relevant_chunks = rag_service.retrieve(user_content, top_k=5)
        except Exception as e:
            print(f"⚠️ RAG 检索失败: {e}")
            relevant_chunks = []

        yield {
            "event": "status",
            "data": {
                "stage": "retrieved",
                "message": f"📚 找到 {len(relevant_chunks)} 条相关资料",
            },
        }

    citations = rag_service.build_citations(relevant_chunks)

    yield {
        "event": "start",
        "data": {
            "user_message_id": user_msg.id,
            "citations": citations,
        },
    }

    # === Step 4: 构造 LLM 输入 ===
    if skip_rag:
        system_prompt = "你是 CC 商城的智能客服助手，友好、简洁、回答用中文。如需查询具体业务，请引导用户提供更多信息。"
    else:
        rag_context = rag_service.format_context(relevant_chunks)
        system_prompt = RAG_SYSTEM_PROMPT.format(rag_context=rag_context)

    # 🆕 情绪共情指令追加到 system prompt
    emotion_prompt = build_emotion_prompt(emotion)
    if emotion_prompt:
        system_prompt = system_prompt + emotion_prompt

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

    # === Step 5 (🆕 Agent 循环): AI 自主决定要不要调工具 ===
    # 招呼语跳过工具（用流式直接答）；其他场景走 Agent 主循环
    full_content = ""
    tokens = 0
    latency_ms = 0
    model_name = ""
    tool_calls_log = []

    if skip_rag:
        # 简单问候，纯流式
        yield {
            "event": "status",
            "data": {"stage": "generating", "message": "🤖 AI 正在回应..."},
        }
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
    else:
        # 业务问题：Agent 主循环（最多 4 轮，防工具死循环）
        # 检测用户意图，第一轮强制 tool_choice（防历史污染让模型不调工具）
        forced_tool_choice = detect_forced_tool(user_content)
        if forced_tool_choice:
            yield {
                "event": "status",
                "data": {
                    "stage": "force_tool",
                    "message": f"🎯 检测到明确意图，强制调用工具...",
                },
            }

        for turn in range(MAX_AGENT_TURNS):
            yield {
                "event": "status",
                "data": {
                    "stage": "generating",
                    "message": f"🤖 AI 正在思考{'（第 ' + str(turn + 1) + ' 轮）' if turn > 0 else '...'}",
                },
            }

            # 仅第一轮使用强制 tool_choice；后续轮恢复 auto（让 AI 决定何时结束）
            current_tool_choice = forced_tool_choice if turn == 0 else None

            try:
                result = llm_client.chat(
                    messages=llm_messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice=current_tool_choice,
                )
            except Exception as e:
                yield {"event": "error", "data": {"message": f"LLM 调用失败: {str(e)[:100]}"}}
                return

            tokens += result["tokens"]
            latency_ms += result["latency_ms"]
            model_name = result["model"]
            tool_calls = result.get("tool_calls")

            if not tool_calls:
                # 没工具调用 → 最终回答，"假流式"推送出去
                final_content = result["content"] or ""
                for ch in final_content:
                    full_content += ch
                    yield {"event": "token", "data": ch}
                break

            # 有工具调用 → 执行并回填
            llm_messages.append({
                "role": "assistant",
                "content": result["content"] or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except Exception:
                    tool_args = {}

                yield {
                    "event": "tool_call",
                    "data": {"name": tool_name, "args": tool_args},
                }

                tool_result = execute_tool(tool_name, tool_args)
                tool_calls_log.append({
                    "name": tool_name,
                    "args": tool_args,
                    "result": tool_result,
                })

                yield {
                    "event": "tool_result",
                    "data": {"name": tool_name, "result": tool_result},
                }

                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })
        else:
            # 4 轮都还在调工具 → 强制收尾
            full_content = "（Agent 调用次数超限，请重新提问或转人工）"
            yield {"event": "token", "data": full_content}

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
