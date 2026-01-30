"""Tests para app.dependencies."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request

from app.dependencies import get_tenant_id, get_db_with_tenant


class TestGetTenantId:
    """Tests para get_tenant_id."""

    def test_get_tenant_id_existe(self):
        """Test que get_tenant_id retorna el tenant_id del request."""
        request = Mock(spec=Request)
        request.state.tenant_id = "test-tenant-123"
        
        result = get_tenant_id(request)
        
        assert result == "test-tenant-123"

    def test_get_tenant_id_no_existe(self):
        """Test que get_tenant_id retorna None si no existe."""
        request = Mock(spec=Request)
        delattr(request.state, "tenant_id")
        
        result = get_tenant_id(request)
        
        assert result is None


class TestGetDbWithTenant:
    """Tests para get_db_with_tenant."""

    @pytest.mark.asyncio
    async def test_get_db_with_tenant_exitoso(self):
        """Test que get_db_with_tenant funciona con tenant_id."""
        tenant_id = "test-tenant-123"
        
        with patch("app.dependencies.SessionManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_session = AsyncMock()
            mock_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            async for session in get_db_with_tenant(tenant_id=tenant_id):
                assert session == mock_session
            
            mock_manager_class.assert_called_once_with(tenant_id=tenant_id)

    @pytest.mark.asyncio
    async def test_get_db_with_tenant_sin_tenant_id_falla(self):
        """Test que get_db_with_tenant falla sin tenant_id."""
        with pytest.raises(ValueError, match="No se ha proporcionado tenant_id"):
            async for _ in get_db_with_tenant(tenant_id=None):
                pass
