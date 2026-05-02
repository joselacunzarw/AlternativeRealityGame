import imaplib
import email
import os
import asyncio
import re
import logging
from datetime import datetime, timezone
from email.header import decode_header
from dotenv import load_dotenv
from core.conversation_threads import resolve_inbound_thread_id
from core.inbound_runtime_state import (
    get_unprocessed_message_ids,
    has_processed_messages,
    is_rate_limited as persistent_is_rate_limited,
    mark_message_processed,
    seed_processed_message_ids,
)
from core.orchestrator import app_graph
from core.email_reply_parser import extract_visible_reply
from langchain_core.messages import HumanMessage
from core.mailer import send_smtp_email

load_dotenv()

# Configurar Logging hacia un archivo
logging.basicConfig(
    filename='polillero.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Rate limiting: máximo de correos procesados por usuario por hora.
# Protege contra jugadores que disparan costos enviando decenas de emails seguidos.
RATE_LIMIT_PER_HOUR = int(os.getenv("IMAP_RATE_LIMIT_PER_HOUR", "20"))
IMAP_UID_SOURCE = "imap_uid"

def _is_rate_limited(from_email: str, db=None) -> bool:
    return persistent_is_rate_limited(
        actor_email=from_email,
        scope="imap",
        limit=RATE_LIMIT_PER_HOUR,
        db=db,
    )

async def start_imap_poller():
    """
    Bucle asíncrono infinito que lee Gmail.
    """
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    if not SMTP_USER or not SMTP_PASSWORD:
        logging.error("No hay credenciales para IMAP")
        return

    await asyncio.sleep(3)
    logging.info("Escáner IMAP iniciado. Estado persistente habilitado.")

    while True:
        try:
            await asyncio.sleep(0.1)
            
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(SMTP_USER, SMTP_PASSWORD)
            mail.select("inbox")

            status, messages = mail.uid("search", None, "ALL")
            if status == "OK" and messages[0]:
                all_ids = [msg_uid.decode("utf-8") for msg_uid in messages[0].split()[-10:]]
                
                if not has_processed_messages(IMAP_UID_SOURCE):
                    inserted = seed_processed_message_ids(IMAP_UID_SOURCE, all_ids)
                    logging.info(f"Semilla inicial persistente plantada con {inserted} UID(s) históricos ignorados.")
                    mail.logout()
                    await asyncio.sleep(15)
                    continue

                new_ids = get_unprocessed_message_ids(IMAP_UID_SOURCE, all_ids)
                
                if new_ids:
                    logging.info(f"Detectados {len(new_ids)} correos nuevos. Procesando...")

                for uid in new_ids:
                    try:
                        status, data = mail.uid("fetch", uid, "(RFC822)")
                        if status != "OK":
                            logging.warning(f"[UID {uid}] Fallo fetch IMAP. Se reintentará en el próximo ciclo.")
                            continue

                        response_tuple = next((part for part in data if isinstance(part, tuple)), None)
                        if not response_tuple:
                            logging.warning(f"[UID {uid}] Respuesta IMAP sin payload RFC822. Se reintentará.")
                            continue

                        msg = email.message_from_bytes(response_tuple[1])

                        subject_header = decode_header(msg["Subject"])[0]
                        subject = subject_header[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(subject_header[1] or "utf-8", errors='ignore')

                        raw_from = msg.get("From")
                        match = re.search(r'<([^>]+)>', raw_from)
                        clean_from = match.group(1) if match else raw_from

                        # Mecanismo de Seguridad
                        if "expediente abierto" not in subject.lower() and "caso abierto" not in subject.lower():
                            logging.debug(f"[UID {uid}] Ignorado por Asunto (No Pertenece Al Juego): {subject}")
                            mark_message_processed(IMAP_UID_SOURCE, uid, from_email=clean_from, subject=subject)
                            continue

                        # Extraer cuerpo de texto
                        text_body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    text_body = part.get_payload(decode=True).decode("utf-8", errors='ignore')
                                    break
                        else:
                            text_body = msg.get_payload(decode=True).decode("utf-8", errors='ignore')

                        logging.info(f"[UID {uid}] Analizando mail válido de {clean_from}")

                        lines = [line.strip() for line in text_body.split("\n") if line.strip()]
                        target_character = SMTP_USER

                        if lines and lines[0].startswith("@"):
                            first_line_parts = lines[0].split(maxsplit=1)
                            possible_alias = first_line_parts[0][1:]
                            target_character = f"{possible_alias}@casos.expedienteabierto.com"

                            rest_of_first_line = first_line_parts[1] if len(first_line_parts) > 1 else ""
                            if rest_of_first_line:
                                lines[0] = rest_of_first_line
                                text_body = "\n".join(lines)
                            else:
                                text_body = "\n".join(lines[1:])

                        if target_character == SMTP_USER:
                            logging.warning(
                                f"[UID {uid}] Ignorando correo porque no tiene @alias en la primera línea "
                                "(Prevención de Infinite Loop)."
                            )
                            mark_message_processed(IMAP_UID_SOURCE, uid, from_email=clean_from, subject=subject)
                            continue

                        text_body = extract_visible_reply(text_body)

                        if _is_rate_limited(clean_from):
                            logging.warning(f"[UID {uid}] Rate limit alcanzado para {clean_from}. Correo descartado.")
                            mark_message_processed(IMAP_UID_SOURCE, uid, from_email=clean_from, subject=subject)
                            continue

                        logging.info(f"Enrutando hacia personaje: {target_character}")

                        email_str = f"Asunto: {subject}\n\nCuerpo:\n{text_body}"
                        human_msg = HumanMessage(content=email_str)

                        init_state = {
                            "from_email": clean_from,
                            "to_email": target_character,
                            "subject": subject,
                            "text_content": text_body,
                            "messages": [human_msg]
                        }

                        thread_id = resolve_inbound_thread_id(
                            from_email=clean_from,
                            to_email=target_character,
                            subject=subject,
                            text_content=text_body,
                        )

                        logging.info(
                            f"Invocando grafo para {clean_from} -> {target_character} "
                            f"(Thread: {thread_id})"
                        )
                        result = app_graph.invoke(init_state, config={"configurable": {"thread_id": thread_id}})

                        action = result.get("action_taken", "")
                        ai_text = result.get("ai_response", "")
                        char_alias = target_character.split("@")[0]

                        if action == "time_guardian_queued":
                            logging.info(
                                f"Time Guardian encoló la respuesta de {char_alias}. "
                                f"El delivery_worker la entregará con delay."
                            )
                        elif ai_text:
                            logging.info(f"LangGraph respondió con éxito. Acción: {action}. Despachando inmediato a {clean_from}...")
                            send_smtp_email(clean_from, f"RE: {subject}", ai_text)

                        mark_message_processed(IMAP_UID_SOURCE, uid, from_email=clean_from, subject=subject)

                    except Exception as email_err:
                        logging.error(f"Error procesando correo individual UID {uid}: {email_err}", exc_info=True)

            mail.logout()
        except Exception as e:
            logging.error(f"Error global IMAP: {e}", exc_info=True)
        
        await asyncio.sleep(15)
