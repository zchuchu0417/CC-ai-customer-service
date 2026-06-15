"""用户反馈模型"""
from datetime import datetime
from sqlalchemy import BigInteger, String, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("messages.id", ondelete="CASCADE"),
        unique=True, index=True,
    )
    type: Mapped[str] = mapped_column(
        Enum("like", "dislike", name="feedback_type")
    )
    reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    message: Mapped["Message"] = relationship(back_populates="feedback")