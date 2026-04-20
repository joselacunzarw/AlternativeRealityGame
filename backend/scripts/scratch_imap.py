import imaplib
import email
import os
from email.header import decode_header
from dotenv import load_dotenv

load_dotenv()

def scan():
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(SMTP_USER, SMTP_PASSWORD)
    mail.select("inbox")
    
    # fetch the last 3 emails
    status, messages = mail.search(None, "ALL")
    if messages[0]:
        msg_nums = messages[0].split()[-3:]
        for num in msg_nums:
            st, data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            subj = decode_header(msg["Subject"])[0]
            decoded_subj = subj[0]
            if isinstance(decoded_subj, bytes):
                decoded_subj = decoded_subj.decode(subj[1] or 'utf-8', errors='ignore')
            print(f"[{num}] Subject: {decoded_subj}")
            
            # extraemos body
            text_body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        text_body = part.get_payload(decode=True).decode("utf-8", errors='ignore')
                        break
            else:
                text_body = msg.get_payload(decode=True).decode("utf-8", errors='ignore')

            safe_body = text_body[:300].encode("ascii", "ignore").decode()
            print(f"BODY:\n{safe_body}...\n")
            
            st_flg, data_flg = mail.fetch(num, "(FLAGS)")
            print(f"FLAGS: {data_flg}\n---")

scan()
