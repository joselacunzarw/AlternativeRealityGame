from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    otp_attempts = Column(Integer, default=0)  # Reintentos fallidos; se resetea al verificar
    is_verified = Column(Integer, default=0) # 0=False, 1=True (SQLite)

class GameSession(Base):
    __tablename__ = "game_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_id = Column(String, index=True)  # ID del caso
    status = Column(String, default="active") # active, completed, abandonado, failed_timeout
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True, index=True)  # Guardián de Tiempo
    
    # Metadata de cierre (poblada por el Director al evaluar)
    completed_at = Column(DateTime, nullable=True)
    verdict = Column(String, nullable=True)       # ej: "win_a", "win_b", "lose_c", "partial"
    director_summary = Column(Text, nullable=True) # Respuesta completa del Director
    
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

class FiredEvent(Base):
    """
    Registro de eventos proactivos ya disparados por el Event Engine.
    Evita que un evento con max_fires=1 se dispare más de una vez por sesión.
    """
    __tablename__ = "fired_events"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("game_sessions.id"), index=True)
    event_id = Column(String, index=True)  # Coincide con proactive_events[].id del JSON
    fired_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("GameSession")


class ScheduledMessage(Base):
    """
    Mensajes en "limbo" — generados por la IA pero aún no entregados al jugador.
    El Time Guardian los libera cuando scheduled_at <= now().
    """
    __tablename__ = "scheduled_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("game_sessions.id"), index=True)
    from_email = Column(String)
    to_email = Column(String)
    subject = Column(String)
    body = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    scheduled_at = Column(DateTime, index=True)   # Cuándo debe "llegar"
    is_delivered = Column(Boolean, default=False)  # Ya fue movido a Message
    
    session = relationship("GameSession")


class ProcessedInboundMessage(Base):
    """
    Marca mensajes entrantes ya vistos por el sistema para evitar reprocesarlos
    cuando el servidor se reinicia.
    """
    __tablename__ = "processed_inbound_messages"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_processed_inbound_source_external"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)  # ej: "imap_uid"
    external_id = Column(String, nullable=False, index=True)  # UID del proveedor
    from_email = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class RateLimitEvent(Base):
    """
    Eventos persistidos para aplicar rate limiting aunque el proceso se reinicie.
    El scope permite mantener presupuestos separados por canal (imap/webhook).
    """
    __tablename__ = "rate_limit_events"
    __table_args__ = (
        Index("ix_rate_limit_scope_actor_created", "scope", "actor_email", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String, nullable=False, index=True)
    actor_email = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class DetectiveNotebookEntry(Base):
    """
    Entradas persistentes del cuaderno del detective.
    Pertenecen a un usuario y a una sesion para evitar cruces entre partidas.
    """
    __tablename__ = "detective_notebook_entries"
    __table_args__ = (
        Index("ix_notebook_user_session_type", "user_id", "session_id", "entry_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False, index=True)
    entry_type = Column(String, nullable=False, index=True)  # note, suspect, timeline, vault_code
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user = relationship("User")
    session = relationship("GameSession")
