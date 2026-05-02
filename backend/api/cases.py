from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from core.orchestrator import cases_db
from database.database import get_db
from database.models import User, GameSession
from core.mailer import send_smtp_email
from core.dependencies import get_current_user

router = APIRouter()

class StartGameRequest(BaseModel):
    case_id: str
    # user_email eliminado: el destinatario del briefing es siempre current_user.email.
    # Aceptarlo desde el body permitía enviar contenido a terceros sin autorización.

@router.get("/cases")
async def get_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_sessions = {}
    sessions = db.query(GameSession).filter(GameSession.user_id == current_user.id).all()
    for s in sessions:
        user_sessions[s.game_id] = s.status

    caso_list = []
    for cid, cdata in cases_db.items():
        status = user_sessions.get(cid, "disponible")
        caso_list.append({
            "id": cdata.get("case_id", cid),
            "title": cdata.get("title", cid.upper()),
            "hours": cdata.get("duration_limit_hours", 48),
            "status": status,
            "desc": cdata.get("briefing_intro", "")[:120] + "..."
        })
    return {"cases": caso_list}

@router.post("/game/start")
async def start_case(req: StartGameRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cdata = cases_db.get(req.case_id)
    if not cdata:
        raise HTTPException(status_code=404, detail="Caso inexistente.")

    # --- 1. PREPARAR CAMBIOS EN DB (SIN COMMIT) ---
    active_session = db.query(GameSession).filter(
        GameSession.user_id == current_user.id,
        GameSession.status == "active"
    ).first()
    if active_session:
        active_session.status = "abandonado"

    duration_hours = cdata.get("duration_limit_hours", 72)
    session = GameSession(
        user_id=current_user.id,
        game_id=req.case_id,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=duration_hours)
    )
    db.add(session)
    db.flush()

    # --- 2. INTENTAR ENVÍO DE MAIL (siempre al usuario autenticado) ---
    case_title = cdata.get("title", "Expediente")
    briefing = cdata.get("briefing_intro", "Nuevo caso asignado.")

    mail_subject = f"CASO ABIERTO: {case_title} || Expediente Abierto"
    mail_body = f"DETECTIVE:\n\nLe han asignado este expediente. Por favor, lea los detalles.\n\n{briefing}"

    mail_sent = send_smtp_email(current_user.email, mail_subject, mail_body)

    if not mail_sent:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="No se pudo enviar el correo de briefing. El caso NO fue iniciado. Verifica la configuración SMTP."
        )

    # --- 3. COMMIT: Solo si el mail salió bien ---
    db.commit()

    return {
        "success": True,
        "message": "Expediente inaugurado. Revisa tu casilla de correo Oficial de Agente.",
        "db_session_id": session.id
    }
