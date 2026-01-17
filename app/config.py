"""Configuración del microservicio usando pydantic-settings."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Información del proyecto
    project_name: str = Field(..., description="Nombre del proyecto actual")
    environment: str = Field(default="development", description="Entorno de ejecución")
    debug: bool = Field(default=False, description="Modo debug")

    # Configuración de base de datos PostgreSQL
    db_host: str = Field(..., description="Host de PostgreSQL")
    db_port: int = Field(default=5432, description="Puerto de PostgreSQL")
    db_user: str = Field(..., description="Usuario de PostgreSQL")
    db_password: str = Field(..., description="Contraseña de PostgreSQL")
    db_name: str = Field(..., description="Nombre de la base de datos")
    db_pool_size: int = Field(default=10, description="Tamaño del pool de conexiones")
    db_max_overflow: int = Field(default=20, description="Overflow máximo del pool")

    # Configuración de Firebase/Identity Platform
    # Opción 1: Usar Google Cloud Secret Manager (recomendado para producción)
    use_secret_manager: bool = Field(
        default=True, description="Usar Secret Manager en lugar de archivo JSON"
    )
    gcp_project_id: str | None = Field(
        None, description="ID del proyecto de Google Cloud"
    )
    firebase_credentials_secret_name: str | None = Field(
        None, description="Nombre del secreto en Secret Manager con las credenciales JSON"
    )
    
    # Opción 2: Usar archivo JSON local (para desarrollo)
    firebase_credentials_path: str | None = Field(
        None, description="Ruta al archivo JSON de credenciales de Firebase (solo si use_secret_manager=False)"
    )

    # Configuración Multi-tenant
    tenant_id_column_name: str = Field(
        default="tenant_id", description="Nombre de la columna discriminadora de tenant"
    )
    rls_setting_name: str = Field(
        default="app.current_tenant",
        description="Nombre de la variable de sesión para RLS",
    )

    # Configuración de seguridad
    allowed_origins: list[str] = Field(
        default=["*"], description="Orígenes permitidos para CORS"
    )

    @field_validator("firebase_credentials_path")
    @classmethod
    def validate_firebase_credentials_path(cls, v: str | None) -> str | None:
        """Valida que el archivo de credenciales exista si se proporciona."""
        if v is None:
            return None
        credentials_path = Path(v)
        if not credentials_path.exists():
            raise ValueError(f"El archivo de credenciales no existe: {v}")
        if not credentials_path.is_file():
            raise ValueError(f"La ruta no es un archivo: {v}")
        return str(credentials_path.absolute())

    def model_post_init(self, __context) -> None:
        """Valida la configuración de credenciales después de la inicialización."""
        if self.use_secret_manager:
            if not self.gcp_project_id:
                raise ValueError(
                    "gcp_project_id es requerido cuando use_secret_manager=True"
                )
            if not self.firebase_credentials_secret_name:
                raise ValueError(
                    "firebase_credentials_secret_name es requerido cuando use_secret_manager=True"
                )
        else:
            if not self.firebase_credentials_path:
                raise ValueError(
                    "firebase_credentials_path es requerido cuando use_secret_manager=False"
                )

    @property
    def database_url(self) -> str:
        """Genera la URL de conexión a la base de datos."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Genera la URL de conexión síncrona (para Alembic)."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


# Instancia global de configuración
settings = Settings()
