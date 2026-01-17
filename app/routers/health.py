"""Router para health checks."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, str]:
    """
    Endpoint de health check.

    Returns:
        dict: Estado del servicio.
    """
    return {"status": "healthy", "service": "auth-service"}
