from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.orchestrator import cases_db
from database.database import get_db
from database.models import User, GameSession
from core.mailer import send_smtp_email
from core.dependencies import get_current_user

router = APIRouter()

class StartGameRequest(BaseModel):
    user_email: str
    case_id: str

@router.get("/cases")
async def get_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Traer todos los game sessions de este usuario autenticado
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
        return {"success": False, "error": "Caso inexistente"}
        
    user = current_user

    # --- 2. ABANDONAR CASO ACTIVO PREVIO (REGLA DE PARTIDA ÚNICA) ---
    active_session = db.query(GameSession).filter(GameSession.user_id == user.id, GameSession.status == "active").first()
    if active_session:
        active_session.status = "abandonado"
        db.commit()

    # --- 3. REGISTRAR EL NUEVO CASO (NUEVA PARTIDA) ---
    session = GameSession(user_id=user.id, game_id=req.case_id, status="active")
    db.add(session)
    db.commit()
    
    # --- 3. DISPARAR PROTOCOLO SMTP GMAIL ---
    case_title = cdata.get("title", "Expediente")
    briefing = cdata.get("briefing_intro", "Nuevo caso asignado.")
    
    # Armamos la introducción del correo que llega al mail de jugador
    mail_subject = f"CASO ABIERTO: {case_title} || Expediente Abierto"
    mail_body = f"DETECTIVE:\n\nLe han asignado este expediente. Por favor, lea los detalles.\n\n{briefing}"
    
    mail_sent = send_smtp_email(req.user_email, mail_subject, mail_body)
    
    if mail_sent:
        return {
            "success": True, 
            "message": "Expediente inaugurado. Revisa tu casilla de correo Oficial de Agente.",
            "db_session_id": session.id
        }
    else:
        return {
            "success": False,
            "message": "Fallo el sistema de Correo. ¿Configuraste el .env en el servidor?"
        }
