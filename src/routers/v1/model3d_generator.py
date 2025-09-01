""" Router for Model3DGenerator """

from typing import Any

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from src.configs.logging import get_logger
from src.schemas.errors.model3d_generator import Model3DGeneratorError
from src.schemas.pydantic.model3d_generator import (
    Model3DGeneratorRequest,
    Model3DGeneratorResponse,
)
from src.services.model3d_generator import Model3DGeneratorService

Model3DGeneratorRouter = APIRouter(
    prefix="/v1/model3d", tags=["model3d"]
)

logger = get_logger(__name__)
_service = Model3DGeneratorService()

def _map_exception(exc: Exception) -> tuple[int, dict[str, Any]]:
    """
    Переводит исключения сервиса в понятные HTTP-коды и payload.
    """
    if isinstance(exc, Model3DGeneratorError):
        return (status.HTTP_502_BAD_GATEWAY, {"code": "provider_error", "message": str(exc)}) # noqa
    if isinstance(exc, TimeoutError):
        return (status.HTTP_504_GATEWAY_TIMEOUT, {"code": "timeout", "message": "Превышено время ожидания генерации"}) # noqa
    if isinstance(exc, ValueError):
        return (status.HTTP_400_BAD_REQUEST, {"code": "bad_request", "message": str(exc)}) # noqa
    return (status.HTTP_500_INTERNAL_SERVER_ERROR, {"code": "internal_error", "message": "Внутренняя ошибка сервера"}) # noqa

@Model3DGeneratorRouter.post(
    "/generate", 
    response_model=Model3DGeneratorResponse, 
    status_code=status.HTTP_200_OK
)
async def generate(request: Model3DGeneratorRequest) -> Model3DGeneratorResponse:
    """
    Генерирует 3D-модель на основе запроса.
    """
    logger.info(
        "Model3D generator request received",
        extra={
            "prompt_length": len(request.prompt),
            "model_format": getattr(request, "format", None),
            "quality": getattr(request, "quality", None),
        }
    )
    
    try:
        result = await _service.generate(request)
        logger.info(
            "Model3D generator request completed successfully",
            extra={"model_url": result.model_url}
        )
        return result
    except Exception as exc:
        logger.error(
            "Model3DGenerator generate failed",
            extra={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "prompt_length": len(request.prompt),
            },
            exc_info=True
        )
        code, payload = _map_exception(exc)
        raise HTTPException(status_code=code, detail=payload) from exc