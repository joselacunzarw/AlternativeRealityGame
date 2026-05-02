import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.conversation_threads import resolve_inbound_thread_id
from core.inbound_runtime_state import is_rate_limited as persistent_is_rate_limited
from database.database import get_db
from models.schemas import InboundEmailPayload, AgentResponse
from core.orchestrator import app_graph, GameState
from core.email_reply_parser import extract_visible_reply
from langchain_core.messages import HumanMessage

router = APIRouter()

# Rate limiting compartido con el mismo parámetro que el IMAP poller.
RATE_LIMIT_PER_HOUR = int(os.getenv("IMAP_RATE_LIMIT_PER_HOUR", "20"))

def _is_rate_limited(from_email: str, db: Session) -> bool:
    return persistent_is_rate_limited(
        actor_email=from_email,
        scope="webhook",
        limit=RATE_LIMIT_PER_HOUR,
        db=db,
    )


@router.post("/webhook/inbound", response_model=AgentResponse)
async def receive_inbound_email(payload: InboundEmailPayload, db: Session = Depends(get_db)):
    """
    Recibe el email parseado y lo envía al orquestador LangGraph.
    """
    if _is_rate_limited(payload.from_email, db=db):
        raise HTTPException(
            status_code=429,
            detail="Límite de mensajes por hora alcanzado. Intente más tarde."
        )

    clean_text = extract_visible_reply(payload.text)
    email_body = f"Asunto: {payload.subject}\n\nCuerpo:\n{clean_text}"
    human_msg = HumanMessage(content=email_body)

    initial_state = {
        "from_email": payload.from_email,
        "to_email": payload.to_email,
        "subject": payload.subject,
        "text_content": clean_text,
        "messages": [human_msg]
    }

    thread_id = resolve_inbound_thread_id(
        from_email=payload.from_email,
        to_email=payload.to_email,
        subject=payload.subject,
        text_content=clean_text,
        db=db,
    )
    config = {"configurable": {"thread_id": thread_id}}

    result = app_graph.invoke(initial_state, config=config)

    action = result.get("action_taken", "unknown")

    if action == "time_guardian_queued":
        return AgentResponse(
            success=True,
            action="time_guardian_queued",
            ai_response="Respuesta encolada. El personaje responderá con latencia realista."
        )

    return AgentResponse(
        success=True,
        action=action,
        ai_response=result.get("ai_response", "Error al procesar.")
    )
