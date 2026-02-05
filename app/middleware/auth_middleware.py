"""Middleware de autenticación con Firebase Identity Platform."""

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

import jwt
import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.auth import ExpiredIdTokenError, InvalidIdTokenError
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings
from app.utils.secret_manager import get_firebase_credentials_from_secret

logger = logging.getLogger(__name__)

# Issuer de tokens devueltos por Identity Platform REST API (signInWithPassword)
IDENTITY_TOOLKIT_ISSUERS = ("https://identitytoolkit.google.com/", "https://identitytoolkit.google.com")
# Claves públicas de Identity Platform (session cookie / ID token signer)
IDENTITY_PLATFORM_JWKS_URL = "https://identitytoolkit.googleapis.com/v1/sessionCookiePublicKeys"
# URL de certificados públicos (Firebase)
FIREBASE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
# Tokeninfo para validar token (solo para tokens OAuth de Google, no Identity Toolkit)
TOKENINFO_URL = "https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={token}"

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


def _verify_identity_toolkit_token(token: str, project_id: str) -> dict | None:
    """
    Verifica un ID token con issuer Identity Toolkit (REST API signInWithPassword).

    Los tokens devueltos por identitytoolkit.googleapis.com/v1/accounts:signInWithPassword
    tienen issuer https://identitytoolkit.google.com/ y el Firebase Admin SDK
    verify_id_token() solo acepta https://securetoken.google.com/{project_id}.
    Intenta: (1) JWKS de Identity Platform, (2) certs Firebase, (3) tokeninfo.

    Returns:
        Payload del token si es válido, None si no.
    """
    # 1) Claves públicas de Identity Platform (sessionCookiePublicKeys)
    try:
        jwks_client = jwt.PyJWKClient(IDENTITY_PLATFORM_JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        for iss in IDENTITY_TOOLKIT_ISSUERS:
            try:
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=project_id,
                    issuer=iss,
                    options={"verify_exp": True},
                )
                return payload
            except jwt.InvalidIssuerError:
                continue
    except Exception as e:
        logger.warning(
            "Fallback Identity Toolkit (JWKS) failed: %s", e, exc_info=False
        )

    # 2) Verificación JWT con certificados Firebase (probar con kid y con todos los certs)
    try:
        req = urllib.request.Request(FIREBASE_CERTS_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            certs = json.loads(resp.read().decode())
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        cert_list = [certs[kid]] if kid and kid in certs else list(certs.values())
        for cert in cert_list:
            for iss in IDENTITY_TOOLKIT_ISSUERS:
                try:
                    payload = jwt.decode(
                        token,
                        cert,
                        algorithms=["RS256"],
                        audience=project_id,
                        issuer=iss,
                        options={"verify_exp": True},
                    )
                    return payload
                except (jwt.InvalidIssuerError, jwt.InvalidAudienceError, jwt.ExpiredSignatureError):
                    continue
                except jwt.PyJWTError:
                    break
    except Exception as e:
        logger.warning(
            "Fallback Identity Toolkit (JWT certs) failed: %s", e, exc_info=False
        )

    # 3) Fallback: tokeninfo de Google (solo tokens OAuth; Identity Toolkit suele devolver 400)
    try:
        url = TOKENINFO_URL.format(token=urllib.parse.quote(token, safe=""))
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("aud") != project_id:
            logger.warning("Tokeninfo aud %s != project_id %s", data.get("aud"), project_id)
            return None
        # Normalizar a formato esperado por el middleware (uid, firebase.tenant, email)
        payload = {
            "uid": data.get("user_id") or data.get("sub"),
            "email": data.get("email"),
            "firebase": {"tenant": data.get("tenant")},
            "tenant": data.get("tenant"),
        }
        if payload.get("uid") and (payload.get("firebase", {}).get("tenant") or payload.get("tenant")):
            return payload
    except urllib.error.HTTPError as e:
        logger.warning("Tokeninfo endpoint error: %s %s", e.code, e.reason)
    except Exception as e:
        logger.warning("Fallback Identity Toolkit (tokeninfo) failed: %s", e, exc_info=False)
    return None


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
            # Verificar token con Firebase Admin SDK (issuer securetoken.google.com)
            decoded_token = auth.verify_id_token(token)
        except InvalidIdTokenError as e:
            err_msg = str(e).lower()
            # Tokens de Identity Platform REST API tienen issuer identitytoolkit.google.com
            if "iss" in err_msg and "identitytoolkit" in err_msg:
                app = get_firebase_app()
                project_id = getattr(app, "project_id", None)
                if project_id:
                    decoded_token = _verify_identity_toolkit_token(token, project_id)
                    if decoded_token:
                        # Normalizar: algunos tokens usan user_id en lugar de uid
                        if "uid" not in decoded_token and "user_id" in decoded_token:
                            decoded_token["uid"] = decoded_token["user_id"]
                    else:
                        decoded_token = None
                else:
                    decoded_token = None
            else:
                decoded_token = None
            if decoded_token is None:
                logger.warning(f"Token inválido: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token de autenticación inválido"},
                )
        except ExpiredIdTokenError:
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

        # Extraer tenant_id del token
        # En Google Cloud Identity Platform, el tenant_id está en firebase.tenant o "tenant"
        tenant_id = (
            decoded_token.get("firebase", {}).get("tenant")
            or decoded_token.get("tenant")
        )
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

        # Continuar con la request
        return await call_next(request)
