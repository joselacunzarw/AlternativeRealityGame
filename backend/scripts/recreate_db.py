"""Elimina y recrea la base de datos desde cero con el schema actualizado."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import engine
from database import models

models.Base.metadata.create_all(bind=engine)
print("DB recreada correctamente.")

import sqlite3
conn = sqlite3.connect("expediente_abierto_app.db")
cur = conn.cursor()
cur.execute("PRAGMA table_info(game_sessions)")
cols = [r[1] for r in cur.fetchall()]
print("Columnas game_sessions:", cols)
conn.close()
