"""
Delivery Worker — Poller asíncrono que entrega mensajes encolados por el Guardián del Tiempo.

Corre como tarea de fondo en el lifespan de FastAPI.
Cada ciclo consulta ScheduledMessage buscando mensajes cuyo scheduled_at ya pasó
y que aún no fueron entregados. Los envía por SMTP y los marca como entregados.

También corre un cleanup periódico (cada hora) que elimina checkpoints LangGraph
de sesiones completadas o abandonadas para evitar crecimiento indefinido del SQLite.
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger("delivery_worker")

# Cada cuántos ciclos de 30s se corre el cleanup (120 ciclos = 1 hora)
_CLEANUP_EVERY_N_CYCLES = 120


def _cleanup_checkpoints():
    """
    Elimina checkpoints LangGraph de sesiones que ya no están activas.

    Estrategia:
      1. Borra por session_id los hilos del formato nuevo: 'thread_session_{session_id}_{alias}'.
      2. Conserva una limpieza de compatibilidad para hilos legacy por email solo si
         el usuario ya no tiene ninguna sesión activa.
    """
    checkpoint_path = os.getenv("DB_CHECKPOINT_PATH", "langgraph_checkpoints.sqlite")

    if not os.path.exists(checkpoint_path):
        return

    try:
        from core.conversation_threads import (
            build_fallback_email_thread_pattern,
            build_legacy_email_thread_pattern,
            build_session_thread_pattern,
        )
        from database.database import SessionLocal
        from database.models import GameSession, User

        db = SessionLocal()
        try:
            # Emails con al menos una sesión activa.
            active_emails = {
                email
                for _, email in db.query(GameSession, User.email)
                .join(User, GameSession.user_id == User.id)
                .filter(GameSession.status == "active")
                .all()
            }

            inactive = (
                db.query(GameSession, User.email)
                .join(User, GameSession.user_id == User.id)
                .filter(GameSession.status.in_(["completed", "abandonado", "failed_timeout"]))
                .all()
            )

            if not inactive:
                return

            thread_patterns_to_delete = {
                build_session_thread_pattern(session.id)
                for session, _ in inactive
            }

            # Compatibilidad con el formato histórico por email.
            legacy_email_patterns = {
                build_legacy_email_thread_pattern(email)
                for _, email in inactive
                if email not in active_emails
            }
            fallback_email_patterns = {
                build_fallback_email_thread_pattern(email)
                for _, email in inactive
                if email not in active_emails
            }
            thread_patterns_to_delete.update(legacy_email_patterns)
            thread_patterns_to_delete.update(fallback_email_patterns)

            conn = sqlite3.connect(checkpoint_path)
            try:
                cur = conn.cursor()
                deleted = 0
                for pattern in thread_patterns_to_delete:
                    cur.execute("DELETE FROM checkpoints WHERE thread_id LIKE ?", (pattern,))
                    deleted += cur.rowcount
                    cur.execute("DELETE FROM writes WHERE thread_id LIKE ?", (pattern,))
                    deleted += cur.rowcount
                conn.commit()
                if deleted:
                    logger.info(f"Checkpoint cleanup: {deleted} registros eliminados de sesiones inactivas.")
            except Exception as e:
                logger.warning(f"Checkpoint cleanup: error al borrar ({e}). Las tablas pueden no existir aún.")
                conn.rollback()
            finally:
                conn.close()

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Checkpoint cleanup: error inesperado: {e}", exc_info=True)


async def start_delivery_worker():
    """
    Bucle asíncrono infinito que revisa y entrega mensajes programados.
    Corre cada 30 segundos. Cada hora también limpia checkpoints de sesiones inactivas.
    """
    from database.database import SessionLocal
    from database.models import ScheduledMessage, Message
    from core.mailer import send_smtp_email

    await asyncio.sleep(5)  # Esperar a que el servidor arranque
    logger.info("Delivery Worker iniciado. Revisando mensajes programados cada 30s.")

    cycle = 0

    while True:
        cycle += 1
        try:
            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc)

                # Buscar mensajes pendientes cuyo scheduled_at ya pasó
                pending = (
                    db.query(ScheduledMessage)
                    .filter(
                        ScheduledMessage.is_delivered == False,
                        ScheduledMessage.scheduled_at <= now
                    )
                    .order_by(ScheduledMessage.scheduled_at.asc())
                    .limit(10)  # Procesar de a 10 para no saturar
                    .all()
                )

                if pending:
                    logger.info(f"Delivery Worker: {len(pending)} mensaje(s) listos para entregar.")

                for msg in pending:
                    try:
                        # Enviar email real
                        success = send_smtp_email(
                            to_email=msg.to_email,
                            subject=msg.subject or "Respuesta",
                            text_content=msg.body
                        )

                        if success:
                            # Marcar como entregado
                            msg.is_delivered = True

                            # Copiar a la tabla Message para historial
                            archived = Message(
                                session_id=msg.session_id,
                                from_email=msg.from_email,
                                to_email=msg.to_email,
                                subject=msg.subject,
                                body=msg.body,
                                sent_at=now
                            )
                            db.add(archived)
                            db.commit()

                            logger.info(
                                f"Delivery Worker: entregado '{msg.subject}' "
                                f"de {msg.from_email} -> {msg.to_email}"
                            )
                        else:
                            logger.warning(
                                f"Delivery Worker: fallo SMTP para msg_id={msg.id}. "
                                f"Se reintentará en el próximo ciclo."
                            )
                            db.rollback()

                    except Exception as e:
                        logger.error(
                            f"Delivery Worker: error procesando msg_id={msg.id}: {e}",
                            exc_info=True
                        )
                        db.rollback()

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Delivery Worker: error global: {e}", exc_info=True)

        # Cleanup de checkpoints cada hora
        if cycle % _CLEANUP_EVERY_N_CYCLES == 0:
            await asyncio.get_event_loop().run_in_executor(None, _cleanup_checkpoints)

        await asyncio.sleep(30)  # Revisar cada 30 segundos
