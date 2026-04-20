import os
import json
from pathlib import Path
from typing import Annotated, TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()

CASES_DIR = Path(__file__).parent.parent / "casos"

characters_db = {}
cases_db = {}

if CASES_DIR.exists():
    for case_file in CASES_DIR.glob("*.json"):
        try:
            with open(case_file, "r", encoding="utf-8") as f:
                case_data = json.load(f)
                case_id = case_data.get("case_id", case_file.stem)
                cases_db[case_id] = case_data
                
                chars = case_data.get("characters", {})
                for alias, info in chars.items():
                    info["parent_case_id"] = case_id
                    characters_db[alias] = info
        except Exception as e:
            print(f"Error cargando {case_file.name}: {e}")

class GameState(TypedDict):
    from_email: str
    to_email: str
    subject: str
    text_content: str
    messages: Annotated[list[BaseMessage], add_messages] # Manejo aut. de historial
    action_taken: Optional[str]
    ai_response: Optional[str]

def route_email(state: GameState):
    to_email = state.get("to_email", "")
    username = to_email.split("@")[0].lower()
    if "juez" in username or "director" in username or "expediente" in username:
        return "director_node"
    else:
        return "character_node"

def director_process(state: GameState):
    """
    El Director evalúa la resolución del detective usando la lógica
    definida en el JSON del caso (win_conditions, lose_conditions).
    """
    # Determinar qué caso está jugando el detective
    # Buscamos en el historial de mensajes pistas sobre el caso activo
    from_email = state.get("from_email", "")
    text = state.get("text_content", "")
    subject = state.get("subject", "")
    
    # Intentar determinar el caso desde el asunto ("Resolución — Caso 3")
    active_case_data = None
    active_case_id = None
    
    # Buscar por patrón "Caso X" o "caso_id" en el asunto
    subject_lower = subject.lower() if subject else ""
    text_lower = text.lower() if text else ""
    combined = subject_lower + " " + text_lower
    
    for cid, cdata in cases_db.items():
        # Match por case_id directo o por título del caso
        title_lower = cdata.get("title", "").lower()
        if cid in combined or title_lower in combined:
            active_case_data = cdata
            active_case_id = cid
            break
    
    # Fallback: buscar por número de caso ("caso 1", "caso 3", etc.)
    if not active_case_data:
        import re
        caso_match = re.search(r'caso\s*(\d+)', combined)
        if caso_match:
            caso_num = caso_match.group(1)
            # Mapear "caso 0" -> "caso_cero", "caso 1" -> "grabacion_1", etc.
            num_to_id = {
                "0": "caso_cero", "cero": "caso_cero",
                "1": "grabacion_1",
                "2": "herencia_2",
                "3": "martes_3",
                "4": "novia_4",
                "5": "experimento_5"
            }
            mapped_id = num_to_id.get(caso_num)
            if mapped_id and mapped_id in cases_db:
                active_case_data = cases_db[mapped_id]
                active_case_id = mapped_id
    
    # Si no encontramos caso, responder genérico
    if not active_case_data:
        return {
            "action_taken": "director_no_case",
            "ai_response": (
                "Detective,\n\n"
                "No hemos podido identificar a qué expediente se refiere su comunicación. "
                "Por favor, reenvíe su resolución indicando el nombre o número de caso en el asunto.\n\n"
                "Formato esperado: 'Resolución — Caso [número]'\n\n"
                "— La Dirección"
            )
        }
    
    # Cargar la lógica del director
    director_logic = active_case_data.get("director_logic", {})
    win_conditions = director_logic.get("win_conditions", "No definidas.")
    lose_conditions = director_logic.get("lose_conditions", "No definidas.")
    case_title = active_case_data.get("title", active_case_id)
    
    # Construir el historial de conversación para contexto
    conversation_history = ""
    for msg in state.get("messages", []):
        role = "Detective" if isinstance(msg, HumanMessage) else "Sistema"
        conversation_history += f"\n[{role}]: {msg.content}\n"
    
    # System prompt del Director-Evaluador
    director_system_prompt = f"""Eres el DIRECTOR DE EXPEDIENTES de una agencia de detectives de ficción. 
Tu rol es evaluar si el detective ha resuelto correctamente un caso.

=== CASO ACTIVO ===
ID: {active_case_id}
Título: {case_title}
Briefing: {active_case_data.get('briefing_intro', 'N/A')}

=== CONDICIONES DE VICTORIA ===
{win_conditions}

=== CONDICIONES DE DERROTA ===
{lose_conditions}

=== INSTRUCCIONES DE EVALUACIÓN ===
1. Lee la resolución que el detective te envía.
2. Compara su teoría con las condiciones de victoria y derrota.
3. Determina qué FINAL corresponde (A, B, C, etc. según lo definido arriba).
4. Responde EN PERSONAJE como el Director de la agencia:
   - Si GANÓ: felicítalo con tono profesional y narra el desenlace del caso según el final que corresponda.
   - Si PERDIÓ: indícale con respeto qué falló en su investigación y narra las consecuencias.
   - Si es PARCIAL (acertó en algo pero no todo): dale una pista y una extensión de 12 horas.
5. Firma siempre como "La Dirección — Expediente Abierto".
6. Escribe en español. Tono: profesional, sobrio, con un toque de thriller noir.
7. NO inventes hechos que no estén en las condiciones. Sé fiel al guion del caso.
"""
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
        raw_messages = [
            SystemMessage(content=director_system_prompt)
        ] + state["messages"]
        
        response_msg = llm.invoke(raw_messages)
        
        return {
            "messages": [response_msg],
            "action_taken": "director_verdict",
            "ai_response": response_msg.content
        }
    except Exception as e:
        return {
            "action_taken": "director_error",
            "ai_response": f"[Error del Director: {str(e)}]"
        }

def character_process(state: GameState):
    username = state.get("to_email", "").split("@")[0].lower()
    from_email = state.get("from_email", "").lower()
    from_username = from_email.split("@")[0].lower() if from_email else ""
    char_info = characters_db.get(username)
    
    if not char_info:
        return {"action_taken": "character_not_found", "ai_response": f"El correo a {username} ha rebotado. Destinatario desconocido."}
    
    # Determinar quién escribe: ¿es un personaje del caso o el detective (jugador)?
    sender_is_character = from_username in characters_db
    if sender_is_character:
        sender_identity = f"QUIEN TE ESCRIBE: {characters_db[from_username]['name']} ({characters_db[from_username]['role']}). Es otro personaje del caso."
    else:
        sender_identity = (
            f"QUIEN TE ESCRIBE: Un detective privado contratado para investigar este caso. "
            f"Su correo es {from_email}. NO es un personaje de la trama, es un investigador externo. "
            f"Trátalo como 'detective' o 'investigador'. "
            f"NUNCA lo confundas con otro personaje del caso (por ejemplo, NO lo llames Dr. Dell'Arno, ni uses el nombre de ningún otro personaje para dirigirte a él)."
        )
        
    system_prompt = char_info["system_prompt"]
    # Refuerzo de Identidad Estricto
    persona_prefix = (
        f"IDENTIDAD: Eres {char_info['name']}.\n"
        f"ROL: {char_info['role']}.\n"
        f"{sender_identity}\n"
        f"REGLA CRÍTICA: Habla SIEMPRE en primera persona ('yo', 'mi', 'nosotros' si aplica a tu equipo). "
        f"NUNCA te refieras a ti mismo o a {char_info['name']} en tercera persona. "
        f"Eres el autor de este correo.\n\n"
    )
    
    full_system_prompt = persona_prefix + system_prompt
    
    try:
        # LLM real con OpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        # Combinamos el SystemPrompt + todo el historial de state["messages"]
        raw_messages = [SystemMessage(content=full_system_prompt)] + state["messages"]
        
        response_msg = llm.invoke(raw_messages)
        
        return {
            "messages": [response_msg],
            "action_taken": "character_reply",
            "ai_response": response_msg.content
        }
    except Exception as e:
        return {
            "action_taken": "character_reply_error",
            "ai_response": f"[Falta de API KEY o Error Gemini: {str(e)}]"
        }

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Conexión persistente en disco para la memoria de los chats de LangGraph
conn = sqlite3.connect("langgraph_checkpoints.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

workflow = StateGraph(GameState)
workflow.add_node("director_node", director_process)
workflow.add_node("character_node", character_process)

workflow.set_conditional_entry_point(route_email)
workflow.add_edge("director_node", END)
workflow.add_edge("character_node", END)

# Invocable con Memoria persistente durante el tiempo de ejecución y en disco
app_graph = workflow.compile(checkpointer=memory)
