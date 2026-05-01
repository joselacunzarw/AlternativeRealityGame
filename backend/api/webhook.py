import os
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from models.schemas import InboundEmailPayload, AgentResponse
from core.orchestrator import app_graph, GameState
from langchain_core.messages import HumanMessage

router = APIRouter()

# Rate limiting compartido con el mismo parámetro que el IMAP poller.
RATE_LIMIT_PER_HOUR = int(os.getenv("IMAP_RATE_LIMIT_PER_HOUR", "20"))
_rate_counters: dict[str, list] = defaultdict(list)

def _is_rate_limited(from_email: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    window = 3600
    _rate_counters[from_email] = [t for t in _rate_counters[from_email] if now - t < window]
    if len(_rate_counters[from_email]) >= RATE_LIMIT_PER_HOUR:
        return True
    _rate_counters[from_email].append(now)
    return False


@router.post("/webhook/inbound", response_model=AgentResponse)
async def receive_inbound_email(payload: InboundEmailPayload):
    """
    Recibe el email parseado y lo envía al orquestador LangGraph.
    """
    if _is_rate_limited(payload.from_email):
        raise HTTPException(
            status_code=429,
            detail="Límite de mensajes por hora alcanzado. Intente más tarde."
        )

    email_body = f"Asunto: {payload.subject}\n\nCuerpo:\n{payload.text}"
    human_msg = HumanMessage(content=email_body)

    initial_state = {
        "from_email": payload.from_email,
        "to_email": payload.to_email,
        "subject": payload.subject,
        "text_content": payload.text,
        "messages": [human_msg]
    }

    # Mismo formato que imap_poller: thread_{from_email}_{char_alias}
    char_alias = payload.to_email.split("@")[0].lower()
    thread_id = f"thread_{payload.from_email}_{char_alias}"
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
