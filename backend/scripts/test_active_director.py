import os
import sys
from pathlib import Path

# Agregar el directorio backend al PYTHONPATH
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from langchain_core.messages import HumanMessage, AIMessage
from core.orchestrator import app_graph, GameState

def test_active_director():
    print("=== INICIANDO PRUEBA DE DIRECTOR ACTIVO ===\n")
    
    # Vamos a simular un jugador que está atascado en el Caso 2 (La herencia)
    # y ha enviado ya 6 mensajes irrelevantes a Isabel Valente.
    
    messages_history = [
        HumanMessage(content="Hola Isabel, soy el detective del caso herencia 2."),
        AIMessage(content="Hola detective, dígame qué necesita."),
        HumanMessage(content="¿Cómo está el clima hoy?"),
        AIMessage(content="Nublado. ¿Tiene preguntas sobre mi padre?"),
        HumanMessage(content="¿Qué opina del color azul?"),
        AIMessage(content="Detective, esto es una pérdida de tiempo."),
        HumanMessage(content="¿Le gustan los perros?"),
        AIMessage(content="Prefiero los gatos. Por favor, centrémonos."),
        HumanMessage(content="¿A qué hora almuerza?"),
        AIMessage(content="A las 13:00. ¿Va a investigar o no?"),
        # ¡Este es el sexto mensaje! (human_count = 6)
        HumanMessage(content="¿Cree que va a llover mañana?")
    ]
    
    # Contamos mensajes humanos para asegurar que son 6
    human_count = sum(1 for m in messages_history if isinstance(m, HumanMessage))
    print(f"Mensajes del jugador en el historial: {human_count}")
    print("Debería activarse el Active Director en este turno...\n")
    
    state: GameState = {
        "from_email": "detective_test@gmail.com",
        "to_email": "isabel.valente@casos.expedienteabierto.com",
        "subject": "Caso 2 - herencia_2",
        "text_content": "¿Cree que va a llover mañana?",
        "messages": messages_history,
        "action_taken": None,
        "ai_response": None,
        "is_safe": None
    }
    
    import uuid
    thread_id = f"active_dir_test_{uuid.uuid4().hex[:6]}"
    print(f"Ejecutando grafo con thread_id: {thread_id}...")
    result = app_graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
    
    print(f"\n--- Resultado Final ---")
    
    # Revisamos el historial modificado para ver si se inyectó la instrucción secreta
    final_messages = result.get("messages", [])
    system_injected = False
    for m in final_messages:
        if m.type == "system" and "[MENSAJE DEL SISTEMA INVISIBLE" in m.content:
            system_injected = True
            print("\n[!] ¡Se encontró la instrucción inyectada del Director!")
            print(f"Contenido inyectado:\n{m.content}\n")
    
    if not system_injected:
        print("\n[x] No se encontró ninguna instrucción inyectada. ¿El jugador no fue detectado como atascado?")
        print(f"Action Taken: {result.get('action_taken')}")
        
    print(f"Action Taken final: {result.get('action_taken')}")
    print(f"Respuesta final del personaje (Isabel):\n{result.get('ai_response')}")
    print("\n=== PRUEBA FINALIZADA ===")

if __name__ == "__main__":
    test_active_director()
