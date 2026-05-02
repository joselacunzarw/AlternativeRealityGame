from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import ProcessedInboundMessage, RateLimitEvent


def has_processed_messages(source: str, db: Optional[Session] = None) -> bool:
    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        return (
            db.query(ProcessedInboundMessage.id)
            .filter(ProcessedInboundMessage.source == source)
            .first()
            is not None
        )
    finally:
        if own_db:
            db.close()


def get_unprocessed_message_ids(
    source: str,
    external_ids: list[str],
    db: Optional[Session] = None,
) -> list[str]:
    normalized_ids = [str(eid) for eid in external_ids if eid]
    if not normalized_ids:
        return []

    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        known_rows = (
            db.query(ProcessedInboundMessage.external_id)
            .filter(
                ProcessedInboundMessage.source == source,
                ProcessedInboundMessage.external_id.in_(normalized_ids),
            )
            .all()
        )
        known_ids = {row[0] for row in known_rows}
        return [eid for eid in normalized_ids if eid not in known_ids]
    finally:
        if own_db:
            db.close()


def seed_processed_message_ids(
    source: str,
    external_ids: list[str],
    db: Optional[Session] = None,
) -> int:
    normalized_ids = []
    seen = set()
    for external_id in external_ids:
        normalized = str(external_id)
        if normalized and normalized not in seen:
            normalized_ids.append(normalized)
            seen.add(normalized)

    if not normalized_ids:
        return 0

    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        existing_rows = (
            db.query(ProcessedInboundMessage.external_id)
            .filter(
                ProcessedInboundMessage.source == source,
                ProcessedInboundMessage.external_id.in_(normalized_ids),
            )
            .all()
        )
        existing_ids = {row[0] for row in existing_rows}
        missing_ids = [external_id for external_id in normalized_ids if external_id not in existing_ids]

        for external_id in missing_ids:
            db.add(
                ProcessedInboundMessage(
                    source=source,
                    external_id=external_id,
                )
            )
        db.commit()
        return len(missing_ids)
    except Exception:
        db.rollback()
        raise
    finally:
        if own_db:
            db.close()


def mark_message_processed(
    source: str,
    external_id: str,
    from_email: Optional[str] = None,
    subject: Optional[str] = None,
    db: Optional[Session] = None,
) -> bool:
    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        db.add(
            ProcessedInboundMessage(
                source=source,
                external_id=str(external_id),
                from_email=from_email,
                subject=subject,
            )
        )
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    finally:
        if own_db:
            db.close()


def is_rate_limited(
    actor_email: str,
    scope: str,
    limit: int,
    window_seconds: int = 3600,
    db: Optional[Session] = None,
) -> bool:
    normalized_email = actor_email.strip().lower()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)

    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        (
            db.query(RateLimitEvent)
            .filter(RateLimitEvent.created_at < cutoff)
            .delete(synchronize_session="fetch")
        )

        current_count = (
            db.query(RateLimitEvent)
            .filter(
                RateLimitEvent.scope == scope,
                RateLimitEvent.actor_email == normalized_email,
                RateLimitEvent.created_at >= cutoff,
            )
            .count()
        )

        if current_count >= limit:
            db.commit()
            return True

        db.add(
            RateLimitEvent(
                scope=scope,
                actor_email=normalized_email,
            )
        )
        db.commit()
        return False
    except Exception:
        db.rollback()
        raise
    finally:
        if own_db:
            db.close()


def clear_runtime_state(db: Optional[Session] = None) -> None:
    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        db.query(ProcessedInboundMessage).delete(synchronize_session=False)
        db.query(RateLimitEvent).delete(synchronize_session=False)
        db.commit()
    finally:
        if own_db:
            db.close()
