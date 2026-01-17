"""Modelo de la tabla Company (Tenant)."""

from sqlalchemy import Column, String, Text

from app.models.base import TenantAwareModel


class Company(TenantAwareModel):
    """
    Modelo que representa una empresa/tenant en el sistema.

    El tenant_id es el ID devuelto por Google Cloud Identity Platform
    al crear un nuevo tenant.
    """

    __tablename__ = "companies"

    # El tenant_id ya está incluido por TenantAwareModel
    name = Column(
        String(255),
        nullable=False,
        comment="Nombre de la empresa",
    )
    display_name = Column(
        String(255),
        nullable=True,
        comment="Nombre para mostrar de la empresa",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Descripción de la empresa",
    )
    status = Column(
        String(50),
        default="active",
        nullable=False,
        comment="Estado de la empresa (active, inactive, suspended)",
    )

    def __repr__(self) -> str:
        """Representación del objeto."""
        return f"<Company(id={self.tenant_id}, name={self.name})>"
