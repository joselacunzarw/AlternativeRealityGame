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

CHARACTERS_PATH = Path(__file__).parent.parent / "models" / "characters.json"
try:
    with open(CHARACTERS_PATH, "r", encoding="utf-8") as f:
        characters_db = json.load(f)
except Exception:
    characters_db = {}

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
    char_info = characters_db.get(username)
    
    if not char_info:
        return {"action_taken": "character_not_found", "ai_response": f"El correo a {username} ha rebotado. Destinatario desconocido."}
        
    system_prompt = char_info["system_prompt"]
    
    try:
        # LLM real con OpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        # Combinamos el SystemPrompt + todo el historial de state["messages"]
        raw_messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response_msg = llm.invoke(raw_messages)
        
        return {
            "messages": [response_msg],  # add_messages lo anexara automáticamente al estado final
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
