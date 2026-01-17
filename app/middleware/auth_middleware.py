"""Middleware de autenticación con Firebase Identity Platform."""

import json
import logging
from pathlib import Path
from typing import Callable

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings
from app.utils.secret_manager import get_firebase_credentials_from_secret

logger = logging.getLogger(__name__)

# Inicializar Firebase Admin SDK (solo una vez)
_firebase_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
    """
    Obtiene o inicializa la instancia de Firebase Admin SDK.

    Obtiene las credenciales desde:
    - Google Cloud Secret Manager (si use_secret_manager=True)
    - Archivo JSON local (si use_secret_manager=False)

    Returns:
        firebase_admin.App: Instancia de la aplicación Firebase.

    Raises:
        ValueError: Si la configuración de credenciales es inválida.
        RuntimeError: Si hay un error al obtener las credenciales.
    """
    global _firebase_app
    if _firebase_app is None:
        try:
            if settings.use_secret_manager:
                # Obtener credenciales desde Secret Manager
                logger.info("Obteniendo credenciales desde Google Cloud Secret Manager")
                credentials_dict = get_firebase_credentials_from_secret()
                cred = credentials.Certificate(credentials_dict)
            else:
                # Usar archivo JSON local
                logger.info(f"Usando credenciales desde archivo: {settings.firebase_credentials_path}")
                if not settings.firebase_credentials_path:
                    raise ValueError(
                        "firebase_credentials_path no está configurado. "
                        "Configura use_secret_manager=True o proporciona firebase_credentials_path"
                    )
                cred = credentials.Certificate(settings.firebase_credentials_path)

            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Firebase Admin SDK: {str(e)}", exc_info=True)
            raise RuntimeError(
                f"Error al inicializar Firebase Admin SDK: {str(e)}"
            ) from e

    return _firebase_app


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que intercepta todas las peticiones para autenticación.

    Excepciones:
    - /health: Endpoint de health check
    - /public/*: Rutas públicas
    - /docs, /openapi.json: Documentación de FastAPI
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        Inicializa el middleware.

        Args:
            app: Aplicación ASGI.
        """
        super().__init__(app)
        # Inicializar Firebase al crear el middleware
        get_firebase_app()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """
        Procesa cada request para verificar autenticación.

        Args:
            request: Request HTTP.
            call_next: Función para continuar con el siguiente middleware.

        Returns:
            Response: Respuesta HTTP.
        """
        # Rutas que no requieren autenticación
        excluded_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/onboarding",
        ]
        if request.url.path.startswith("/public"):
            excluded_paths.append(request.url.path)

        if any(request.url.path.startswith(path) for path in excluded_paths):
            return await call_next(request)

        # Extraer token del header Authorization
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token de autenticación no proporcionado"},
            )

        # Validar formato del header
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Formato de token inválido. Use: Bearer <token>"},
            )

        token = parts[1]

        try:
            # Verificar token con Firebase Admin SDK
            decoded_token = auth.verify_id_token(token)

            # Extraer tenant_id del token
            # En Google Cloud Identity Platform, el tenant_id está en firebase.tenant
            tenant_id = decoded_token.get("firebase", {}).get("tenant")
            if not tenant_id:
                logger.warning(
                    "Token válido pero sin tenant_id. "
                    "Asegúrate de que el usuario pertenezca a un tenant."
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Token no asociado a un tenant"},
                )

            # Inyectar tenant_id en el contexto de la request
            request.state.tenant_id = tenant_id
            request.state.user_id = decoded_token.get("uid")
            request.state.user_email = decoded_token.get("email")
            request.state.decoded_token = decoded_token

            logger.debug(
                f"Usuario autenticado: {request.state.user_email} "
                f"(tenant: {tenant_id})"
            )

        except auth.InvalidIdTokenError as e:
            logger.warning(f"Token inválido: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token de autenticación inválido"},
            )
        except auth.ExpiredIdTokenError:
            logger.warning("Token expirado")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token de autenticación expirado"},
            )
        except Exception as e:
            logger.error(f"Error al verificar token: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Error interno al verificar autenticación"},
            )

        # Continuar con la request
        return await call_next(request)
