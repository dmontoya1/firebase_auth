"""Aplicación principal FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_db, init_db
from app.middleware.auth_middleware import AuthMiddleware, get_firebase_app
from app.routers import example, health, onboarding

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager para eventos de startup y shutdown.

    Args:
        app: Instancia de FastAPI.
    """
    # Startup
    logger.info(f"Iniciando {settings.project_name} en modo {settings.environment}")
    
    # Inicializar Firebase Admin SDK
    get_firebase_app()
    logger.info("Firebase Admin SDK inicializado")

    # Inicializar base de datos (solo para desarrollo)
    if settings.environment == "development":
        try:
            await init_db()
            logger.info("Base de datos inicializada")
        except Exception as e:
            logger.warning(f"No se pudo inicializar la base de datos: {e}")

    yield

    # Shutdown
    logger.info("Cerrando conexiones...")
    await close_db()
    logger.info("Aplicación cerrada correctamente")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.project_name,
    description="Microservicio de Autenticación y Onboarding Multi-tenant",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware de autenticación
app.add_middleware(AuthMiddleware)

# Incluir routers
app.include_router(health.router)
app.include_router(onboarding.router)
app.include_router(example.router)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Endpoint raíz.

    Returns:
        dict: Información del servicio.
    """
    return {
        "service": settings.project_name,
        "version": "1.0.0",
        "status": "running",
    }
