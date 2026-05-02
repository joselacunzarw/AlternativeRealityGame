from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.orchestrator import cases_db
from database.database import get_db
from database.models import DetectiveNotebookEntry, GameSession, User

router = APIRouter()

VALID_ENTRY_TYPES = {"note", "suspect", "timeline", "vault_code"}


class NotebookEntryCreate(BaseModel):
    entry_type: str
    title: str
    content: str = ""
    session_id: int | None = None


class NotebookEntryUpdate(BaseModel):
    entry_type: str | None = None
    title: str | None = None
    content: str | None = None


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


def _active_session(db: Session, user: User) -> GameSession | None:
    return (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id, GameSession.status == "active")
        .order_by(GameSession.started_at.desc())
        .first()
    )


def _session_for_user(db: Session, user: User, session_id: int | None) -> GameSession | None:
    if session_id is None:
        return _active_session(db, user)
    return (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id, GameSession.id == session_id)
        .first()
    )


def _normalize_entry_type(entry_type: str | None) -> str | None:
    if entry_type is None:
        return None
    normalized = entry_type.strip().lower()
    if normalized not in VALID_ENTRY_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de entrada invalido. Use note, suspect, timeline o vault_code.",
        )
    return normalized


def _normalize_title(title: str | None) -> str | None:
    if title is None:
        return None
    normalized = title.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="El titulo de la entrada es obligatorio.")
    if len(normalized) > 140:
        raise HTTPException(status_code=400, detail="El titulo no puede superar 140 caracteres.")
    return normalized


def _normalize_content(content: str | None) -> str:
    if content is None:
        return ""
    return content.strip()


def _serialize_session(session: GameSession | None) -> dict | None:
    if session is None:
        return None
    return {
        "id": session.id,
        "game_id": session.game_id,
        "case_title": _case_title(session.game_id),
        "status": session.status,
        "started_at": _iso(session.started_at),
        "expires_at": _iso(session.expires_at),
    }


def _serialize_entry(entry: DetectiveNotebookEntry) -> dict:
    return {
        "id": entry.id,
        "session_id": entry.session_id,
        "entry_type": entry.entry_type,
        "title": entry.title,
        "content": entry.content or "",
        "created_at": _iso(entry.created_at),
        "updated_at": _iso(entry.updated_at),
    }


@router.get("/notebook")
def list_notebook_entries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    session_id: int | None = Query(default=None),
    entry_type: str | None = Query(default=None),
):
    session = _session_for_user(db, current_user, session_id)
    if session_id is not None and session is None:
        raise HTTPException(status_code=404, detail="Sesion no encontrada para este usuario.")
    if session is None:
        return {
            "active_session": None,
            "entries": [],
            "message": "No hay un expediente activo para asociar notas.",
        }

    normalized_type = _normalize_entry_type(entry_type)
    query = (
        db.query(DetectiveNotebookEntry)
        .filter(
            DetectiveNotebookEntry.user_id == current_user.id,
            DetectiveNotebookEntry.session_id == session.id,
        )
    )
    if normalized_type:
        query = query.filter(DetectiveNotebookEntry.entry_type == normalized_type)

    entries = query.order_by(DetectiveNotebookEntry.updated_at.desc()).all()
    return {
        "active_session": _serialize_session(session),
        "entries": [_serialize_entry(entry) for entry in entries],
    }


@router.post("/notebook")
def create_notebook_entry(
    payload: NotebookEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _session_for_user(db, current_user, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Inicie un expediente antes de crear notas.")

    entry = DetectiveNotebookEntry(
        user_id=current_user.id,
        session_id=session.id,
        entry_type=_normalize_entry_type(payload.entry_type),
        title=_normalize_title(payload.title),
        content=_normalize_content(payload.content),
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "success": True,
        "entry": _serialize_entry(entry),
        "active_session": _serialize_session(session),
    }


@router.patch("/notebook/{entry_id}")
def update_notebook_entry(
    entry_id: int,
    payload: NotebookEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(DetectiveNotebookEntry)
        .filter(
            DetectiveNotebookEntry.id == entry_id,
            DetectiveNotebookEntry.user_id == current_user.id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada.")

    if payload.entry_type is not None:
        entry.entry_type = _normalize_entry_type(payload.entry_type)
    if payload.title is not None:
        entry.title = _normalize_title(payload.title)
    if payload.content is not None:
        entry.content = _normalize_content(payload.content)
    entry.updated_at = _now()

    db.commit()
    db.refresh(entry)
    return {"success": True, "entry": _serialize_entry(entry)}


@router.delete("/notebook/{entry_id}")
def delete_notebook_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(DetectiveNotebookEntry)
        .filter(
            DetectiveNotebookEntry.id == entry_id,
            DetectiveNotebookEntry.user_id == current_user.id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada.")

    db.delete(entry)
    db.commit()
    return {"success": True, "deleted_id": entry_id}
