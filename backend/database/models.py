from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Autenticación Passwordless (OTP)
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_verified = Column(Integer, default=0) # 0=False, 1=True (SQLite)

class GameSession(Base):
    __tablename__ = "game_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_id = Column(String, index=True)  # ID del caso
    status = Column(String, default="active") # active, completed
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("game_sessions.id"))
    from_email = Column(String)
    to_email = Column(String)
    subject = Column(String)
    body = Column(Text)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    session = relationship("GameSession")
