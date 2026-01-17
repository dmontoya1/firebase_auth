"""Esquemas Pydantic para el modelo Company."""

from datetime import datetime

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    """Esquema para crear una nueva empresa."""

    name: str = Field(..., min_length=1, max_length=255, description="Nombre de la empresa")
    display_name: str | None = Field(
        None, max_length=255, description="Nombre para mostrar"
    )
    description: str | None = Field(None, description="Descripción de la empresa")


class CompanyResponse(BaseModel):
    """Esquema de respuesta para una empresa."""

    tenant_id: str = Field(..., description="ID del tenant en Identity Platform")
    name: str = Field(..., description="Nombre de la empresa")
    display_name: str | None = Field(None, description="Nombre para mostrar")
    description: str | None = Field(None, description="Descripción")
    status: str = Field(..., description="Estado de la empresa")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    model_config = {"from_attributes": True}
