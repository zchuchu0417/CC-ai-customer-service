"""会话相关的业务逻辑

放在 service 层而不是 router 层的原因：
1. 业务规则可独立测试（不依赖 HTTP）
2. 不同入口（HTTP / 后台任务 / CLI）可复用同一段逻辑
3. router 只负责 "拿请求 → 调 service → 返回响应"，保持轻薄
"""
from sqlalchemy.orm import Session as DbSession
from app.models import User, Session as SessionModel
from app.schemas.session import SessionCreate


def ensure_user(db: DbSession, user_id: int = 1) -> User:
    """
    确保指定 user_id 的用户存在，不存在则创建一个测试用户。

    MVP 阶段为了简化，先用这个机制规避"必须先注册才能用"的复杂性。
    上线前会替换为真实的鉴权 + 注册流程。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user

    # 不存在 → 创建
    user = User(
        id=user_id,
        external_id=f"test_user_{user_id}",
        name=f"测试用户 {user_id}",
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(db: DbSession, payload: SessionCreate) -> SessionModel:
    """创建一个新的会话"""
    # Step 1: 确保用户存在（外键约束要求）
    ensure_user(db, payload.user_id)

    # Step 2: 写入会话
    new_session = SessionModel(
        user_id=payload.user_id,
        title=payload.title or "新对话",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def list_sessions(
    db: DbSession,
    user_id: int,
    limit: int = 20,
) -> tuple[int, list[SessionModel]]:
    """
    查询用户的会话列表，最近创建的在前。

    返回 (总数, 列表) 元组，方便前端做分页。
    """
    query = db.query(SessionModel).filter(SessionModel.user_id == user_id)
    total = query.count()
    items = (
        query.order_by(SessionModel.created_at.desc())
        .limit(limit)
        .all()
    )
    return total, items


def get_session(db: DbSession, session_id: int) -> SessionModel | None:
    """根据 ID 查询单个会话"""
    return db.query(SessionModel).filter(SessionModel.id == session_id).first()
