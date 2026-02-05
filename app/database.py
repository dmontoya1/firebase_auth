"""Gestión de conexiones a la base de datos con soporte RLS."""

import contextlib
import re
from typing import AsyncGenerator, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config import settings

# Base para los modelos
Base = declarative_base()

# Motor asíncrono de SQLAlchemy
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.debug,
    future=True,
)

# Factory para crear sesiones
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Formato esperado de tenant_id (Firebase/Identity Platform: alfanumérico y guiones)
_TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]+$")


def _safe_rls_value(value: str) -> str:
    """Escapa un valor para usarlo como literal en SET LOCAL (evita SQL injection)."""
    if not _TENANT_ID_PATTERN.match(value):
        raise ValueError(
            f"tenant_id inválido: solo se permiten letras, números, guiones y guión bajo."
        )
    return value.replace("'", "''")


class SessionManager:
    """
    Gestor de sesiones que ejecuta automáticamente SET app.current_tenant
    antes de cada consulta para habilitar Row Level Security (RLS).
    """

    def __init__(self, tenant_id: Optional[str] = None):
        """
        Inicializa el gestor de sesiones.

        Args:
            tenant_id: ID del tenant a establecer en la sesión de PostgreSQL.
        """
        self.tenant_id = tenant_id

    @contextlib.asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager que proporciona una sesión con RLS configurado.

        Yields:
            AsyncSession: Sesión de SQLAlchemy con el tenant configurado.

        Raises:
            ValueError: Si no se ha establecido un tenant_id.
        """
        if not self.tenant_id:
            raise ValueError(
                "No se ha establecido un tenant_id. "
                "Asegúrate de que el middleware de autenticación lo haya configurado."
            )

        safe_value = _safe_rls_value(self.tenant_id)
        rls_name = settings.rls_setting_name
        # SET LOCAL no acepta parámetros ($1) en PostgreSQL; el valor debe ser literal.
        set_sql = text(f"SET LOCAL {rls_name} = '{safe_value}'")

        async with AsyncSessionLocal() as session:
            # Establecer el tenant en la sesión de PostgreSQL para RLS
            await session.execute(set_sql)

            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                # Limpiar la variable de sesión (opcional, pero buena práctica)
                await session.execute(text(f"RESET {settings.rls_setting_name}"))


# Función helper para obtener sesión (para uso en dependencias de FastAPI)
async def get_db_session(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency de FastAPI para obtener una sesión de base de datos con RLS.

    Args:
        tenant_id: ID del tenant extraído del token de autenticación.

    Yields:
        AsyncSession: Sesión de SQLAlchemy configurada con el tenant.
    """
    manager = SessionManager(tenant_id=tenant_id)
    async with manager.get_session() as session:
        yield session


async def init_db() -> None:
    """Inicializa las tablas en la base de datos (solo para desarrollo)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Cierra las conexiones de la base de datos."""
    await engine.dispose()
