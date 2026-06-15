"""会话相关的 HTTP 接口"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DbSession
from app.db.base import get_db
from app.schemas.session import SessionCreate, SessionResponse, SessionListResponse
from app.services import session_service

router = APIRouter(prefix="/api/v1/sessions", tags=["会话管理"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新会话",
    description="""
    创建一个新的对话会话。

    **业务规则**：
    - 如果 user_id 对应的用户不存在，会自动创建一个测试用户（MVP 简化）
    - 不传 title 时，默认为「新对话」（首条消息发送后由 LLM 自动总结标题）
    - 新会话状态固定为 active
    """,
)
def create_session(
    payload: SessionCreate,
    db: DbSession = Depends(get_db),
):
    new_session = session_service.create_session(db, payload)
    return new_session


@router.get(
    "",
    response_model=SessionListResponse,
    summary="获取会话列表",
    description="按时间倒序返回指定用户的所有会话。",
)
def list_sessions(
    user_id: int = Query(default=1, ge=1, description="用户 ID"),
    limit: int = Query(default=20, ge=1, le=100, description="每页数量，1-100"),
    db: DbSession = Depends(get_db),
):
    total, items = session_service.list_sessions(db, user_id, limit)
    return SessionListResponse(total=total, items=items)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="获取单个会话详情",
)
def get_session(
    session_id: int,
    db: DbSession = Depends(get_db),
):
    session = session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在",
        )
    return session
