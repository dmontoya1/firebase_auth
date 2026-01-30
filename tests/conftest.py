"""Configuración compartida para tests."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import AsyncGenerator

import firebase_admin
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, AsyncSessionLocal
from app.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Configuración de prueba."""
    return Settings(
        project_name="test_project",
        environment="test",
        debug=True,
        db_host="localhost",
        db_port=5432,
        db_user="test_user",
        db_password="test_password",
        db_name="test_db",
        use_secret_manager=False,
        firebase_credentials_path="./tests/fixtures/test-service-account.json",
        tenant_id_column_name="tenant_id",
        rls_setting_name="app.current_tenant",
        allowed_origins=["*"],
    )


@pytest.fixture(scope="session")
def mock_firebase_credentials() -> dict:
    """Credenciales mock de Firebase para tests."""
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK_KEY\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


@pytest.fixture(scope="session")
def test_firebase_credentials_file(mock_firebase_credentials, tmp_path_factory):
    """Crea un archivo temporal con credenciales de prueba."""
    import json
    
    temp_file = tmp_path_factory.mktemp("fixtures") / "test-service-account.json"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_file, "w") as f:
        json.dump(mock_firebase_credentials, f)
    
    return str(temp_file)


@pytest.fixture
def mock_firebase_app():
    """Mock de la aplicación Firebase."""
    with patch("app.middleware.auth_middleware._firebase_app", None):
        with patch("firebase_admin.initialize_app") as mock_init:
            mock_app = Mock()
            mock_init.return_value = mock_app
            yield mock_app


@pytest.fixture
def mock_firebase_auth():
    """Mock del módulo auth de Firebase (parchear donde se usa en el middleware)."""
    with patch("app.middleware.auth_middleware.auth") as mock_auth:
        yield mock_auth


@pytest.fixture
def mock_secret_manager_client():
    """Mock del cliente de Secret Manager."""
    with patch("app.utils.secret_manager.secretmanager.SecretManagerServiceClient") as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def test_client(mock_firebase_app) -> TestClient:
    """Cliente de prueba para FastAPI."""
    return TestClient(app)


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Sesión de base de datos de prueba.
    
    Nota: En tests reales, deberías usar una base de datos de prueba.
    Para estos tests, usamos mocks.
    """
    # Crear motor de prueba en memoria (SQLite)
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Crear tablas
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Crear sesión de prueba
    TestSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with TestSessionLocal() as session:
        yield session
    
    await test_engine.dispose()


@pytest.fixture
def mock_decoded_token():
    """Token decodificado mock para tests."""
    return {
        "uid": "test-user-id",
        "email": "test@example.com",
        "firebase": {
            "tenant": "test-tenant-id"
        },
        "iat": 1234567890,
        "exp": 1234571490,
    }


@pytest.fixture
def sample_company_data():
    """Datos de ejemplo para una empresa."""
    return {
        "tenant_id": "test-tenant-id",
        "name": "Test Company",
        "display_name": "Test Company Display",
        "description": "A test company",
        "status": "active",
    }


@pytest.fixture
def sample_onboarding_request():
    """Request de ejemplo para onboarding."""
    return {
        "company_name": "New Company",
        "company_display_name": "New Company Display",
        "company_description": "A new company",
        "admin_user": {
            "email": "admin@newcompany.com",
            "password": "SecurePassword123!",
            "display_name": "Admin User"
        }
    }
