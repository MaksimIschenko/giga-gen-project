"""Pydantic schemas for 3D Model Generator"""
from typing import Literal

from pydantic import BaseModel, Field


class Model3DGeneratorRequest(BaseModel):
    """
    - prompt — описание объекта (обяз.)
    - mode — "lowpoly" или "realistic" (управляет системным промптом)
    - fewshot — добавлять ли демонстрационный ответ ассистента
    - style — опциональный override system-промпта
    - filename_prefix — префикс имени файла
    - extension — расширение файла модели (по умолчанию .fbx)
    """
    prompt: str = Field(..., description="Описание 3D-модели")
    mode: Literal["lowpoly", "realistic"] = Field(
        "lowpoly", 
        description="Стиль генерации"
    )
    fewshot: bool = Field(True, description="Добавлять ли few-shot подсказку")
    style: str | None = Field(None, description="Полная замена system-промпта")
    filename_prefix: str = Field("model", description="Префикс имени файла")
    extension: str = Field(".fbx", description="Расширение файла модели")

    model_config = {
        "json_schema_extra": {
            "example": {
                "extension": ".fbx",
                "fewshot": True,
                "filename_prefix": "reward",
                "mode": "lowpoly",
                "prompt": "3D-модель кубка соревнований из золота."
            }
        }
    }


class Model3DGeneratorResponse(BaseModel):
    """- model_url — URL сгенерированного файла 3D-модели (FBX)."""
    model_url: str
