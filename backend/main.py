from fastapi import FastAPI
from api.webhook import router as webhook_router
from database.database import engine
import database.models as models

# Crea las tablas si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Expediente Abierto - API MVP",
    description="API que maneja la lógica de emails y agentes del caso",
    version="0.1.0"
)

app.include_router(webhook_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Expediente Abierto Backend is running"}
