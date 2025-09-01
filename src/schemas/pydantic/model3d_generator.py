""" Pydantic schemas for Model3DGenerator """
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Model3DGeneratorRequest(BaseModel):
    """
    Запрос на генерацию 3D-модели через Meshy Text-to-3D.
    """
    prompt: str = Field(..., description="Текстовое описание объекта")
    mode: Literal["lowpoly", "realistic"] = Field(
        "lowpoly", description="Профиль для параметров топологии/полигонажа"
    )
    # Дополнительно можно переопределить дефолты:
    art_style: Literal["realistic", "sculpture"] | None = Field(
        None, description="Стиль Meshy; если None — берётся из mode"
    )
    topology: Literal["triangle", "quad"] | None = Field(
        None, description="Тип топологии; если None — берётся из mode"
    )
    target_polycount: int | None = Field(
        None, ge=500, le=200000, description="Целевой полигонаж; если None — берётся из mode" # noqa
    )
    ai_model: Literal["meshy-5", "meshy-4"] = Field(
        "meshy-5", description="Модель Meshy (по умолчанию meshy-5)"
    )
    texture_prompt: str | None = Field(
        None, description="Подсказка для текстурирования (используется на refine)"
    )

    filename_prefix: str = Field(
        "model", description="Префикс имени файла при сохранении"
    )
    extension: str = Field(
        ".fbx", description="Желаемое расширение (.fbx|.glb|.obj|.usdz)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Низкополигональная модель деревянного стула без анимаций", # noqa
                    "mode": "lowpoly",
                    "filename_prefix": "chair_lp",
                    "extension": ".fbx"
                },
                {
                    "prompt": "Фотореалистичная модель глиняной вазы",
                    "mode": "realistic",
                    "art_style": "sculpture",
                    "texture_prompt": "Матовая керамика с тонкой трещиноватой глазурью",
                    "filename_prefix": "vase_rx",
                    "extension": ".glb"
                }
            ]
        }
    }


class Model3DGeneratorResponse(BaseModel):
    """
    Ответ: публичный URL на результат.
    """
    model_url: str = Field(..., description="URL скачивания файла модели")

    model_config = {
        "json_schema_extra": {
            "example": {"model_url": "file:///.../output/models/chair_lp.fbx"}
        }
    }
