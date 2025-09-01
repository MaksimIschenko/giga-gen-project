from pydantic import BaseModel, Field
from typing import Literal, Optional

class SimpleGeneratorRequest(BaseModel):
    """
    - prompt — текстовое описание картинки (обязательно).
    - mode — "icon" или "logo" (управляет выбором системного промпта).
    - fewshot — true/false, добавлять ли демонстрационный ответ ассистента для стабилизации стиля.
    - style — опционально: если хотите полностью заменить системный промпт своим.
    - filename_prefix — префикс имени файла (например, "settings").
    - extension — расширение файла (.jpg, .png и т.д., по умолчанию .jpg).
    """
    prompt: str = Field(..., description="Описание картинки")
    mode: Literal["icon", "logo"] = Field("icon", description="Режим генерации")
    fewshot: bool = Field(True, description="Добавлять ли few-shot подсказку")
    style: Optional[str] = Field(None, description="Опциональный system-промпт")
    filename_prefix: str = Field("gen", description="Префикс имени файла")
    extension: str = Field(".jpg", description="Расширение изображения")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Простой логотип для компании, которая делает программное обеспечение для малых бизнесов",
                "mode": "logo",
                "fewshot": True,
                "style": "Минималистичный стиль, плоская геометрия, белый фон",
                "filename_prefix": "company_logo",
                "extension": ".png",
            }
        }
    }

class SimpleGeneratorResponse(BaseModel):
    """
    - image_url — URL изображения.
    """
    image_url: str