"""Utilidades para interactuar con Google Cloud Secret Manager."""

import json
import logging
from typing import Any

from google.cloud import secretmanager
from google.api_core import exceptions as gcp_exceptions

from app.config import settings

logger = logging.getLogger(__name__)


def get_firebase_credentials_from_secret() -> dict[str, Any]:
    """
    Obtiene las credenciales de Firebase desde Google Cloud Secret Manager.

    Returns:
        dict: Credenciales de Firebase en formato JSON parseado.

    Raises:
        ValueError: Si no se puede acceder al secreto o está mal formateado.
        RuntimeError: Si hay un error al comunicarse con Secret Manager.
    """
    if not settings.use_secret_manager:
        raise ValueError(
            "use_secret_manager está deshabilitado. "
            "Usa firebase_credentials_path en su lugar."
        )

    if not settings.gcp_project_id:
        raise ValueError("gcp_project_id no está configurado")

    if not settings.firebase_credentials_secret_name:
        raise ValueError("firebase_credentials_secret_name no está configurado")

    try:
        # Crear cliente de Secret Manager
        client = secretmanager.SecretManagerServiceClient()

        # Construir el nombre del secreto
        secret_name = f"projects/{settings.gcp_project_id}/secrets/{settings.firebase_credentials_secret_name}/versions/latest"

        logger.info(f"Obteniendo credenciales desde Secret Manager: {secret_name}")

        # Obtener el secreto
        response = client.access_secret_version(request={"name": secret_name})

        # El secreto viene como bytes, decodificarlo
        secret_payload = response.payload.data.decode("UTF-8")

        # Parsear el JSON
        try:
            credentials = json.loads(secret_payload)
            logger.info("Credenciales obtenidas exitosamente desde Secret Manager")
            return credentials
        except json.JSONDecodeError as e:
            raise ValueError(
                f"El secreto no contiene un JSON válido: {str(e)}"
            ) from e

    except gcp_exceptions.PermissionDenied:
        logger.error(
            "Permiso denegado al acceder a Secret Manager. "
            "Verifica que la aplicación tenga el rol 'Secret Manager Secret Accessor'"
        )
        raise RuntimeError(
            "No se tienen permisos para acceder a Secret Manager. "
            "Verifica los permisos de la cuenta de servicio."
        )
    except gcp_exceptions.NotFound:
        logger.error(
            f"El secreto '{settings.firebase_credentials_secret_name}' no se encontró "
            f"en el proyecto '{settings.gcp_project_id}'"
        )
        raise ValueError(
            f"Secreto no encontrado: {settings.firebase_credentials_secret_name}"
        )
    except Exception as e:
        logger.error(f"Error al obtener credenciales desde Secret Manager: {str(e)}")
        raise RuntimeError(
            f"Error al comunicarse con Secret Manager: {str(e)}"
        ) from e
