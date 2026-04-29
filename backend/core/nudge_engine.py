"""
Nudge Engine — Motor de apuros proactivos.

Cuando un jugador deja de interactuar por demasiado tiempo, los personajes
del caso le envían mensajes proactivos para reengancharlo.

Implementación v1 (costo-controlada):
  - NO usa LLM para decidir cuándo apurar. Usa temporizadores fijos.
  - Usa plantillas curadas con ligera variación aleatoria.
  - Disparo: tras 24h de inactividad (primer nudge), 48h (segundo), 72h (último).
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("nudge_engine")

# ────────────────────────────────────────────────────────────
# PLANTILLAS DE NUDGE
# Organizadas por tono. El motor elige según el personaje y el nivel de urgencia.
# ────────────────────────────────────────────────────────────

NUDGE_TEMPLATES = {
    "amable": [
        "Detective, ¿sigue con nosotros? Hace tiempo que no recibimos noticias suyas. El caso sigue abierto y el tiempo corre.",
        "Detective, nos preocupa su silencio. Si necesita más tiempo, lo entendemos, pero el expediente no espera para siempre.",
        "Disculpe la insistencia, detective. Solo queríamos saber si sigue trabajando en el caso. Hay pistas que se enfrían.",
        "Detective, ¿todo bien? El caso no va a resolverse solo. Si necesita una pista, escríbale a alguno de los contactos del expediente.",
    ],
    "urgente": [
        "Detective, URGENTE. El plazo del caso está por vencer. Si tiene una teoría, envíe su resolución ahora.",
        "Última notificación, detective. Si no recibimos avances en las próximas horas, el expediente será reasignado.",
        "Detective, la Dirección necesita un informe de progreso. El caso lleva demasiado tiempo sin movimiento.",
    ],
    "personaje": [
        "Detective, soy {nombre}. ¿Se olvidó de mí? Sigo esperando su respuesta. Esto es importante.",
        "Detective, le escribo porque hace días que no sé nada de usted. ¿Abandonó el caso? {nombre}.",
        "No quiero presionarlo, detective, pero necesito saber si sigue investigando. {nombre}.",
    ],
}

# Intervalos de nudge (en horas desde la última actividad)
NUDGE_INTERVALS_HOURS = [24, 48, 72]
MAX_NUDGES_PER_SESSION = 3


async def start_nudge_engine():
    """
    Bucle asíncrono que detecta sesiones inactivas y encola nudges.
    Corre cada 15 minutos.
    """
    from database.database import SessionLocal
    from database.models import GameSession, ScheduledMessage, Message, User

    await asyncio.sleep(10)  # Esperar a que el servidor arranque
    logger.info("Nudge Engine iniciado. Revisando inactividad cada 15 minutos.")

    while True:
        try:
            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc)

                # Buscar sesiones activas
                active_sessions = (
                    db.query(GameSession)
                    .filter(GameSession.status == "active")
                    .all()
                )

                for session in active_sessions:
                    try:
                        _process_session_nudge(db, session, now)
                    except Exception as e:
                        logger.error(
                            f"Nudge Engine: error en session_id={session.id}: {e}",
                            exc_info=True
                        )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Nudge Engine: error global: {e}", exc_info=True)

        await asyncio.sleep(900)  # 15 minutos


def _process_session_nudge(db, session, now: datetime):
    """Evalúa si una sesión necesita un nudge y lo encola si corresponde."""
    from database.models import Message, ScheduledMessage

    # 1. Encontrar la última actividad del jugador (mensajes entrantes)
    last_player_msg = (
        db.query(Message)
        .filter(
            Message.session_id == session.id,
            Message.from_email != None  # Mensajes del jugador, no del sistema
        )
        .order_by(Message.sent_at.desc())
        .first()
    )

    # Si no hay mensajes, usar el inicio de sesión como referencia
    last_activity = last_player_msg.sent_at if last_player_msg else session.started_at

    # Asegurar que last_activity sea timezone-aware
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    hours_inactive = (now - last_activity).total_seconds() / 3600

    # 2. Contar nudges ya enviados para esta sesión
    nudges_sent = (
        db.query(ScheduledMessage)
        .filter(
            ScheduledMessage.session_id == session.id,
            ScheduledMessage.subject.like("%[NUDGE]%")
        )
        .count()
    )

    if nudges_sent >= MAX_NUDGES_PER_SESSION:
        return  # Ya se agotaron los apuros

    # 3. Determinar si toca enviar un nudge
    target_hours = NUDGE_INTERVALS_HOURS[nudges_sent] if nudges_sent < len(NUDGE_INTERVALS_HOURS) else None
    if target_hours is None:
        return

    if hours_inactive < target_hours:
        return  # Aún no toca

    # 4. Verificar que no haya ya un nudge pendiente de entrega
    pending_nudge = (
        db.query(ScheduledMessage)
        .filter(
            ScheduledMessage.session_id == session.id,
            ScheduledMessage.subject.like("%[NUDGE]%"),
            ScheduledMessage.is_delivered == False
        )
        .first()
    )

    if pending_nudge:
        return  # Ya hay uno en cola

    # 5. Generar y encolar el nudge
    nudge_level = nudges_sent  # 0, 1, 2
    user = db.query(db.query.__self__.query(type(session)).session.bind.__class__).first() if False else None

    # Obtener email del jugador
    from database.models import User
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        return

    # Elegir plantilla según nivel
    if nudge_level == 0:
        template = random.choice(NUDGE_TEMPLATES["amable"])
    elif nudge_level == 1:
        template = random.choice(NUDGE_TEMPLATES["personaje"])
        # Intentar obtener un nombre de personaje del caso
        from core.orchestrator import cases_db
        case_data = cases_db.get(session.game_id, {})
        characters = case_data.get("characters", {})
        if characters:
            random_char = random.choice(list(characters.values()))
            template = template.format(nombre=random_char.get("name", "Un contacto"))
        else:
            template = template.format(nombre="Un contacto del caso")
    else:
        template = random.choice(NUDGE_TEMPLATES["urgente"])

    # Añadir variación menor: posdata aleatoria
    postscripts = [
        "",
        "\n\nPD: Recuerde que puede escribir a cualquier contacto del expediente.",
        "\n\nPD: El tiempo de resolución afecta la evaluación final del caso.",
        "\n\n-- Sistema de Comunicaciones, Expediente Abierto",
    ]
    template += random.choice(postscripts)

    # Programar entrega con un delay aleatorio de 5-30 minutos
    delay = random.randint(5, 30)
    scheduled_at = now + timedelta(minutes=delay)

    nudge_msg = ScheduledMessage(
        session_id=session.id,
        from_email="direccion@casos.expedienteabierto.com",
        to_email=user.email,
        subject=f"[NUDGE] Expediente Abierto — Seguimiento del caso",
        body=template,
        created_at=now,
        scheduled_at=scheduled_at,
        is_delivered=False
    )
    db.add(nudge_msg)
    db.commit()

    logger.info(
        f"Nudge Engine: apuro nivel {nudge_level} encolado para session_id={session.id} "
        f"(inactividad: {hours_inactive:.1f}h, entrega en {delay}min)"
    )
