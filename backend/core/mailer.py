import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

def send_smtp_email(to_email: str, subject: str, text_content: str) -> bool:
    """
    Envía un correo oficial a través del servidor SMTP de Gmail usando
    la Contraseña de Aplicación.
    """
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    if not SMTP_USER or not SMTP_PASSWORD:
        print("[ERROR] Credenciales SMTP faltantes en .env")
        return False

    msg = EmailMessage()
    msg.set_content(text_content)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        # Enviar usando SSL puerto 465 (Gmail)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[ERROR] Envio SMTP: {str(e)}")
        return False
