"""Tests para app.utils.secret_manager."""

import json
import pytest
from unittest.mock import Mock, patch
from google.api_core import exceptions as gcp_exceptions

from app.utils.secret_manager import get_firebase_credentials_from_secret
from app.config import settings


class TestGetFirebaseCredentialsFromSecret:
    """Tests para get_firebase_credentials_from_secret."""

    @pytest.fixture(autouse=True)
    def setup_mock_settings(self, monkeypatch):
        """Configura settings mock para los tests."""
        monkeypatch.setattr(settings, "use_secret_manager", True)
        monkeypatch.setattr(settings, "gcp_project_id", "test-project")
        monkeypatch.setattr(settings, "firebase_credentials_secret_name", "test-secret")

    def test_get_credentials_exitoso(self, mock_secret_manager_client):
        """Test que obtiene credenciales exitosamente desde Secret Manager."""
        # Configurar mock
        mock_response = Mock()
        mock_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK\n-----END PRIVATE KEY-----\n",
        }
        mock_response.payload.data = json.dumps(mock_credentials).encode("UTF-8")
        mock_secret_manager_client.access_secret_version.return_value = mock_response
        
        # Ejecutar
        result = get_firebase_credentials_from_secret()
        
        # Verificar
        assert result == mock_credentials
        mock_secret_manager_client.access_secret_version.assert_called_once()
        call_args = mock_secret_manager_client.access_secret_version.call_args
        assert "test-project" in str(call_args)
        assert "test-secret" in str(call_args)

    def test_get_credentials_use_secret_manager_false_falla(self, monkeypatch):
        """Test que falla si use_secret_manager está deshabilitado."""
        monkeypatch.setattr(settings, "use_secret_manager", False)
        
        with pytest.raises(ValueError, match="use_secret_manager está deshabilitado"):
            get_firebase_credentials_from_secret()

    def test_get_credentials_sin_gcp_project_id_falla(self, monkeypatch):
        """Test que falla si gcp_project_id no está configurado."""
        monkeypatch.setattr(settings, "gcp_project_id", None)
        
        with pytest.raises(ValueError, match="gcp_project_id no está configurado"):
            get_firebase_credentials_from_secret()

    def test_get_credentials_sin_secret_name_falla(self, monkeypatch):
        """Test que falla si firebase_credentials_secret_name no está configurado."""
        monkeypatch.setattr(settings, "firebase_credentials_secret_name", None)
        
        with pytest.raises(ValueError, match="firebase_credentials_secret_name no está configurado"):
            get_firebase_credentials_from_secret()

    def test_get_credentials_permission_denied(self, mock_secret_manager_client):
        """Test que maneja correctamente PermissionDenied."""
        mock_secret_manager_client.access_secret_version.side_effect = (
            gcp_exceptions.PermissionDenied("Permission denied")
        )
        
        with pytest.raises(RuntimeError, match="No se tienen permisos"):
            get_firebase_credentials_from_secret()

    def test_get_credentials_not_found(self, mock_secret_manager_client):
        """Test que maneja correctamente NotFound."""
        mock_secret_manager_client.access_secret_version.side_effect = (
            gcp_exceptions.NotFound("Secret not found")
        )
        
        with pytest.raises(ValueError, match="Secreto no encontrado"):
            get_firebase_credentials_from_secret()

    def test_get_credentials_json_invalido(self, mock_secret_manager_client):
        """Test que maneja correctamente JSON inválido (el código re-lanza como RuntimeError)."""
        mock_response = Mock()
        mock_response.payload.data = b"not valid json"
        mock_secret_manager_client.access_secret_version.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="JSON válido|Secret Manager|comunicarse"):
            get_firebase_credentials_from_secret()

    def test_get_credentials_error_generico(self, mock_secret_manager_client):
        """Test que maneja correctamente errores genéricos."""
        mock_secret_manager_client.access_secret_version.side_effect = Exception("Generic error")
        
        with pytest.raises(RuntimeError, match="Error al comunicarse"):
            get_firebase_credentials_from_secret()
