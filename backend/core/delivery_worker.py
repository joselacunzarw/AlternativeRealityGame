"""
Delivery Worker — Poller asíncrono que entrega mensajes encolados por el Guardián del Tiempo.

Corre como tarea de fondo en el lifespan de FastAPI.
Cada ciclo consulta ScheduledMessage buscando mensajes cuyo scheduled_at ya pasó
y que aún no fueron entregados. Los envía por SMTP y los marca como entregados.
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("delivery_worker")


async def start_delivery_worker():
    """
    Bucle asíncrono infinito que revisa y entrega mensajes programados.
    Corre cada 30 segundos.
    """
    from database.database import SessionLocal
    from database.models import ScheduledMessage, Message
    from core.mailer import send_smtp_email

    await asyncio.sleep(5)  # Esperar a que el servidor arranque
    logger.info("Delivery Worker iniciado. Revisando mensajes programados cada 30s.")

    while True:
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

        await asyncio.sleep(30)  # Revisar cada 30 segundos
