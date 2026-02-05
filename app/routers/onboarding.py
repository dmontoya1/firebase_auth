"""Router para el proceso de onboarding de empresas."""

import logging
from typing import Annotated

from firebase_admin import tenant_mgt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionManager
from app.models.company import Company
from app.schemas.onboarding import (
    OnboardingRequest,
    OnboardingResponse,
    TenantInfo,
    TenantsListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get(
    "/tenants",
    response_model=TenantsListResponse,
    summary="Listar tenants",
    description="Lista todos los tenants del proyecto en Identity Platform. Útil para verificar que el registro de compañía creó el tenant correctamente.",
)
async def list_tenants() -> TenantsListResponse:
    """
    Lista los tenants existentes en Google Cloud Identity Platform.

    Returns:
        TenantsListResponse: Lista de tenant_id y display_name.
    """
    try:
        page = tenant_mgt.list_tenants(max_results=100)
        tenants: list[TenantInfo] = []
        for tenant in page.iterate_all():
            tenants.append(
                TenantInfo(tenant_id=tenant.tenant_id, display_name=tenant.display_name)
            )
        return TenantsListResponse(tenants=tenants)
    except Exception as e:
        logger.error(f"Error al listar tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar tenants: {str(e)}",
        )


@router.patch(
    "/tenants/{tenant_id}/enable-password-sign-in",
    summary="Habilitar login con contraseña en un tenant",
    description="Habilita el inicio de sesión con email/contraseña en un tenant existente. Útil si obtuviste PASSWORD_LOGIN_DISABLED al hacer login.",
)
async def enable_password_sign_in(tenant_id: str) -> dict:
    """
    Habilita allow_password_sign_up en el tenant para permitir login con email/contraseña.

    Args:
        tenant_id: ID del tenant (ej. el que devolvió register-company).

    Returns:
        Mensaje de confirmación.
    """
    try:
        tenant_mgt.update_tenant(tenant_id, allow_password_sign_up=True)
        logger.info(f"Password sign-in habilitado para tenant: {tenant_id}")
        return {
            "message": "Login con email/contraseña habilitado para este tenant",
            "tenant_id": tenant_id,
        }
    except Exception as e:
        logger.error(f"Error al habilitar password sign-in para {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


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
            tenant = tenant_mgt.create_tenant(
                display_name=request_data.company_display_name or request_data.company_name,
                allow_password_sign_up=True,  # Necesario para login con email/contraseña
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
                    tenant_mgt.delete_tenant(tenant_id)
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
            tenant_auth = tenant_mgt.auth_for_tenant(tenant_id)
            admin_user = tenant_auth.create_user(
                email=request_data.admin_user.email,
                password=request_data.admin_user.password,
                display_name=request_data.admin_user.display_name,
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
                    tenant_mgt.delete_tenant(tenant_id)
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
                tenant_mgt.delete_tenant(tenant_id)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado durante el proceso de onboarding",
        )
