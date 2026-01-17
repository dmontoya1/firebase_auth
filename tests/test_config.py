"""Tests para app.config."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from app.config import Settings


class TestSettings:
    """Tests para la clase Settings."""

    def test_settings_creacion_minima(self, tmp_path):
        """Test que Settings se puede crear con valores mínimos."""
        # Crear archivo de credenciales temporal
        cred_file = tmp_path / "test-creds.json"
        cred_file.write_text('{"type": "service_account"}')
        
        settings = Settings(
            project_name="test",
            db_host="localhost",
            db_user="user",
            db_password="pass",
            db_name="db",
            use_secret_manager=False,
            firebase_credentials_path=str(cred_file),
        )
        
        assert settings.project_name == "test"
        assert settings.db_host == "localhost"
        assert settings.use_secret_manager is False

    def test_settings_con_secret_manager(self):
        """Test que Settings valida correctamente cuando usa Secret Manager."""
        settings = Settings(
            project_name="test",
            db_host="localhost",
            db_user="user",
            db_password="pass",
            db_name="db",
            use_secret_manager=True,
            gcp_project_id="test-project",
            firebase_credentials_secret_name="test-secret",
        )
        
        assert settings.use_secret_manager is True
        assert settings.gcp_project_id == "test-project"
        assert settings.firebase_credentials_secret_name == "test-secret"

    def test_settings_secret_manager_sin_proyecto_falla(self):
        """Test que falla si usa Secret Manager sin gcp_project_id."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                project_name="test",
                db_host="localhost",
                db_user="user",
                db_password="pass",
                db_name="db",
                use_secret_manager=True,
                # Falta gcp_project_id
                firebase_credentials_secret_name="test-secret",
            )
        
        assert "gcp_project_id" in str(exc_info.value)

    def test_settings_secret_manager_sin_secret_name_falla(self):
        """Test que falla si usa Secret Manager sin secret_name."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                project_name="test",
                db_host="localhost",
                db_user="user",
                db_password="pass",
                db_name="db",
                use_secret_manager=True,
                gcp_project_id="test-project",
                # Falta firebase_credentials_secret_name
            )
        
        assert "firebase_credentials_secret_name" in str(exc_info.value)

    def test_settings_archivo_sin_path_falla(self):
        """Test que falla si no usa Secret Manager pero no proporciona path."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                project_name="test",
                db_host="localhost",
                db_user="user",
                db_password="pass",
                db_name="db",
                use_secret_manager=False,
                # Falta firebase_credentials_path
            )
        
        assert "firebase_credentials_path" in str(exc_info.value)

    def test_settings_archivo_inexistente_falla(self, tmp_path):
        """Test que falla si el archivo de credenciales no existe."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                project_name="test",
                db_host="localhost",
                db_user="user",
                db_password="pass",
                db_name="db",
                use_secret_manager=False,
                firebase_credentials_path=str(tmp_path / "no-existe.json"),
            )
        
        assert "no existe" in str(exc_info.value).lower()

    def test_database_url(self, tmp_path):
        """Test que database_url se genera correctamente."""
        cred_file = tmp_path / "test-creds.json"
        cred_file.write_text('{"type": "service_account"}')
        
        settings = Settings(
            project_name="test",
            db_host="localhost",
            db_port=5432,
            db_user="user",
            db_password="pass",
            db_name="db",
            use_secret_manager=False,
            firebase_credentials_path=str(cred_file),
        )
        
        url = settings.database_url
        assert "postgresql+asyncpg://" in url
        assert "user:pass@localhost:5432/db" in url

    def test_database_url_sync(self, tmp_path):
        """Test que database_url_sync se genera correctamente."""
        cred_file = tmp_path / "test-creds.json"
        cred_file.write_text('{"type": "service_account"}')
        
        settings = Settings(
            project_name="test",
            db_host="localhost",
            db_user="user",
            db_password="pass",
            db_name="db",
            use_secret_manager=False,
            firebase_credentials_path=str(cred_file),
        )
        
        url = settings.database_url_sync
        assert "postgresql://" in url
        assert "user:pass@localhost:5432/db" in url

    def test_default_values(self, tmp_path):
        """Test que los valores por defecto se aplican correctamente."""
        cred_file = tmp_path / "test-creds.json"
        cred_file.write_text('{"type": "service_account"}')
        
        settings = Settings(
            project_name="test",
            db_host="localhost",
            db_user="user",
            db_password="pass",
            db_name="db",
            use_secret_manager=False,
            firebase_credentials_path=str(cred_file),
        )
        
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.db_port == 5432
        assert settings.tenant_id_column_name == "tenant_id"
        assert settings.rls_setting_name == "app.current_tenant"
        assert settings.use_secret_manager is False
