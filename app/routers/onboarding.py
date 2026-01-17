"""Router para el proceso de onboarding de empresas."""

import logging
from typing import Annotated

import firebase_admin
from firebase_admin import auth
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionManager
from app.models.company import Company
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post(
    "/register-company",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(
    request_data: OnboardingRequest,
) -> OnboardingResponse:
    """
    Endpoint de onboarding que crea un nuevo tenant y empresa.

    Este endpoint realiza una transacción atómica:
    1. Crea un nuevo tenant en Google Cloud Identity Platform
    2. Inserta el registro de la empresa en la base de datos
    3. Crea el usuario administrador inicial dentro del tenant

    Si algo falla, se hace rollback de todo.

    Args:
        request_data: Datos de la empresa y administrador.

    Returns:
        OnboardingResponse: Información del tenant y empresa creados.

    Raises:
        HTTPException: Si ocurre un error en el proceso.
    """
    tenant_id: str | None = None
    admin_user_id: str | None = None

    try:
        # Paso 1: Crear tenant en Google Cloud Identity Platform
        logger.info(f"Creando tenant en Identity Platform para: {request_data.company_name}")
        try:
            tenant = auth.create_tenant(
                display_name=request_data.company_display_name or request_data.company_name
            )
            tenant_id = tenant.tenant_id
            logger.info(f"Tenant creado exitosamente: {tenant_id}")
        except Exception as e:
            logger.error(f"Error al crear tenant en Identity Platform: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear tenant en Identity Platform: {str(e)}",
            )

        # Paso 2: Insertar empresa en la base de datos
        logger.info(f"Insertando empresa en base de datos: {request_data.company_name}")
        try:
            # Usar SessionManager con el tenant_id para esta operación
            async with SessionManager(tenant_id=tenant_id).get_session() as db:
                # Crear registro de empresa con el tenant_id de Identity Platform
                new_company = Company(
                    tenant_id=tenant_id,
                    name=request_data.company_name,
                    display_name=request_data.company_display_name,
                    description=request_data.company_description,
                    status="active",
                )

                db.add(new_company)
                await db.flush()  # Para obtener el ID sin hacer commit
                company_id = new_company.tenant_id  # En este caso, tenant_id es el ID

            logger.info(f"Empresa insertada exitosamente: {company_id}")

        except Exception as e:
            logger.error(f"Error al insertar empresa en base de datos: {str(e)}")
            # Rollback: Eliminar tenant de Identity Platform
            if tenant_id:
                try:
                    auth.delete_tenant(tenant_id)
                    logger.info(f"Tenant {tenant_id} eliminado debido a error en DB")
                except Exception as delete_error:
                    logger.error(
                        f"Error al eliminar tenant durante rollback: {str(delete_error)}"
                    )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear empresa en base de datos: {str(e)}",
            )

        # Paso 3: Crear usuario administrador dentro del tenant
        logger.info(f"Creando usuario administrador: {request_data.admin_user.email}")
        try:
            admin_user = auth.create_user(
                email=request_data.admin_user.email,
                password=request_data.admin_user.password,
                display_name=request_data.admin_user.display_name,
                tenant_id=tenant_id,
            )
            admin_user_id = admin_user.uid
            logger.info(f"Usuario administrador creado exitosamente: {admin_user_id}")

        except Exception as e:
            logger.error(f"Error al crear usuario administrador: {str(e)}")
            # Rollback: Eliminar empresa de la base de datos y tenant de Identity Platform
            if tenant_id:
                try:
                    # Eliminar empresa de la base de datos
                    async with SessionManager(tenant_id=tenant_id).get_session() as db:
                        result = await db.execute(
                            select(Company).where(Company.tenant_id == tenant_id)
                        )
                        company = result.scalar_one_or_none()
                        if company:
                            await db.delete(company)
                            await db.commit()

                    # Eliminar tenant de Identity Platform
                    auth.delete_tenant(tenant_id)
                    logger.info(
                        f"Rollback completado: empresa y tenant {tenant_id} eliminados"
                    )
                except Exception as rollback_error:
                    logger.error(
                        f"Error durante rollback: {str(rollback_error)}",
                        exc_info=True,
                    )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear usuario administrador: {str(e)}",
            )

        # Todo exitoso
        return OnboardingResponse(
            tenant_id=tenant_id,
            company_id=company_id,
            admin_user_id=admin_user_id,
            message="Empresa y usuario administrador creados exitosamente",
        )

    except HTTPException:
        # Re-lanzar HTTPException sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en onboarding: {str(e)}", exc_info=True)
        # Rollback final por si acaso
        if tenant_id:
            try:
                auth.delete_tenant(tenant_id)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado durante el proceso de onboarding",
        )
