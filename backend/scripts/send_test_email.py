import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def send_test():
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    subject = "Re: CASO ABIERTO: El experimento || Expediente Abierto"
    body = "@elena.vasquez Hola Doctora. Soy el investigador externo que el Dr. Moreno contrató. Escuché rumores de que usted está preocupada por el tema de los sueños. Hábleme con libertad."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = SMTP_USER

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print("Correo simulado hacia Elena Vásquez despachado a la bandeja.")
    except Exception as e:
        print(f"Error despachando: {e}")

if __name__ == "__main__":
    send_test()
