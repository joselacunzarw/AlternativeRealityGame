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
    
    Detección de caso:
      1. Busca al jugador por email en la DB y toma su GameSession activa.
      2. Fallback: busca por título/ID en el texto (para QA sin DB).
    
    Cierre de sesión:
      - Si el veredicto es conclusivo, marca la sesión como 'completed'.
      - Guarda el tipo de final y la respuesta del Director en la DB.
    """
    import re
    from datetime import datetime, timezone
    
    from_email = state.get("from_email", "")
    text = state.get("text_content", "")
    subject = state.get("subject", "")
    
    active_case_data = None
    active_case_id = None
    db_session_obj = None  # La GameSession de la DB (si existe)
    
    # ── 1. DETECCIÓN POR DB (método principal) ──────────────────────
    try:
        from database.database import SessionLocal
        from database.models import User, GameSession
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == from_email).first()
            if user:
                db_session_obj = (
                    db.query(GameSession)
                    .filter(GameSession.user_id == user.id, GameSession.status == "active")
                    .order_by(GameSession.started_at.desc())
                    .first()
                )
                if db_session_obj and db_session_obj.game_id in cases_db:
                    active_case_id = db_session_obj.game_id
                    active_case_data = cases_db[active_case_id]
        finally:
            if not db_session_obj:
                db.close()
    except Exception:
        pass  # DB no disponible (ej. QA agent), usar fallback
    
    # ── 2. FALLBACK: detección por texto (QA y testing) ─────────────
    if not active_case_data:
        subject_lower = (subject or "").lower()
        text_lower = (text or "").lower()
        combined = subject_lower + " " + text_lower
        
        for cid, cdata in cases_db.items():
            title_lower = cdata.get("title", "").lower()
            if cid in combined or title_lower in combined:
                active_case_data = cdata
                active_case_id = cid
                break
        
        if not active_case_data:
            caso_match = re.search(r'caso\s*(\d+|cero)', combined)
            if caso_match:
                caso_key = caso_match.group(1)
                num_to_id = {
                    "0": "caso_cero", "cero": "caso_cero",
                    "1": "grabacion_1", "2": "herencia_2",
                    "3": "martes_3", "4": "novia_4", "5": "experimento_5"
                }
                mapped_id = num_to_id.get(caso_key)
                if mapped_id and mapped_id in cases_db:
                    active_case_data = cases_db[mapped_id]
                    active_case_id = mapped_id
    
    # ── 3. SIN CASO IDENTIFICADO ────────────────────────────────────
    if not active_case_data:
        return {
            "action_taken": "director_no_case",
            "ai_response": (
                "Detective,\n\n"
                "No hemos podido identificar a que expediente se refiere su comunicacion. "
                "Asegurese de tener un caso activo antes de enviar su resolucion.\n\n"
                "-- La Direccion"
            )
        }
    
    # ── 4. CONSTRUIR PROMPT CON EPILOGOS COMPLETOS ──────────────────
    director_logic = active_case_data.get("director_logic", {})
    win_conditions = director_logic.get("win_conditions", "No definidas.")
    lose_conditions = director_logic.get("lose_conditions", "No definidas.")
    case_title = active_case_data.get("title", active_case_id)
    briefing = active_case_data.get("briefing_intro", "N/A")
    
    director_system_prompt = f"""Eres el DIRECTOR DE EXPEDIENTES de una agencia de detectives de ficcion llamada "Expediente Abierto".
Tu rol es evaluar si el detective ha resuelto correctamente un caso.

=== CASO ACTIVO ===
ID: {active_case_id}
Titulo: {case_title}
Briefing Original: {briefing}

=== CONDICIONES DE VICTORIA (incluyen los finales posibles) ===
{win_conditions}

=== CONDICIONES DE DERROTA ===
{lose_conditions}

=== INSTRUCCIONES DE EVALUACION ===
1. Lee la resolucion que el detective te envia.
2. Compara su teoria con las condiciones de victoria y derrota definidas arriba.
3. Determina EXACTAMENTE que FINAL corresponde (A, B, C, D, etc. segun lo definido).
4. Responde EN PERSONAJE como el Director de la agencia:
   - Si GANO: felicitalo con tono profesional y narra el EPILOGO del final que corresponda.
     USA los detalles del epilogo definido en las condiciones de victoria. No improvises.
   - Si PERDIO: explicale que fallo en su investigacion y narra las consecuencias
     segun lo definido en las condiciones de derrota.
   - Si es PARCIAL (acerto en algo pero no todo): dale UNA pista concreta y una 
     extension de 12 horas. NO cierres el caso aun.
5. Firma siempre como "La Direccion -- Expediente Abierto".
6. Escribe en espanol. Tono: profesional, sobrio, thriller noir.
7. NO inventes hechos. Se fiel al guion del caso.
8. AL FINAL de tu respuesta, en una linea separada, incluye EXACTAMENTE una de estas etiquetas:
   [VERDICT:win_a] o [VERDICT:win_b] o [VERDICT:win_c] o [VERDICT:win_d]
   [VERDICT:lose] o [VERDICT:partial]
   Esto es para el sistema interno, el detective no lo ve.
"""
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
        raw_messages = [
            SystemMessage(content=director_system_prompt)
        ] + state["messages"]
        
        response_msg = llm.invoke(raw_messages)
        ai_text = response_msg.content
        
        # ── 5. EXTRAER VEREDICTO Y LIMPIAR RESPUESTA ────────────────
        verdict_tag = "unknown"
        verdict_match = re.search(r'\[VERDICT:(\w+)\]', ai_text)
        if verdict_match:
            verdict_tag = verdict_match.group(1)
            # Remover la etiqueta de la respuesta visible al jugador
            ai_text_clean = re.sub(r'\n?\[VERDICT:\w+\]', '', ai_text).strip()
        else:
            ai_text_clean = ai_text
        
        is_conclusive = verdict_tag.startswith("win") or verdict_tag == "lose"
        
        # ── 6. ACTUALIZAR DB ────────────────────────────────────────
        if db_session_obj and is_conclusive:
            try:
                db_session_obj.status = "completed"
                db_session_obj.completed_at = datetime.now(timezone.utc)
                db_session_obj.verdict = verdict_tag
                db_session_obj.director_summary = ai_text_clean[:2000]  # Cap para seguridad
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        elif db_session_obj:
            db.close()
        
        return {
            "messages": [response_msg],
            "action_taken": f"director_verdict_{verdict_tag}",
            "ai_response": ai_text_clean
        }
    except Exception as e:
        if db_session_obj:
            try:
                db.close()
            except Exception:
                pass
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
