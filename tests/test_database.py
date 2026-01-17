"""Tests para app.database."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.database import SessionManager, get_db_session
from app.config import Settings


class TestSessionManager:
    """Tests para SessionManager."""

    @pytest.mark.asyncio
    async def test_session_manager_sin_tenant_id_falla(self):
        """Test que SessionManager falla sin tenant_id."""
        manager = SessionManager(tenant_id=None)
        
        with pytest.raises(ValueError, match="No se ha establecido un tenant_id"):
            async with manager.get_session():
                pass

    @pytest.mark.asyncio
    async def test_session_manager_establece_tenant(self):
        """Test que SessionManager establece el tenant en la sesión."""
        tenant_id = "test-tenant-123"
        
        with patch("app.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            manager = SessionManager(tenant_id=tenant_id)
            
            async with manager.get_session() as session:
                # Verificar que se ejecutó SET LOCAL
                calls = [str(call) for call in mock_session.execute.call_args_list]
                assert any("SET LOCAL" in str(call) for call in calls)
                assert any("app.current_tenant" in str(call) for call in calls)
                assert any(tenant_id in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_session_manager_hace_commit_exitoso(self):
        """Test que SessionManager hace commit cuando no hay errores."""
        with patch("app.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            manager = SessionManager(tenant_id="test-tenant")
            
            async with manager.get_session():
                pass
            
            # Verificar que se llamó commit
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_manager_hace_rollback_en_error(self):
        """Test que SessionManager hace rollback cuando hay errores."""
        with patch("app.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            manager = SessionManager(tenant_id="test-tenant")
            
            try:
                async with manager.get_session():
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            # Verificar que se llamó rollback
            mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_manager_resetea_variable(self):
        """Test que SessionManager resetea la variable de sesión."""
        with patch("app.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            manager = SessionManager(tenant_id="test-tenant")
            
            async with manager.get_session():
                pass
            
            # Verificar que se ejecutó RESET
            calls = [str(call) for call in mock_session.execute.call_args_list]
            assert any("RESET" in str(call) for call in calls)


class TestGetDbSession:
    """Tests para la función get_db_session."""

    @pytest.mark.asyncio
    async def test_get_db_session_con_tenant_id(self):
        """Test que get_db_session funciona con tenant_id."""
        tenant_id = "test-tenant-123"
        
        with patch("app.database.SessionManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            async for session in get_db_session(tenant_id=tenant_id):
                assert session is not None
            
            # Verificar que se creó SessionManager con el tenant_id correcto
            mock_manager_class.assert_called_once_with(tenant_id=tenant_id)

    @pytest.mark.asyncio
    async def test_get_db_session_sin_tenant_id(self):
        """Test que get_db_session funciona sin tenant_id."""
        with patch("app.database.SessionManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            async for session in get_db_session(tenant_id=None):
                assert session is not None
            
            # Verificar que se creó SessionManager sin tenant_id
            mock_manager_class.assert_called_once_with(tenant_id=None)
