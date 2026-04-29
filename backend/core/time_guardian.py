"""
Guardián del Tiempo — Módulo central de latencia y scheduling.

Responsabilidades:
  1. Parsear las latencias de respuesta escritas en el system_prompt de cada personaje.
  2. Calcular un delay realista (en minutos) para cada respuesta generada.
  3. Funcionar como nodo de LangGraph que intercepta la respuesta del character_node
     y la encola en ScheduledMessage en lugar de devolverla inmediatamente.
"""

import os
import re
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

logger = logging.getLogger("time_guardian")

# En modo desarrollo, el Guardián se desactiva y las respuestas llegan inmediatas.
# Activar con DEV_MODE=true en .env
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")

# ────────────────────────────────────────────────────────────
# 1. PARSEADOR DE LATENCIA DESDE SYSTEM PROMPTS
# ────────────────────────────────────────────────────────────

# Patrones que capturan rangos de latencia escritos en español en los prompts.
# Ejemplos reales del codebase:
#   "Respondés rápido, entre 5 y 15 minutos"
#   "Respondés entre 20 y 90 minutos, nunca inmediato"
#   "Respondés en 1 a 3 horas"
#   "Respondés lento, 2 a 4 horas"
#   "Respondés en horarios raros, 10 minutos o 10 horas"
#   "Respondés rápido, 30 minutos"
#   "Respondés cuando te da la gana, entre 30 minutos y 24 horas"
#   "Respondés cuando podés, 6 a 24 horas"
#   "Respondés rápido (30 a 60 minutos)"

_LATENCY_PATTERNS = [
    # "entre X y Y minutos/horas"
    re.compile(
        r'(?:entre\s+)?(\d+)\s*(?:y|a)\s*(\d+)\s*(minutos?|horas?)',
        re.IGNORECASE
    ),
    # "X minutos o Y horas" (mixed units)
    re.compile(
        r'(\d+)\s*(minutos?|horas?)\s*o\s*(\d+)\s*(minutos?|horas?)',
        re.IGNORECASE
    ),
    # "X a Y horas/minutos" (simple range)
    re.compile(
        r'(\d+)\s*a\s*(\d+)\s*(minutos?|horas?)',
        re.IGNORECASE
    ),
    # Single value: "30 minutos" or "2 horas" (fallback)
    re.compile(
        r'(?:rápido|lento)?,?\s*(\d+)\s*(minutos?|horas?)',
        re.IGNORECASE
    ),
]


def _to_minutes(value: int, unit: str) -> int:
    """Convierte un valor con unidad a minutos."""
    if 'hora' in unit.lower():
        return value * 60
    return value


def parse_latency_from_prompt(system_prompt: str) -> Tuple[int, int]:
    """
    Extrae el rango de latencia (min_minutes, max_minutes) del system_prompt
    de un personaje. Busca patrones como "Respondés en X a Y minutos/horas".

    Returns:
        (min_minutes, max_minutes) — rango en minutos.
        Default (15, 60) si no se encuentra nada.
    """
    # Buscar solo en la sección que habla de latencia de respuesta
    latency_section = ""
    for line in system_prompt.split('.'):
        if any(kw in line.lower() for kw in ['respondés', 'respondes', 'latencia']):
            latency_section += line + ". "

    if not latency_section:
        latency_section = system_prompt

    # Patrón especial: "X minutos o Y horas" (unidades mixtas, separador "o")
    mixed_match = re.search(
        r'(\d+)\s*(minutos?|horas?)\s*o\s*(\d+)\s*(minutos?|horas?)',
        latency_section, re.IGNORECASE
    )
    if mixed_match:
        min_val = _to_minutes(int(mixed_match.group(1)), mixed_match.group(2))
        max_val = _to_minutes(int(mixed_match.group(3)), mixed_match.group(4))
        return (min(min_val, max_val), max(min_val, max_val))

    # Patrón especial: "entre X minutos y Y horas" (unidades mixtas, separador "y")
    mixed_range_match = re.search(
        r'(?:entre\s+)?(\d+)\s*(minutos?|horas?)\s*y\s*(\d+)\s*(minutos?|horas?)',
        latency_section, re.IGNORECASE
    )
    if mixed_range_match:
        min_val = _to_minutes(int(mixed_range_match.group(1)), mixed_range_match.group(2))
        max_val = _to_minutes(int(mixed_range_match.group(3)), mixed_range_match.group(4))
        return (min(min_val, max_val), max(min_val, max_val))

    # Patrón de rango con misma unidad: "entre X y Y minutos" o "X a Y horas"
    range_match = re.search(
        r'(?:entre\s+)?(\d+)\s*(?:y|a)\s*(\d+)\s*(minutos?|horas?)',
        latency_section, re.IGNORECASE
    )
    if range_match:
        unit = range_match.group(3)
        min_val = _to_minutes(int(range_match.group(1)), unit)
        max_val = _to_minutes(int(range_match.group(2)), unit)
        return (min(min_val, max_val), max(min_val, max_val))

    # Valor simple: "30 minutos"
    single_match = re.search(
        r'(\d+)\s*(minutos?|horas?)',
        latency_section, re.IGNORECASE
    )
    if single_match:
        val = _to_minutes(int(single_match.group(1)), single_match.group(2))
        # Crear un rango de ±30% alrededor del valor único
        margin = max(int(val * 0.3), 5)
        return (max(val - margin, 1), val + margin)

    # Default: 15-60 minutos
    return (15, 60)


def calculate_delay_minutes(
    system_prompt: str,
    interaction_count: int = 0,
    is_urgent: bool = False
) -> int:
    """
    Calcula cuántos minutos debe tardar la respuesta de un personaje.

    Args:
        system_prompt: El prompt del personaje (contiene hints de latencia).
        interaction_count: Cuántas interacciones lleva el hilo (comprime latencia
                          ligeramente a medida que la conversación se intensifica).
        is_urgent: Si el caso está cerca de expirar, reduce latencia.

    Returns:
        Delay en minutos (entero).
    """
    min_min, max_min = parse_latency_from_prompt(system_prompt)

    # Factor de compresión por intensidad conversacional
    # A medida que el jugador y el NPC intercambian más, las respuestas
    # se aceleran ligeramente (como en una conversación real que se calienta).
    intensity_factor = max(0.5, 1.0 - (interaction_count * 0.03))

    # Factor de urgencia (caso a punto de expirar)
    urgency_factor = 0.4 if is_urgent else 1.0

    adjusted_min = int(min_min * intensity_factor * urgency_factor)
    adjusted_max = int(max_min * intensity_factor * urgency_factor)

    # Asegurar mínimos razonables
    adjusted_min = max(adjusted_min, 2)
    adjusted_max = max(adjusted_max, adjusted_min + 3)

    delay = random.randint(adjusted_min, adjusted_max)

    logger.info(
        f"Latencia calculada: {delay}min "
        f"(rango base: {min_min}-{max_min}min, "
        f"intensity: {intensity_factor:.2f}, "
        f"urgency: {urgency_factor:.2f})"
    )
    return delay


# ────────────────────────────────────────────────────────────
# 2. DETECCIÓN DE HORARIO IMPOSIBLE (para personajes como Marta Soler)
# ────────────────────────────────────────────────────────────

def should_use_impossible_hour(system_prompt: str, message_count: int) -> bool:
    """
    Algunos personajes (como Marta Soler) deben enviar respuestas en
    horarios 'imposibles' (3:00-5:30 AM) como pista narrativa.

    Detecta si el prompt lo exige y aplica la frecuencia descrita
    (ej: "una de cada tres respuestas").
    """
    if 'horarios' in system_prompt.lower() and 'imposible' in system_prompt.lower():
        # "Al menos una de cada tres respuestas"
        return message_count % 3 == 0
    return False


def adjust_for_impossible_hour(scheduled_at: datetime) -> datetime:
    """
    Mueve la hora de entrega a un horario 'imposible' (3:00-5:30 AM)
    del día siguiente si la hora actual no cae en ese rango.
    """
    target_hour = random.randint(3, 5)
    target_minute = random.randint(0, 30 if target_hour == 5 else 59)

    # Si estamos antes de las 3 AM, programar para hoy.
    # Si estamos después, programar para mañana.
    if scheduled_at.hour >= 6:
        next_day = scheduled_at + timedelta(days=1)
        return next_day.replace(hour=target_hour, minute=target_minute, second=0)
    else:
        return scheduled_at.replace(hour=target_hour, minute=target_minute, second=0)


# ────────────────────────────────────────────────────────────
# 3. NODO LANGGRAPH: time_guardian_node
# ────────────────────────────────────────────────────────────

def time_guardian_process(state: dict) -> dict:
    """
    Nodo de LangGraph que intercepta la respuesta del character_node.
    En lugar de devolver la respuesta directamente, la encola en
    ScheduledMessage con un delay calculado.

    Si la acción tomada NO fue 'character_reply' (ej: error, not found),
    devuelve la respuesta inmediatamente sin delay.
    """
    from database.database import SessionLocal
    from database.models import ScheduledMessage, GameSession, User, Message
    from langchain_core.messages import HumanMessage

    action = state.get("action_taken", "")
    ai_response = state.get("ai_response", "")
    from_email = state.get("from_email", "")
    to_email = state.get("to_email", "")
    subject = state.get("subject", "")

    # Solo aplicar delay a respuestas exitosas de personaje
    if action != "character_reply" or not ai_response:
        logger.info(f"Time Guardian: bypass (action={action})")
        return {}  # No modifica el estado, la respuesta fluye normal

    # En DEV_MODE, dejar pasar la respuesta sin delay
    if DEV_MODE:
        logger.info("Time Guardian: DEV_MODE activo — respuesta inmediata")
        return {}  # No toca el estado → character_reply + ai_response pasan directo

    # Obtener el system_prompt del personaje para calcular latencia
    from core.orchestrator import characters_db
    char_alias = to_email.split("@")[0].lower()
    char_info = characters_db.get(char_alias, {})
    system_prompt = char_info.get("system_prompt", "")

    # Contar interacciones previas para factor de intensidad
    messages = state.get("messages", [])
    human_count = sum(1 for m in messages if isinstance(m, HumanMessage))

    # Determinar urgencia (sesión cercana a expirar)
    is_urgent = False
    db = None
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.email == from_email).first()
        if user:
            session = (
                db.query(GameSession)
                .filter(GameSession.user_id == user.id, GameSession.status == "active")
                .order_by(GameSession.started_at.desc())
                .first()
            )
            if session and session.expires_at:
                remaining = (session.expires_at - datetime.now(timezone.utc)).total_seconds()
                is_urgent = remaining < 3600  # Menos de 1 hora

    except Exception as e:
        logger.warning(f"Time Guardian: error checking urgency: {e}")

    # Calcular delay
    delay_minutes = calculate_delay_minutes(
        system_prompt=system_prompt,
        interaction_count=human_count,
        is_urgent=is_urgent
    )

    now = datetime.now(timezone.utc)
    scheduled_at = now + timedelta(minutes=delay_minutes)

    # Ajustar horario imposible si aplica
    if should_use_impossible_hour(system_prompt, human_count):
        scheduled_at = adjust_for_impossible_hour(scheduled_at)
        logger.info(f"Time Guardian: usando horario imposible -> {scheduled_at}")

    # Encolar en ScheduledMessage
    try:
        if db is None:
            db = SessionLocal()

        # Buscar session_id
        session_id = None
        user = db.query(User).filter(User.email == from_email).first()
        if user:
            session = (
                db.query(GameSession)
                .filter(GameSession.user_id == user.id, GameSession.status == "active")
                .order_by(GameSession.started_at.desc())
                .first()
            )
            if session:
                session_id = session.id

        scheduled_msg = ScheduledMessage(
            session_id=session_id,
            from_email=to_email,  # El personaje "responde"
            to_email=from_email,  # Al jugador
            subject=f"RE: {subject}" if subject else "Respuesta",
            body=ai_response,
            created_at=now,
            scheduled_at=scheduled_at,
            is_delivered=False
        )
        db.add(scheduled_msg)
        db.commit()

        logger.info(
            f"Time Guardian: respuesta encolada "
            f"(delay={delay_minutes}min, scheduled_at={scheduled_at.isoformat()}, "
            f"char={char_alias})"
        )

        # Modificar el estado para indicar que la respuesta fue encolada
        return {
            "action_taken": "time_guardian_queued",
            "ai_response": None,  # NO devolver respuesta inmediata
        }

    except Exception as e:
        logger.error(f"Time Guardian: error enqueueing: {e}", exc_info=True)
        if db:
            db.rollback()
        # Fallback: devolver respuesta inmediata
        return {
            "action_taken": "time_guardian_fallback_immediate",
        }
    finally:
        if db:
            db.close()
