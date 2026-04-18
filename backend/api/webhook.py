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
    
    # Identificador de la conversacion (ej. emisor -> receptor)
    thread_id = f"thread_{payload.from_email}_{payload.to_email}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Ejecutar grafo guardando estado en hilo (MemorySaver)
    result = app_graph.invoke(initial_state, config=config)
    
    return AgentResponse(
        success=True,
        action=result.get("action_taken", "unknown"),
        ai_response=result.get("ai_response", "Error al procesar.")
    )
