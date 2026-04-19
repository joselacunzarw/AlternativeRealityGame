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
    return {"action_taken": "director_evaluation", "ai_response": "El Director ha archivado tu avance transitoriamente."}

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
