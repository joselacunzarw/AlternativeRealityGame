from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from api.webhook import router as webhook_router
from api.cases import router as cases_router
from api.users import router as users_router
from database.database import engine
from core.imap_poller import start_imap_poller
import database.models as models

# Crea las tablas si no existen
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranca el Escaner IMAP F&F silencioso
    task = asyncio.create_task(start_imap_poller())
    yield
    # Cancela ordenadamente al cerrar el servidor
    task.cancel()

app = FastAPI(
    title="Expediente Abierto - API MVP",
    description="API que maneja la lógica de emails y agentes del caso",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Expediente Abierto Backend is running"}
