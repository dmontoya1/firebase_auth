"""Tests para app.middleware.auth_middleware."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request
from fastapi.responses import JSONResponse
from firebase_admin import auth as firebase_auth

from app.middleware.auth_middleware import AuthMiddleware, get_firebase_app


class TestGetFirebaseApp:
    """Tests para get_firebase_app."""

    @patch("app.middleware.auth_middleware._firebase_app", None)
    @patch("firebase_admin.initialize_app")
    @patch("app.middleware.auth_middleware.credentials.Certificate")
    @patch("app.middleware.auth_middleware.get_firebase_credentials_from_secret")
    def test_get_firebase_app_con_secret_manager(self, mock_get_secret, mock_cert, mock_init, monkeypatch):
        """Test que inicializa Firebase con Secret Manager."""
        monkeypatch.setattr("app.config.settings.use_secret_manager", True)
        
        mock_credentials = {"type": "service_account"}
        mock_get_secret.return_value = mock_credentials
        mock_cert.return_value = Mock()
        mock_app = Mock()
        mock_init.return_value = mock_app
        
        result = get_firebase_app()
        
        assert result == mock_app
        mock_get_secret.assert_called_once()
        mock_cert.assert_called_once_with(mock_credentials)
        mock_init.assert_called_once()

    @patch("app.middleware.auth_middleware._firebase_app", None)
    @patch("firebase_admin.initialize_app")
    @patch("firebase_admin.credentials.Certificate")
    def test_get_firebase_app_con_archivo(self, mock_cert, mock_init, monkeypatch, tmp_path):
        """Test que inicializa Firebase con archivo."""
        monkeypatch.setattr("app.config.settings.use_secret_manager", False)
        monkeypatch.setattr("app.config.settings.firebase_credentials_path", str(tmp_path / "creds.json"))
        
        mock_app = Mock()
        mock_init.return_value = mock_app
        
        result = get_firebase_app()
        
        assert result == mock_app
        mock_cert.assert_called_once()
        mock_init.assert_called_once()


class TestAuthMiddleware:
    """Tests para AuthMiddleware."""

    @pytest.fixture
    def middleware(self, mock_firebase_app):
        """Fixture para crear middleware."""
        from app.middleware.auth_middleware import AuthMiddleware
        
        app_mock = Mock()
        return AuthMiddleware(app_mock)

    @pytest.fixture
    def mock_request(self):
        """Fixture para crear request mock (headers como Mock para poder setear return_value)."""
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.headers = Mock()
        request.headers.get = Mock(return_value=None)
        request.state = Mock()
        return request

    @pytest.mark.asyncio
    async def test_middleware_permite_health_check(self, middleware, mock_request):
        """Test que el middleware permite /health sin autenticación."""
        mock_request.url.path = "/health"
        mock_call_next = AsyncMock(return_value=Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_middleware_permite_docs(self, middleware, mock_request):
        """Test que el middleware permite /docs sin autenticación."""
        mock_request.url.path = "/docs"
        mock_call_next = AsyncMock(return_value=Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_middleware_permite_onboarding(self, middleware, mock_request):
        """Test que el middleware permite /onboarding sin autenticación."""
        mock_request.url.path = "/onboarding/register-company"
        mock_call_next = AsyncMock(return_value=Mock())
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_middleware_sin_authorization_header(self, middleware, mock_request):
        """Test que el middleware rechaza requests sin Authorization header."""
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = None
        mock_call_next = AsyncMock()
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_token_invalido_formato(self, middleware, mock_request):
        """Test que el middleware rechaza tokens con formato inválido."""
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "InvalidFormat token123"
        mock_call_next = AsyncMock()
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_token_valido(self, middleware, mock_request, mock_firebase_auth):
        """Test que el middleware permite requests con token válido."""
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "Bearer valid-token"
        mock_call_next = AsyncMock(return_value=Mock())
        
        # Mock del token decodificado
        decoded_token = {
            "uid": "user123",
            "email": "user@example.com",
            "firebase": {"tenant": "tenant123"}
        }
        mock_firebase_auth.verify_id_token.return_value = decoded_token
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verificar que se inyectó el tenant_id
        assert hasattr(mock_request.state, "tenant_id")
        assert mock_request.state.tenant_id == "tenant123"
        assert mock_request.state.user_id == "user123"
        assert mock_request.state.user_email == "user@example.com"
        
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_middleware_token_sin_tenant(self, middleware, mock_request, mock_firebase_auth):
        """Test que el middleware rechaza tokens sin tenant_id."""
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "Bearer valid-token"
        mock_call_next = AsyncMock()
        
        # Mock del token sin tenant
        decoded_token = {
            "uid": "user123",
            "email": "user@example.com",
            "firebase": {}
        }
        mock_firebase_auth.verify_id_token.return_value = decoded_token
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 403
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_token_invalido(self, middleware, mock_request, mock_firebase_auth):
        """Test que el middleware rechaza tokens inválidos."""
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "Bearer invalid-token"
        mock_call_next = AsyncMock()
        
        mock_firebase_auth.verify_id_token.side_effect = (
            firebase_auth.InvalidIdTokenError("Invalid token")
        )
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_token_expirado(self, middleware, mock_request, mock_firebase_auth):
        """Test que el middleware rechaza tokens expirados."""
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "Bearer expired-token"
        mock_call_next = AsyncMock()
        
        mock_firebase_auth.verify_id_token.side_effect = (
            firebase_auth.ExpiredIdTokenError("Token expired", cause=Exception("expired"))
        )
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()
