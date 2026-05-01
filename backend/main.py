# Cargar variables de entorno ANTES de cualquier import que las necesite
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import os
from api.webhook import router as webhook_router
from api.cases import router as cases_router
from api.users import router as users_router
from api.vault import router as vault_router
from database.database import engine
from core.imap_poller import start_imap_poller
from core.delivery_worker import start_delivery_worker
from core.nudge_engine import start_nudge_engine
from core.event_engine import start_event_engine
import database.models as models

# Crea las tablas si no existen
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranca los servicios de fondo
    imap_task = asyncio.create_task(start_imap_poller())
    delivery_task = asyncio.create_task(start_delivery_worker())
    nudge_task = asyncio.create_task(start_nudge_engine())
    event_task = asyncio.create_task(start_event_engine())
    yield
    # Cancela ordenadamente al cerrar el servidor
    for task in [imap_task, delivery_task, nudge_task, event_task]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass  # Esperado: la tarea fue cancelada exitosamente

app = FastAPI(
    title="Expediente Abierto - API MVP",
    description="API que maneja la lógica de emails y agentes del caso",
    version="0.1.0",
    lifespan=lifespan
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(vault_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Expediente Abierto Backend is running"}
