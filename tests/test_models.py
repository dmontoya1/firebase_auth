"""Tests para los modelos de base de datos."""

import pytest
from datetime import datetime

from app.models.base import TenantAwareModel
from app.models.company import Company
from app.config import settings


class TestTenantAwareModel:
    """Tests para TenantAwareModel."""

    def test_tenant_aware_model_es_abstracto(self):
        """Test que TenantAwareModel es abstracto."""
        # Intentar crear una instancia directa debería fallar
        with pytest.raises(TypeError):
            TenantAwareModel()

    def test_tenant_aware_model_tiene_tenant_id_column(self):
        """Test que TenantAwareModel tiene columna tenant_id."""
        # Verificar que Company (que hereda de TenantAwareModel) tiene tenant_id
        assert hasattr(Company, "tenant_id")
        
        # Verificar que la columna tiene el nombre correcto
        tenant_column = Company.__table__.columns.get(settings.tenant_id_column_name)
        assert tenant_column is not None
        assert tenant_column.nullable is False

    def test_tenant_aware_model_tiene_timestamps(self):
        """Test que TenantAwareModel tiene created_at y updated_at."""
        assert hasattr(Company, "created_at")
        assert hasattr(Company, "updated_at")
        
        created_column = Company.__table__.columns.get("created_at")
        updated_column = Company.__table__.columns.get("updated_at")
        
        assert created_column is not None
        assert updated_column is not None


class TestCompany:
    """Tests para el modelo Company."""

    def test_company_tiene_tablename(self):
        """Test que Company tiene __tablename__ definido."""
        assert Company.__tablename__ == "companies"

    def test_company_tiene_columnas_esperadas(self):
        """Test que Company tiene todas las columnas esperadas."""
        columns = {col.name for col in Company.__table__.columns}
        
        expected_columns = {
            settings.tenant_id_column_name,
            "name",
            "display_name",
            "description",
            "status",
            "created_at",
            "updated_at",
        }
        
        assert expected_columns.issubset(columns)

    def test_company_name_no_nullable(self):
        """Test que la columna name no es nullable."""
        name_column = Company.__table__.columns.get("name")
        assert name_column.nullable is False

    def test_company_status_tiene_default(self):
        """Test que status tiene valor por defecto."""
        status_column = Company.__table__.columns.get("status")
        assert status_column.default is not None

    def test_company_repr(self):
        """Test que __repr__ funciona correctamente."""
        # Crear instancia sin guardar
        company = Company(
            tenant_id="test-tenant",
            name="Test Company",
        )
        
        repr_str = repr(company)
        assert "Company" in repr_str
        assert "test-tenant" in repr_str
        assert "Test Company" in repr_str
