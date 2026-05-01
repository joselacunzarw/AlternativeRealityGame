from fastapi import APIRouter
from models.schemas import InboundEmailPayload, AgentResponse
from core.orchestrator import app_graph, GameState
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post("/webhook/inbound", response_model=AgentResponse)
async def receive_inbound_email(payload: InboundEmailPayload):
    """
    Recibe el email parseado y lo envía al orquestador LangGraph.
    """
    # Creamos un bloque coherente que simula el email de entrada humano
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
    # Garantiza que ambos canales compartan la misma memoria LangGraph.
    char_alias = payload.to_email.split("@")[0].lower()
    thread_id = f"thread_{payload.from_email}_{char_alias}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Ejecutar grafo guardando estado en hilo (MemorySaver)
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
