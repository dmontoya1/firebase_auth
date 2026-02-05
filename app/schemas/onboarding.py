"""Esquemas Pydantic para el proceso de onboarding."""

from pydantic import BaseModel, EmailStr, Field


class AdminUserCreate(BaseModel):
    """Esquema para crear el usuario administrador inicial."""

    email: EmailStr = Field(..., description="Email del administrador")
    password: str = Field(
        ..., min_length=8, description="Contraseña del administrador"
    )
    display_name: str | None = Field(
        None, max_length=255, description="Nombre para mostrar"
    )


class OnboardingRequest(BaseModel):
    """Esquema para el request de onboarding."""

    company_name: str = Field(
        ..., min_length=1, max_length=255, description="Nombre de la empresa"
    )
    company_display_name: str | None = Field(
        None, max_length=255, description="Nombre para mostrar de la empresa"
    )
    company_description: str | None = Field(
        None, description="Descripción de la empresa"
    )
    admin_user: AdminUserCreate = Field(..., description="Datos del administrador inicial")


class OnboardingResponse(BaseModel):
    """Esquema de respuesta del onboarding."""

    tenant_id: str = Field(..., description="ID del tenant creado en Identity Platform")
    company_id: str = Field(..., description="ID de la empresa en la base de datos")
    admin_user_id: str = Field(..., description="ID del usuario administrador creado")
    message: str = Field(..., description="Mensaje de confirmación")


class TenantInfo(BaseModel):
    """Esquema de un tenant para listado."""

    tenant_id: str = Field(..., description="ID del tenant en Identity Platform")
    display_name: str = Field(..., description="Nombre para mostrar del tenant")


class TenantsListResponse(BaseModel):
    """Esquema de respuesta del listado de tenants."""

    tenants: list[TenantInfo] = Field(..., description="Lista de tenants del proyecto")
