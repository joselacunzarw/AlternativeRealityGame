import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.orchestrator import cases_db
from database.database import get_db
from database.models import GameSession, User

router = APIRouter()
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSETS_BASE_URL = (os.getenv("ASSETS_BASE_URL") or "/assets").rstrip("/")


class VaultUnlockRequest(BaseModel):
    code: str


def _build_asset_relative_path(case_id: str, evidence: dict) -> Path | None:
    if evidence.get("file_path"):
        return Path(str(evidence["file_path"]).replace("\\", "/"))

    file_name = evidence.get("file_name") or evidence.get("title")
    if not file_name:
        return None

    return Path(case_id) / file_name


def _resolve_asset_url(case_id: str, evidence: dict) -> str | None:
    relative_path = _build_asset_relative_path(case_id, evidence)
    if relative_path is None:
        return None

    asset_path = ASSETS_DIR / relative_path
    if not asset_path.is_file():
        return None

    encoded_path = "/".join(quote(part) for part in relative_path.parts)
    return f"{ASSETS_BASE_URL}/{encoded_path}"


@router.post("/vault/unlock")
async def unlock_evidence(
    req: VaultUnlockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Desencripta evidencia de la Boveda Forense.
    Busca el codigo en el vault_evidence del caso activo del jugador.
    """
    active_session = (
        db.query(GameSession)
        .filter(GameSession.user_id == current_user.id, GameSession.status == "active")
        .order_by(GameSession.started_at.desc())
        .first()
    )

    if not active_session:
        raise HTTPException(
            status_code=404,
            detail="No tiene ningun caso activo. Inicie un expediente antes de acceder a la Boveda.",
        )

    case_data = cases_db.get(active_session.game_id)
    if not case_data:
        raise HTTPException(
            status_code=404,
            detail="Caso no encontrado en el sistema.",
        )

    vault = case_data.get("vault_evidence", {})
    code_upper = req.code.strip().upper()
    evidence = vault.get(code_upper)
    if not evidence:
        raise HTTPException(
            status_code=400,
            detail="Clave criptografica invalida o revocada. Verifique el codigo proporcionado por sus contactos.",
        )

    response_evidence = {
        "title": evidence.get("title", "Archivo clasificado"),
        "type": evidence.get("type", "unknown"),
        "desc": evidence.get("desc", "Sin descripcion disponible."),
    }
    file_url = _resolve_asset_url(active_session.game_id, evidence)
    if file_url:
        response_evidence["file_url"] = file_url

    return {
        "success": True,
        "case_id": active_session.game_id,
        "evidence": response_evidence,
    }
