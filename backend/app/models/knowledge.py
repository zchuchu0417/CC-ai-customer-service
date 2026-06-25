"""知识库相关模型 - 文档元信息 + 切片

设计权衡（PM 视角）：
- 切片内容在 Qdrant 里也存了一份（payload），为什么 MySQL 还存？
  → 便于运营在管理后台浏览、搜索、批量删除
  → Qdrant 当作"纯向量索引"，业务数据落在 MySQL
  → 万一 Qdrant 挂了，MySQL 数据还在
"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Text, Integer, Enum, DateTime, ForeignKey, Index, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class KnowledgeDoc(Base):
    """知识库文档元信息（一篇 PDF/MD 对应一行）"""
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(512), comment="原始文件路径")
    category: Mapped[str] = mapped_column(
        String(64),
        index=True,
        comment="分类：退换货/物流/优惠券/会员/商品/客服/其他",
    )
    version: Mapped[str] = mapped_column(String(32), default="v1.0")
    status: Mapped[str] = mapped_column(
        Enum("active", "archived", name="doc_status"),
        default="active",
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="切片数量")
    total_chars: Mapped[int] = mapped_column(Integer, default=0, comment="原文总字符数")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 关系
    chunks: Mapped[list["DocChunk"]] = relationship(
        back_populates="doc", cascade="all, delete-orphan"
    )


class DocChunk(Base):
    """文档切片（一个 chunk 对应一个 Qdrant point）"""
    __tablename__ = "doc_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_docs.id", ondelete="CASCADE"),
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, comment="文档内序号 0,1,2...")
    content: Mapped[str] = mapped_column(Text, comment="切片正文")
    chunk_size: Mapped[int] = mapped_column(Integer, comment="字符数")
    section: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="所属章节（H1/H2 标题）"
    )
    vector_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, comment="Qdrant point id"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    doc: Mapped["KnowledgeDoc"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_doc_chunks_doc_index", "doc_id", "chunk_index"),
    )
