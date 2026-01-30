"""Modelo de la tabla Company (Tenant)."""

from sqlalchemy import PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.models.base import TenantAwareModel


class Company(TenantAwareModel):
    """
    Modelo que representa una empresa/tenant en el sistema.

    El tenant_id es el ID devuelto por Google Cloud Identity Platform
    al crear un nuevo tenant.
    """

    __tablename__ = "companies"
    __table_args__ = (PrimaryKeyConstraint(settings.tenant_id_column_name),)

    # El tenant_id ya está incluido por TenantAwareModel
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre de la empresa",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nombre para mostrar de la empresa",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Descripción de la empresa",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        comment="Estado de la empresa (active, inactive, suspended)",
    )

    def __repr__(self) -> str:
        """Representación del objeto."""
        return f"<Company(id={self.tenant_id}, name={self.name})>"
