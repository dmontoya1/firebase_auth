"""
Ejemplo de router que muestra cómo usar el sistema multi-tenant.

Este archivo es solo un ejemplo y puede ser eliminado en producción.
Muestra cómo usar las dependencias para obtener sesiones de DB con RLS.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_with_tenant
from app.models.company import Company
from app.schemas.company import CompanyResponse

router = APIRouter(prefix="/example", tags=["example"])


@router.get("/my-company", response_model=CompanyResponse)
async def get_my_company(
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
) -> CompanyResponse:
    """
    Ejemplo de endpoint que requiere autenticación y usa RLS.

    Este endpoint:
    1. Requiere un token Bearer válido (verificado por el middleware)
    2. Extrae automáticamente el tenant_id del token
    3. Usa una sesión de DB con RLS configurado
    4. Solo puede ver/editar datos de su propio tenant

    Args:
        db: Sesión de base de datos con RLS configurado para el tenant del usuario.

    Returns:
        CompanyResponse: Información de la empresa del tenant actual.
    """
    # La consulta solo devolverá registros del tenant del usuario
    # gracias a RLS configurado en PostgreSQL
    result = await db.execute(
        select(Company).where(Company.status == "active")
    )
    company = result.scalar_one_or_none()

    if not company:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada",
        )

    return CompanyResponse.model_validate(company)
