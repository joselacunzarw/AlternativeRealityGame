from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.orchestrator import cases_db
from database.database import get_db
from database.models import User, GameSession
from core.dependencies import get_current_user

router = APIRouter()

class VaultUnlockRequest(BaseModel):
    code: str

@router.post("/vault/unlock")
async def unlock_evidence(req: VaultUnlockRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Desencripta evidencia de la Bóveda Forense.
    Busca el código en el vault_evidence del caso activo del jugador.
    """
    # 1. Buscar la sesión activa del usuario
    active_session = (
        db.query(GameSession)
        .filter(GameSession.user_id == current_user.id, GameSession.status == "active")
        .order_by(GameSession.started_at.desc())
        .first()
    )
    
    if not active_session:
        raise HTTPException(
            status_code=404,
            detail="No tiene ningún caso activo. Inicie un expediente antes de acceder a la Bóveda."
        )
    
    # 2. Obtener los datos del caso
    case_data = cases_db.get(active_session.game_id)
    if not case_data:
        raise HTTPException(
            status_code=404,
            detail="Caso no encontrado en el sistema."
        )
    
    # 3. Buscar el código en vault_evidence (case-insensitive)
    vault = case_data.get("vault_evidence", {})
    code_upper = req.code.strip().upper()
    
    evidence = vault.get(code_upper)
    if not evidence:
        raise HTTPException(
            status_code=400,
            detail="Clave criptográfica inválida o revocada. Verifique el código proporcionado por sus contactos."
        )
    
    # 4. Devolver la evidencia desbloqueada
    return {
        "success": True,
        "case_id": active_session.game_id,
        "evidence": {
            "title": evidence.get("title", "Archivo clasificado"),
            "type": evidence.get("type", "unknown"),
            "desc": evidence.get("desc", "Sin descripción disponible."),
        }
    }
