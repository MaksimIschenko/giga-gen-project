""" Router for Kandinsky Generator """
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from src.schemas.pydantic.kandinsky_generator import (
    KandinskyGeneratorRequest,
    KandinskyGeneratorResponse,
)
from src.services.kandinsky_generator import (
    KandinskyGeneratorError,
    KandinskyGeneratorService,
)

KandinskyGeneratorRouter = APIRouter(prefix="/v1/kandinsky", tags=["kandinsky"])
_service = KandinskyGeneratorService()


def _map_exception(exc: Exception) -> tuple[int, dict[str, Any]]:
    if isinstance(exc, KandinskyGeneratorError):
        return (status.HTTP_502_BAD_GATEWAY, {"code": "provider_error", "message": str(exc)}) # noqa
    if isinstance(exc, TimeoutError):
        return (status.HTTP_504_GATEWAY_TIMEOUT, {"code": "timeout", "message": "Превышено время ожидания генерации"}) # noqa
    if isinstance(exc, ValueError):
        return (status.HTTP_400_BAD_REQUEST, {"code": "bad_request", "message": str(exc)}) # noqa
    return (status.HTTP_500_INTERNAL_SERVER_ERROR, {"code": "internal_error", "message": "Внутренняя ошибка сервера"}) # noqa


@KandinskyGeneratorRouter.post(
    "/generate",
    response_model=KandinskyGeneratorResponse,
    status_code=status.HTTP_200_OK,
)
async def generate(request: KandinskyGeneratorRequest) -> KandinskyGeneratorResponse:
    """
    Генерация «сложных/красочных» изображений (Kandinsky/FusionBrain).
    """
    try:
        result = await _service.generate(request)
        return result
    except Exception as exc:
        print("Kandinsky generate failed: %s", exc)
        code, payload = _map_exception(exc)
        raise HTTPException(status_code=code, detail=payload) from exc
