import sqlite3
import os
from datetime import datetime

def monitor():
    db_path = "expediente_abierto_app.db"
    if not os.path.exists(db_path):
        print("La base de datos no existe.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Sesión Activa
    cur.execute("SELECT id, game_id, started_at FROM game_sessions WHERE status = 'active'")
    session = cur.fetchone()

    if not session:
        print("--- No hay sesión activa ---")
    else:
        sid, gid, started = session
        print(f"--- SESIÓN ACTIVA: {gid.upper()} (ID: {sid}) ---")
        print(f"Iniciada: {started}")

        # Mensajes Enviados
        cur.execute("SELECT from_email, to_email, subject, sent_at FROM messages WHERE session_id = ? ORDER BY sent_at DESC LIMIT 5", (sid,))
        messages = cur.fetchall()
        print("\n--- ÚLTIMOS MENSAJES ENTREGADOS ---")
        if not messages:
            print("Ninguno aún.")
        for m in messages:
            print(f"[{m[3]}] {m[0]} -> {m[1]} | {m[2]}")

        # Mensajes Programados (Time Guardian)
        cur.execute("SELECT from_email, scheduled_at, created_at FROM scheduled_messages WHERE session_id = ? AND is_delivered = 0", (sid,))
        scheduled = cur.fetchall()
        print("\n--- COLA DEL GUARDIÁN DEL TIEMPO ---")
        if not scheduled:
            print("Vacía.")
        for s in scheduled:
            print(f"PROGRAMADO: {s[1]} (Generado: {s[2]})")
            print(f"DE: {s[0]}")

    conn.close()

if __name__ == "__main__":
    monitor()
