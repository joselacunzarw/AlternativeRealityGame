import re
from typing import Optional

from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import GameSession, User


_CASE_NUMBER_TO_ID = {
    "0": "caso_cero",
    "cero": "caso_cero",
    "1": "grabacion_1",
    "2": "herencia_2",
    "3": "martes_3",
    "4": "novia_4",
    "5": "experimento_5",
}


def _normalize_char_alias(to_email: str) -> str:
    return to_email.split("@")[0].strip().lower()


def build_session_thread_id(session_id: int, to_email: str) -> str:
    char_alias = _normalize_char_alias(to_email)
    return f"thread_session_{session_id}_{char_alias}"


def build_session_thread_pattern(session_id: int) -> str:
    return f"thread_session_{session_id}_%"


def build_case_thread_id(case_id: str, from_email: str, to_email: str) -> str:
    char_alias = _normalize_char_alias(to_email)
    return f"thread_case_{case_id}_{from_email.strip().lower()}_{char_alias}"


def build_email_thread_id(from_email: str, to_email: str) -> str:
    char_alias = _normalize_char_alias(to_email)
    return f"thread_email_{from_email.strip().lower()}_{char_alias}"


def build_legacy_email_thread_pattern(email: str) -> str:
    return f"thread_{email.strip().lower()}_%"


def build_fallback_email_thread_pattern(email: str) -> str:
    return f"thread_email_{email.strip().lower()}_%"


def resolve_inbound_thread_id(
    from_email: str,
    to_email: str,
    subject: str = "",
    text_content: str = "",
    db: Optional[Session] = None,
) -> str:
    """
    Resuelve el thread_id de LangGraph para un mensaje entrante.

    Prioridad:
      1. session_id de la GameSession activa del jugador
      2. case_id detectado en asunto/cuerpo (fallback QA)
      3. email + alias (ultimo recurso, sin guarantees de aislamiento entre casos)
    """
    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        session = _find_active_session(db, from_email)
        if session:
            return build_session_thread_id(session.id, to_email)
    finally:
        if own_db and db is not None:
            db.close()

    case_id = _detect_case_id(subject, text_content)
    if case_id:
        return build_case_thread_id(case_id, from_email, to_email)

    return build_email_thread_id(from_email, to_email)


def _find_active_session(db: Session, from_email: str) -> Optional[GameSession]:
    user = db.query(User).filter(User.email == from_email).first()
    if not user:
        return None

    return (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id, GameSession.status == "active")
        .order_by(GameSession.started_at.desc())
        .first()
    )


def _detect_case_id(subject: str, text_content: str) -> Optional[str]:
    combined = f"{subject or ''} {text_content or ''}".lower()
    if not combined.strip():
        return None

    from core.orchestrator import cases_db

    for case_id, case_data in cases_db.items():
        title = case_data.get("title", "").lower()
        if case_id in combined or (title and title in combined):
            return case_id

    case_match = re.search(r"caso\s*(\d+|cero)", combined)
    if case_match:
        return _CASE_NUMBER_TO_ID.get(case_match.group(1))

    return None
