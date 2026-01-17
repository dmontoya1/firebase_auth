"""Modelo base con soporte multi-tenant."""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import declared_attr

from app.config import settings
from app.database import Base


class TenantAwareModel(Base):
    """
    Modelo base abstracto que incluye automáticamente la columna tenant_id.

    Todas las tablas que hereden de este modelo tendrán automáticamente:
    - tenant_id: ID del tenant (discriminador de fila)
    - created_at: Timestamp de creación
    - updated_at: Timestamp de última actualización
    """

    __abstract__ = True

    @declared_attr
    def tenant_id(cls) -> Column[str]:
        """Columna discriminadora de tenant configurable."""
        return Column(
            String(255),
            nullable=False,
            name=settings.tenant_id_column_name,
            index=True,
            comment="ID del tenant para Row Level Security",
        )

    @declared_attr
    def created_at(cls) -> Column[datetime]:
        """Timestamp de creación del registro."""
        return Column(
            DateTime(timezone=True),
            default=datetime.utcnow,
            nullable=False,
            comment="Fecha y hora de creación",
        )

    @declared_attr
    def updated_at(cls) -> Column[datetime]:
        """Timestamp de última actualización."""
        return Column(
            DateTime(timezone=True),
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
            comment="Fecha y hora de última actualización",
        )
