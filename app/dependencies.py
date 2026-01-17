"""Dependencias de FastAPI para inyección de dependencias."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionManager


def get_tenant_id(request: Request) -> str | None:
    """
    Extrae el tenant_id del estado de la request (inyectado por el middleware).

    Args:
        request: Request HTTP de FastAPI.

    Returns:
        str | None: ID del tenant o None si no está disponible.
    """
    return getattr(request.state, "tenant_id", None)


async def get_db_with_tenant(
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> AsyncSession:
    """
    Dependency que proporciona una sesión de base de datos con RLS configurado.

    Esta dependencia debe usarse en endpoints que requieren autenticación.
    El tenant_id se extrae automáticamente del token de autenticación.

    Args:
        tenant_id: ID del tenant extraído del token.

    Yields:
        AsyncSession: Sesión de base de datos con RLS configurado.

    Raises:
        ValueError: Si no se proporciona tenant_id (usuario no autenticado).
    """
    if not tenant_id:
        raise ValueError(
            "No se ha proporcionado tenant_id. "
            "Asegúrate de que el endpoint requiera autenticación."
        )

    manager = SessionManager(tenant_id=tenant_id)
    async with manager.get_session() as session:
        yield session
