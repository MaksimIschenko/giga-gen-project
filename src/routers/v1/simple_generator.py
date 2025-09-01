""" Router for Simple Generator """
from typing import Any

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from src.schemas.errors.simple_generator import SimpleGeneratorError
from src.schemas.pydantic.simple_generator import (
    SimpleGeneratorRequest,
    SimpleGeneratorResponse,
)
from src.services.simple_generator import SimpleGeneratorService

SimpleGeneratorRouter = APIRouter(
    prefix="/v1/simple", tags=["simple"]
)

_service = SimpleGeneratorService()

def _map_exception(exc: Exception) -> tuple[int, dict[str, Any]]:
    """
    Переводит исключения сервиса в понятные HTTP-коды и payload.
    """
    # Пустой/некорректный prompt, неправильные параметры и пр. — это, по сути, 422/400
    if isinstance(exc, ValueError):
        return (
            status.HTTP_400_BAD_REQUEST, 
            {"code": "bad_request", "message": str(exc)}
        )
    if isinstance(exc, SimpleGeneratorError):
        # По умолчанию считаем, что это ошибка взаимодействия с провайдером — 502
        # (можно вернуть 424 Failed Dependency, 
        # но 502 понятнее «внешний сервис сломался») 
        return (
            status.HTTP_502_BAD_GATEWAY, 
            {"code": "provider_error", "message": str(exc)}
        )
    if isinstance(exc, TimeoutError):
        return (
            status.HTTP_504_GATEWAY_TIMEOUT, 
            {"code": "timeout", "message": "Превышено время ожидания генерации"}
        )
    # На всё прочее — 500
    return (
        status.HTTP_500_INTERNAL_SERVER_ERROR, 
        {"code": "internal_error", "message": "Внутренняя ошибка сервера"}
    )


@SimpleGeneratorRouter.post(
    "/generate", 
    response_model=SimpleGeneratorResponse, 
    status_code=status.HTTP_200_OK
)
async def generate(request: SimpleGeneratorRequest) -> SimpleGeneratorResponse:
    """
    Генерирует простое изображение (логотип, иконку) на основе запроса.
    """
    try:
        result = await _service.generate(request)
        return result
    except Exception as exc:
        # Логируем с контекстом запроса (без чувствительных данных)
        print("SimpleGenerator generate failed: %s", exc)
        http_code, payload = _map_exception(exc)
        raise HTTPException(status_code=http_code, detail=payload) from exc
    