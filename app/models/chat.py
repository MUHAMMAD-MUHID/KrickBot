import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import ChatBase

def get_utc_now():
    return datetime.now(timezone.utc)

class ChatSession(ChatBase):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(ChatBase):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False) # 'user' or 'bot'
    content = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True) # E.g., 'FACTUAL', 'EXPLANATORY'
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    session = relationship("ChatSession", back_populates="messages")
