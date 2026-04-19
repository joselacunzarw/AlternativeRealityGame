import imaplib
import email
import os
import re
from email.header import decode_header
from dotenv import load_dotenv

load_dotenv()
from core.orchestrator import app_graph
from langchain_core.messages import HumanMessage
from core.mailer import send_smtp_email

def test():
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(SMTP_USER, SMTP_PASSWORD)
    mail.select("inbox")
    
    st, messages = mail.search(None, "ALL")
    num = messages[0].split()[-1] # 60621
    
    status, data = mail.fetch(num, "(RFC822)")
    response_part = data[0]
    msg = email.message_from_bytes(response_part[1])
    
    subject_header = decode_header(msg["Subject"])[0]
    subject = subject_header[0]
    if isinstance(subject, bytes):
        subject = subject.decode(subject_header[1] or "utf-8", errors='ignore')
        
    raw_from = msg.get("From")
    match = re.search(r'<([^>]+)>', raw_from)
    clean_from = match.group(1) if match else raw_from

    print(f"Subject: {subject}")
    
    # Extraer cuerpo de texto
    text_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                text_body = part.get_payload(decode=True).decode("utf-8", errors='ignore')
                break
    else:
        text_body = msg.get_payload(decode=True).decode("utf-8", errors='ignore')

    lines = [line.strip() for line in text_body.split("\n") if line.strip()]
    target_character = SMTP_USER
    
    print(f"DEBUG LINES: {repr(lines[:3])}")
    
    if lines and lines[0].startswith("@"):
        possible_alias = lines[0].split()[0][1:] 
        target_character = f"{possible_alias}@casos.expedienteabierto.com"
        text_body = "\n".join(lines[1:])
        
    print(f"Target: {target_character}")

    email_str = f"Asunto: {subject}\n\nCuerpo:\n{text_body}"
    human_msg = HumanMessage(content=email_str)

    init_state = {
        "from_email": clean_from,
        "to_email": target_character,
        "subject": subject,
        "text_content": text_body,
        "messages": [human_msg]
    }

    thread_id = f"thread_{clean_from}_{SMTP_USER}_test"
    print("Invoking graph...")
    try:
        result = app_graph.invoke(init_state, config={"configurable": {"thread_id": thread_id}})
        print("Success! Response:")
        print(result.get("ai_response"))
    except Exception as e:
        print(f"ERROR: {e}")

test()
