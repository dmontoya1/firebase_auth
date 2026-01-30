"""Tests para los routers."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import status

from app.routers import health, onboarding


class TestHealthRouter:
    """Tests para el router de health."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test que el endpoint de health check funciona."""
        response = await health.health_check()
        
        assert isinstance(response, dict)
        assert "status" in response
        assert response["status"] == "healthy"
        assert "service" in response


class TestOnboardingRouter:
    """Tests para el router de onboarding."""

    @pytest.fixture
    def sample_request(self):
        """Request de ejemplo para onboarding."""
        from app.schemas.onboarding import OnboardingRequest, AdminUserCreate
        
        return OnboardingRequest(
            company_name="Test Company",
            company_display_name="Test Company Display",
            company_description="A test company",
            admin_user=AdminUserCreate(
                email="admin@test.com",
                password="SecurePassword123!",
                display_name="Admin User"
            )
        )

    @pytest.mark.asyncio
    @patch("app.routers.onboarding.auth.create_tenant", create=True)
    @patch("app.routers.onboarding.auth.create_user")
    @patch("app.routers.onboarding.SessionManager")
    async def test_register_company_exitoso(
        self,
        mock_session_manager,
        mock_create_user,
        mock_create_tenant,
        sample_request
    ):
        """Test que register_company funciona correctamente."""
        # Configurar mocks
        mock_tenant = Mock()
        mock_tenant.tenant_id = "tenant-123"
        mock_create_tenant.return_value = mock_tenant
        
        mock_user = Mock()
        mock_user.uid = "user-123"
        mock_create_user.return_value = mock_user
        
        mock_db = AsyncMock()
        mock_db.add = Mock()  # add() es síncrono en SQLAlchemy
        mock_session_manager.return_value.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_manager.return_value.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Ejecutar
        response = await onboarding.register_company(sample_request)
        
        # Verificar
        assert response.tenant_id == "tenant-123"
        assert response.company_id == "tenant-123"
        assert response.admin_user_id == "user-123"
        assert "exitosamente" in response.message.lower()
        
        # Verificar que se llamaron las funciones correctas
        mock_create_tenant.assert_called_once()
        mock_create_user.assert_called_once()
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.routers.onboarding.auth.create_tenant", create=True)
    @patch("app.routers.onboarding.auth.delete_tenant", create=True)
    async def test_register_company_falla_crear_tenant(
        self,
        mock_delete_tenant,
        mock_create_tenant,
        sample_request
    ):
        """Test que register_company hace rollback si falla crear tenant."""
        mock_create_tenant.side_effect = Exception("Error creating tenant")
        
        with pytest.raises(Exception):
            await onboarding.register_company(sample_request)
        
        # No debería intentar eliminar tenant si no se creó
        mock_delete_tenant.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.routers.onboarding.auth.create_tenant", create=True)
    @patch("app.routers.onboarding.auth.delete_tenant", create=True)
    @patch("app.routers.onboarding.SessionManager")
    async def test_register_company_falla_db_hace_rollback(
        self,
        mock_session_manager,
        mock_delete_tenant,
        mock_create_tenant,
        sample_request
    ):
        """Test que register_company hace rollback si falla la DB."""
        # Configurar mocks
        mock_tenant = Mock()
        mock_tenant.tenant_id = "tenant-123"
        mock_create_tenant.return_value = mock_tenant
        
        mock_db = AsyncMock()
        mock_db.add = Mock(side_effect=Exception("DB Error"))  # add() es síncrono
        mock_session_manager.return_value.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_manager.return_value.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Ejecutar
        with pytest.raises(Exception):
            await onboarding.register_company(sample_request)
        
        # Verificar que se intentó eliminar el tenant
        mock_delete_tenant.assert_called_once_with("tenant-123")

    @pytest.mark.asyncio
    @patch("app.routers.onboarding.auth.create_tenant", create=True)
    @patch("app.routers.onboarding.auth.create_user")
    @patch("app.routers.onboarding.auth.delete_tenant", create=True)
    @patch("app.routers.onboarding.SessionManager")
    @patch("app.routers.onboarding.select")
    async def test_register_company_falla_crear_usuario_hace_rollback(
        self,
        mock_select,
        mock_session_manager,
        mock_delete_tenant,
        mock_create_user,
        mock_create_tenant,
        sample_request
    ):
        """Test que register_company hace rollback si falla crear usuario."""
        # Configurar mocks
        mock_tenant = Mock()
        mock_tenant.tenant_id = "tenant-123"
        mock_create_tenant.return_value = mock_tenant
        
        mock_create_user.side_effect = Exception("Error creating user")
        
        mock_db = AsyncMock()
        mock_db.add = Mock()  # add() es síncrono en SQLAlchemy
        mock_company = Mock()
        mock_company.tenant_id = "tenant-123"
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_company
        mock_db.execute = AsyncMock(return_value=mock_result)  # execute() es async
        mock_session_manager.return_value.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_manager.return_value.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Ejecutar
        with pytest.raises(Exception):
            await onboarding.register_company(sample_request)
        
        # Verificar que se intentó eliminar el tenant y la empresa
        mock_delete_tenant.assert_called_once_with("tenant-123")
        mock_db.delete.assert_called_once()
