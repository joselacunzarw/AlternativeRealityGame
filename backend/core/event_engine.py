"""
Event Engine — Motor de eventos proactivos del Director.

Responsabilidades:
  1. Monitorear sesiones activas cada 30 minutos.
  2. Para cada sesión, evaluar si algún evento proactivo del caso debe dispararse.
  3. Trigger combinado: tiempo transcurrido + evaluación LLM del progreso del detective.
  4. Generar el mensaje del personaje correspondiente y encolarlo en ScheduledMessage.

Diseño de triggers:
  - Tiempo: el evento no puede dispararse antes de N horas desde el inicio de la sesión.
  - Progreso: el LLM evalúa si la condición narrativa descripta en trigger_condition se cumple.
  - Ambos deben cumplirse para que el evento se dispare.
  - Mínimo MIN_HOURS_BETWEEN_EVENTS entre eventos consecutivos (producción).
  - En DEV_MODE el mínimo entre eventos se reduce a 10 minutos para testeo.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger("event_engine")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [EVENT] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")

# Horas mínimas entre eventos proactivos consecutivos en una misma sesión
MIN_HOURS_BETWEEN_EVENTS = (10 / 60) if DEV_MODE else 6  # 10 min en dev, 6h en prod

# Cada cuántos segundos corre el ciclo de evaluación
POLL_INTERVAL = 60 if DEV_MODE else 1800  # 1 min en dev, 30 min en prod

# En DEV_MODE, 1 hora de juego = 1 minuto real (factor 1/60)
# Permite testear eventos sin esperar horas reales.
DEV_TIME_FACTOR = (1 / 60) if DEV_MODE else 1


async def start_event_engine():
    """
    Bucle asíncrono que evalúa y dispara eventos proactivos.
    """
    await asyncio.sleep(15)  # Esperar arranque completo del servidor
    logger.info(
        f"Event Engine iniciado. "
        f"Ciclo: {POLL_INTERVAL}s. "
        f"Min entre eventos: {MIN_HOURS_BETWEEN_EVENTS}h."
    )

    while True:
        try:
            await _run_cycle()
        except Exception as e:
            logger.error(f"Event Engine: error en ciclo global: {e}", exc_info=True)
        await asyncio.sleep(POLL_INTERVAL)


async def _run_cycle():
    from database.database import SessionLocal
    from database.models import GameSession

    db = SessionLocal()
    try:
        active_sessions = db.query(GameSession).filter(GameSession.status == "active").all()
        logger.info(f"Event Engine: ciclo — {len(active_sessions)} sesión(es) activa(s).")
        for session in active_sessions:
            try:
                await asyncio.get_event_loop().run_in_executor(None, _process_session, session.id)
            except Exception as e:
                logger.error(f"Event Engine: error en session_id={session.id}: {e}", exc_info=True)
    finally:
        db.close()


def _log(msg: str):
    """Print directo a stdout para garantizar visibilidad en docker logs y threads."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"{ts} [EVENT] {msg}", flush=True)
    logger.info(msg)


def _process_session(session_id: int):
    """
    Evalúa y dispara el primer evento elegible para una sesión dada.
    Solo dispara un evento por ciclo por sesión.
    """
    from database.database import SessionLocal
    from database.models import GameSession, FiredEvent, Message, ScheduledMessage, User
    from core.orchestrator import cases_db, characters_db

    db = SessionLocal()
    try:
        session = db.query(GameSession).filter(GameSession.id == session_id).first()
        if not session or session.status != "active":
            _log(f"session_id={session_id} no activa, skip.")
            return

        case_data = cases_db.get(session.game_id)
        if not case_data:
            _log(f"session_id={session_id} caso '{session.game_id}' no encontrado.")
            return

        proactive_events = case_data.get("proactive_events", [])
        if not proactive_events:
            _log(f"session_id={session_id} caso sin proactive_events.")
            return

        _log(f"session_id={session_id} caso='{session.game_id}' — evaluando {len(proactive_events)} evento(s).")

        now = datetime.now(timezone.utc)

        # ── 1. VERIFICAR MÍNIMO ENTRE EVENTOS ───────────────────────────
        last_fired = (
            db.query(FiredEvent)
            .filter(FiredEvent.session_id == session_id)
            .order_by(FiredEvent.fired_at.desc())
            .first()
        )
        if last_fired:
            last_fired_at = last_fired.fired_at
            if last_fired_at.tzinfo is None:
                last_fired_at = last_fired_at.replace(tzinfo=timezone.utc)
            hours_since_last = (now - last_fired_at).total_seconds() / 3600
            if hours_since_last < MIN_HOURS_BETWEEN_EVENTS:
                return

        # ── 2. OBTENER HISTORIAL DE LA SESIÓN ───────────────────────────
        messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.sent_at.asc())
            .all()
        )
        history_text = "\n".join([
            f"{'Detective' if _is_player_message(msg, session, db) else msg.from_email}: {msg.body[:300]}"
            for msg in messages[-20:]  # Últimos 20 mensajes
        ])

        # ── 3. EVALUAR CADA EVENTO ───────────────────────────────────────
        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        hours_since_start = (now - started_at).total_seconds() / 3600

        already_fired_ids = {
            fe.event_id
            for fe in db.query(FiredEvent).filter(FiredEvent.session_id == session_id).all()
        }

        for event in proactive_events:
            event_id = event.get("id")
            max_fires = event.get("max_fires", 1)
            trigger_hours = event.get("trigger_after_hours", 0)
            trigger_condition = event.get("trigger_condition", "")
            char_alias = event.get("character", "")
            message_hint = event.get("message_hint", "")

            # ¿Ya se disparó el máximo de veces?
            fires_count = sum(1 for fid in already_fired_ids if fid == event_id)
            if fires_count >= max_fires:
                _log(f"  [{event_id}] ya disparado {fires_count}/{max_fires} veces, skip.")
                continue

            # ¿Pasaron las horas mínimas desde el inicio?
            threshold = trigger_hours * DEV_TIME_FACTOR
            _log(f"  [{event_id}] tiempo: {hours_since_start:.3f}h transcurrido, umbral: {threshold:.3f}h.")
            if hours_since_start < threshold:
                _log(f"  [{event_id}] aún no alcanzó el umbral, skip.")
                continue

            # ¿El personaje existe?
            char_info = characters_db.get(char_alias)
            if not char_info:
                _log(f"  [{event_id}] personaje '{char_alias}' no encontrado, skip.")
                continue

            # ── 4. EVALUAR CONDICIÓN NARRATIVA CON LLM ──────────────────
            _log(f"  [{event_id}] evaluando condición narrativa con LLM...")
            if not _evaluate_trigger_condition(trigger_condition, history_text, event_id):
                _log(f"  [{event_id}] LLM dijo NO, skip.")
                continue
            _log(f"  [{event_id}] LLM dijo SI — disparando evento.")

            # ── 5. DISPARAR EL EVENTO ────────────────────────────────────
            user = db.query(User).filter(User.id == session.user_id).first()
            if not user:
                continue

            _fire_event(db, session, event, char_info, user.email, now)
            already_fired_ids.add(event_id)

            logger.info(
                f"Event Engine: evento '{event_id}' disparado para session_id={session_id} "
                f"(personaje: {char_alias})"
            )
            break  # Un solo evento por ciclo por sesión

    finally:
        db.close()


def _is_player_message(msg, session, db) -> bool:
    """Determina si un mensaje es del jugador (no de un personaje del juego)."""
    from database.models import User
    user = db.query(User).filter(User.id == session.user_id).first()
    return user and msg.from_email == user.email


def _evaluate_trigger_condition(trigger_condition: str, history_text: str, event_id: str) -> bool:
    """
    Usa el LLM para evaluar si la condición narrativa del evento se cumple.
    Devuelve True si se debe disparar, False si no.
    Ante cualquier error, asume True para no bloquear el evento indefinidamente.
    """
    if not history_text.strip():
        # Sin historial todavía — las condiciones "el detective aún no hizo X"
        # son trivialmente verdaderas: el jugador no ha hecho nada todavía.
        logger.info(f"Event Engine: sin historial para trigger '{event_id}' → asumiendo condición cumplida.")
        return True

    eval_prompt = f"""Eres el DIRECTOR de un juego de detectives por email. Analizas el historial de conversación y decides si una condición narrativa se cumple.

=== CONDICIÓN A EVALUAR ===
{trigger_condition}

=== HISTORIAL RECIENTE DE LA PARTIDA ===
{history_text}

=== INSTRUCCIÓN ===
Evalúa si la condición descripta se cumple en base al historial.
Responde ÚNICAMENTE con una sola palabra: SI o NO."""

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        response = llm.invoke([SystemMessage(content=eval_prompt)])
        verdict = response.content.strip().upper()
        result = "SI" in verdict or "YES" in verdict
        logger.debug(f"Event Engine: trigger '{event_id}' evaluado → {verdict} → disparar={result}")
        return result
    except Exception as e:
        logger.warning(f"Event Engine: error evaluando trigger '{event_id}': {e}. Asumiendo SI.")
        return True


def _fire_event(db, session, event, char_info, player_email: str, now: datetime):
    """
    Genera el mensaje del personaje usando el LLM y lo encola en ScheduledMessage.
    """
    from database.models import FiredEvent, ScheduledMessage

    char_alias = event.get("character", "")
    message_hint = event.get("message_hint", "")
    event_id = event.get("id", "unknown")

    # Construir prompt de generación
    generation_prompt = f"""Eres {char_info['name']}.
{char_info['system_prompt']}

=== INSTRUCCIÓN DEL DIRECTOR (invisible para el jugador) ===
{message_hint}

Escribe el email que le enviarías al detective ahora mismo. En personaje, en español, tono consistente con tu perfil.
Firma como corresponde a tu personaje. NO menciones que el Director te pidió esto."""

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.75)
        response = llm.invoke([SystemMessage(content=generation_prompt)])
        message_body = response.content.strip()
    except Exception as e:
        logger.error(f"Event Engine: error generando mensaje para evento '{event_id}': {e}")
        return

    # Encolar con pequeño delay aleatorio (entre 2 y 15 min en prod, inmediato en dev)
    import random
    delay_minutes = random.randint(2, 5) if DEV_MODE else random.randint(5, 30)
    scheduled_at = now + timedelta(minutes=delay_minutes)

    char_email = f"{char_alias}@casos.expedienteabierto.com"
    subject = f"[Expediente Abierto] Mensaje de {char_info['name']}"

    scheduled_msg = ScheduledMessage(
        session_id=session.id,
        from_email=char_email,
        to_email=player_email,
        subject=subject,
        body=message_body,
        created_at=now,
        scheduled_at=scheduled_at,
        is_delivered=False,
    )
    db.add(scheduled_msg)

    # Registrar el evento como disparado
    fired = FiredEvent(
        session_id=session.id,
        event_id=event_id,
        fired_at=now,
    )
    db.add(fired)
    db.commit()

    logger.info(
        f"Event Engine: mensaje encolado para '{char_alias}' → '{player_email}' "
        f"(evento: {event_id}, entrega en {delay_minutes}min)"
    )
