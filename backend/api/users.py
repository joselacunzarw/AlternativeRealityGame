from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, GameSession
from core.orchestrator import cases_db

import random
from datetime import datetime, timedelta, timezone
from core.mailer import send_smtp_email
from core.security import create_access_token
from core.dependencies import get_current_user

router = APIRouter()

class OtpRequest(BaseModel):
    email: str

class OtpVerify(BaseModel):
    email: str
    code: str

@router.post("/auth/request-otp")
async def request_otp(req: OtpRequest, db: Session = Depends(get_db)):
    email = req.email.lower()
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        user = User(email=email)
        db.add(user)
    
    # Generar código de 6 dígitos
    code = str(random.randint(100000, 999999))
    user.otp_code = code
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Enviar correo de seguridad ANTES de persistir
    subject = "🔑 Código de Acceso - Agencia"
    body = f"DETECTIVE:\n\nSu código de autorización de un solo uso es:\n\n{code}\n\nIngréselo en la terminal segura. Este código se autodestruirá en 10 minutos."
    mail_sent = send_smtp_email(to_email=email, subject=subject, text_content=body)
    
    if not mail_sent:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="No se pudo enviar el código OTP. Verifica tu correo o intenta más tarde."
        )
    
    # Solo persistimos el OTP si el mail salió
    db.commit()
    return {"success": True, "message": "OTP enviado al correo."}

@router.post("/auth/verify-otp")
async def verify_otp(req: OtpVerify, db: Session = Depends(get_db)):
    email = req.email.lower()
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not user.otp_code:
        raise HTTPException(status_code=400, detail="Mala solicitud. Pida un código nuevo.")
        
    if user.otp_code != req.code:
        raise HTTPException(status_code=401, detail="Código incorrecto.")
        
    if datetime.now(timezone.utc) > user.otp_expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=401, detail="El código ha expirado.")
        
    # Verificar usuario y limpiar OTP
    user.is_verified = 1
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()
    
    # Emitir Token JWT seguro
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer", "email": user.email}

@router.get("/users/me/profile")
async def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = current_user
        
    sessions = db.query(GameSession).filter(GameSession.user_id == user.id).all()
    
    past_cases = []
    active_case = None
    
    for s in sessions:
        cdata = cases_db.get(s.game_id)
        case_title = cdata.get("title", s.game_id.upper()) if cdata else s.game_id.upper()
        
        session_info = {
            "session_id": s.id,
            "game_id": s.game_id,
            "title": case_title,
            "status": s.status,
            "started_at": s.started_at
        }
        
        if s.status == "active":
            active_case = session_info
        else:
            past_cases.append(session_info)
            
    # Computar metrics
    total_played = len(past_cases)
    abandoned = len([c for c in past_cases if c["status"] == "abandonado"])
    completed_success = len([c for c in past_cases if c["status"] == "completed_success"])
    completed_fail = len([c for c in past_cases if c["status"] == "completed_fail"])
    
    return {
        "email": user.email,
        "joined_at": user.created_at,
        "metrics": {
            "total_played": total_played,
            "abandoned": abandoned,
            "completed_success": completed_success,
            "completed_fail": completed_fail
        },
        "active_case": active_case,
        "history": past_cases
    }
