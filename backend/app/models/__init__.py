"""统一导入所有模型，让 Base.metadata 能发现它们"""
from app.models.user import User
from app.models.session import Session
from app.models.message import Message
from app.models.feedback import Feedback
from app.models.knowledge import KnowledgeDoc, DocChunk

__all__ = ["User", "Session", "Message", "Feedback", "KnowledgeDoc", "DocChunk"]