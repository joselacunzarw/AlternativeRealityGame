import imaplib
import email
import os
import asyncio
import re
import logging
from email.header import decode_header
from dotenv import load_dotenv
from core.orchestrator import app_graph
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
    logging.info("Escáner IMAP iniciado. Memoria base limpia.")

    processed_ids = set()

    while True:
        try:
            await asyncio.sleep(0.1)
            
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(SMTP_USER, SMTP_PASSWORD)
            mail.select("inbox")

            status, messages = mail.search(None, "ALL")
            if status == "OK" and messages[0]:
                all_ids = messages[0].split()[-10:]
                
                if not processed_ids:
                    processed_ids.update(all_ids)
                    logging.info(f"Semilla inicial plantada con {len(all_ids)} correos históricos ignorados.")
                    mail.logout()
                    await asyncio.sleep(15)
                    continue

                new_ids = [msg_id for msg_id in all_ids if msg_id not in processed_ids]
                
                if new_ids:
                    logging.info(f"Detectados {len(new_ids)} correos nuevos. Procesando...")

                for num in new_ids:
                    processed_ids.add(num)

                    try:
                        status, data = mail.fetch(num, "(RFC822)")
                        if status != "OK": continue

                        for response_part in data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                
                                subject_header = decode_header(msg["Subject"])[0]
                                subject = subject_header[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(subject_header[1] or "utf-8", errors='ignore')
                                    
                                raw_from = msg.get("From")
                                match = re.search(r'<([^>]+)>', raw_from)
                                clean_from = match.group(1) if match else raw_from

                                # Mecanismo de Seguridad
                                if "expediente abierto" not in subject.lower() and "caso abierto" not in subject.lower():
                                    logging.debug(f"[{num}] Ignorado por Asunto (No Pertenece Al Juego): {subject}")
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

                                logging.info(f"[{num}] Analizando mail válido de {clean_from}")

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
                                    logging.warning(f"[{num}] Ignorando correo porque no tiene @alias en la primera línea (Prevención de Infinite Loop).")
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

                                # Aislar hilos: un hilo por par (Usuario, Personaje)
                                char_alias = target_character.split("@")[0]
                                thread_id = f"thread_{clean_from}_{char_alias}"
                                
                                logging.info(f"Invocando grafo para {clean_from} -> {char_alias} (Thread: {thread_id})")
                                result = app_graph.invoke(init_state, config={"configurable": {"thread_id": thread_id}})
                                
                                ai_text = result.get("ai_response", "")

                                if ai_text:
                                    logging.info(f"LangGraph respondió con éxito. Acción tomada: {result.get('action_taken')}. Despachando a {clean_from}...")
                                    send_smtp_email(clean_from, f"RE: {subject}", ai_text)

                    except Exception as email_err:
                        logging.error(f"Error procesando correo individual {num}: {email_err}", exc_info=True)

            mail.logout()
        except Exception as e:
            logging.error(f"Error global IMAP: {e}", exc_info=True)
        
        await asyncio.sleep(15)
