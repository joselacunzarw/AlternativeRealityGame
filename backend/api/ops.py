import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.orchestrator import cases_db
from database.database import get_db
from database.models import (
    FiredEvent,
    GameSession,
    ProcessedInboundMessage,
    RateLimitEvent,
    ScheduledMessage,
    User,
)

router = APIRouter()


def _parse_allowlist() -> set[str]:
    raw = os.getenv("OPS_EMAIL_ALLOWLIST", "")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def require_ops_user(current_user: User = Depends(get_current_user)) -> User:
    allowlist = _parse_allowlist()
    if "*" not in allowlist and current_user.email.lower() not in allowlist:
        raise HTTPException(status_code=403, detail="Acceso operativo no autorizado.")
    return current_user


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _iso(value: datetime | None) -> str | None:
    aware = _as_aware(value)
    return aware.isoformat() if aware else None


def _case_title(case_id: str | None) -> str | None:
    if not case_id:
        return None
    case_data = cases_db.get(case_id)
    return case_data.get("title", case_id.upper()) if case_data else case_id.upper()


def _limit(value: int) -> int:
    return max(1, min(value, 200))


@router.get("/ops/summary")
def get_ops_summary(
    _: User = Depends(require_ops_user),
    db: Session = Depends(get_db),
):
    now = _now()
    last_hour = now - timedelta(hours=1)
    last_24h = now - timedelta(hours=24)

    status_rows = (
        db.query(GameSession.status, func.count(GameSession.id))
        .group_by(GameSession.status)
        .all()
    )
    sessions_by_status = {status or "unknown": count for status, count in status_rows}

    pending_messages = (
        db.query(ScheduledMessage)
        .filter(ScheduledMessage.is_delivered == False)
        .count()
    )
    overdue_messages = (
        db.query(ScheduledMessage)
        .filter(
            ScheduledMessage.is_delivered == False,
            ScheduledMessage.scheduled_at < now,
        )
        .count()
    )
    delivered_messages = (
        db.query(ScheduledMessage)
        .filter(ScheduledMessage.is_delivered == True)
        .count()
    )

    rate_rows = (
        db.query(RateLimitEvent.scope, func.count(RateLimitEvent.id))
        .filter(RateLimitEvent.created_at >= last_hour)
        .group_by(RateLimitEvent.scope)
        .all()
    )

    recent_inbound = (
        db.query(ProcessedInboundMessage)
        .order_by(ProcessedInboundMessage.processed_at.desc())
        .limit(5)
        .all()
    )

    return {
        "generated_at": _iso(now),
        "sessions_by_status": sessions_by_status,
        "active_sessions": sessions_by_status.get("active", 0),
        "pending_messages": pending_messages,
        "overdue_messages": overdue_messages,
        "delivered_messages": delivered_messages,
        "events_last_24h": (
            db.query(FiredEvent)
            .filter(FiredEvent.fired_at >= last_24h)
            .count()
        ),
        "rate_limits_last_hour": [
            {"scope": scope or "unknown", "count": count}
            for scope, count in rate_rows
        ],
        "inbound_last_24h": (
            db.query(ProcessedInboundMessage)
            .filter(ProcessedInboundMessage.processed_at >= last_24h)
            .count()
        ),
        "recent_inbound": [_serialize_inbound_message(row) for row in recent_inbound],
    }


@router.get("/ops/sessions")
def list_ops_sessions(
    _: User = Depends(require_ops_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = (
        db.query(GameSession, User.email)
        .join(User, GameSession.user_id == User.id)
        .order_by(GameSession.started_at.desc())
        .limit(_limit(limit))
        .all()
    )
    return {"sessions": [_serialize_session(session, email) for session, email in rows]}


@router.get("/ops/queue")
def list_ops_queue(
    _: User = Depends(require_ops_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = (
        db.query(ScheduledMessage, GameSession, User.email)
        .outerjoin(GameSession, ScheduledMessage.session_id == GameSession.id)
        .outerjoin(User, GameSession.user_id == User.id)
        .order_by(ScheduledMessage.is_delivered.asc(), ScheduledMessage.scheduled_at.asc())
        .limit(_limit(limit))
        .all()
    )
    return {
        "queue": [
            _serialize_scheduled_message(message, session, email)
            for message, session, email in rows
        ]
    }


@router.get("/ops/events")
def list_ops_events(
    _: User = Depends(require_ops_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = (
        db.query(FiredEvent, GameSession, User.email)
        .outerjoin(GameSession, FiredEvent.session_id == GameSession.id)
        .outerjoin(User, GameSession.user_id == User.id)
        .order_by(FiredEvent.fired_at.desc())
        .limit(_limit(limit))
        .all()
    )
    return {
        "events": [
            _serialize_fired_event(event, session, email)
            for event, session, email in rows
        ]
    }


@router.get("/ops/inbound")
def list_ops_inbound(
    _: User = Depends(require_ops_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    bounded_limit = _limit(limit)
    processed = (
        db.query(ProcessedInboundMessage)
        .order_by(ProcessedInboundMessage.processed_at.desc())
        .limit(bounded_limit)
        .all()
    )
    rate_limits = (
        db.query(RateLimitEvent)
        .order_by(RateLimitEvent.created_at.desc())
        .limit(bounded_limit)
        .all()
    )
    return {
        "processed": [_serialize_inbound_message(row) for row in processed],
        "rate_limits": [_serialize_rate_limit(row) for row in rate_limits],
    }


def _serialize_session(session: GameSession, user_email: str | None) -> dict:
    expires_at = _as_aware(session.expires_at)
    now = _now()
    return {
        "id": session.id,
        "user_email": user_email,
        "game_id": session.game_id,
        "case_title": _case_title(session.game_id),
        "status": session.status,
        "started_at": _iso(session.started_at),
        "expires_at": _iso(session.expires_at),
        "completed_at": _iso(session.completed_at),
        "verdict": session.verdict,
        "is_expired": bool(session.status == "active" and expires_at and expires_at < now),
    }


def _serialize_scheduled_message(
    message: ScheduledMessage,
    session: GameSession | None,
    user_email: str | None,
) -> dict:
    scheduled_at = _as_aware(message.scheduled_at)
    now = _now()
    is_overdue = bool(not message.is_delivered and scheduled_at and scheduled_at < now)
    minutes_overdue = None
    if is_overdue and scheduled_at:
        minutes_overdue = int((now - scheduled_at).total_seconds() // 60)

    return {
        "id": message.id,
        "session_id": message.session_id,
        "user_email": user_email,
        "game_id": session.game_id if session else None,
        "case_title": _case_title(session.game_id) if session else None,
        "from_email": message.from_email,
        "to_email": message.to_email,
        "subject": message.subject,
        "created_at": _iso(message.created_at),
        "scheduled_at": _iso(message.scheduled_at),
        "is_delivered": bool(message.is_delivered),
        "is_overdue": is_overdue,
        "minutes_overdue": minutes_overdue,
    }


def _serialize_fired_event(
    event: FiredEvent,
    session: GameSession | None,
    user_email: str | None,
) -> dict:
    return {
        "id": event.id,
        "session_id": event.session_id,
        "user_email": user_email,
        "game_id": session.game_id if session else None,
        "case_title": _case_title(session.game_id) if session else None,
        "event_id": event.event_id,
        "fired_at": _iso(event.fired_at),
    }


def _serialize_inbound_message(message: ProcessedInboundMessage) -> dict:
    return {
        "id": message.id,
        "source": message.source,
        "external_id": message.external_id,
        "from_email": message.from_email,
        "subject": message.subject,
        "processed_at": _iso(message.processed_at),
    }


def _serialize_rate_limit(event: RateLimitEvent) -> dict:
    return {
        "id": event.id,
        "scope": event.scope,
        "actor_email": event.actor_email,
        "created_at": _iso(event.created_at),
    }
