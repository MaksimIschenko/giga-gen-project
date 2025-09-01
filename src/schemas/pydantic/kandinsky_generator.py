""" Pydantic schemas for Kandinsky Generator """
from pydantic import BaseModel, Field


class KandinskyGeneratorRequest(BaseModel):
    """
    Запрос генерации изображения через Kandinsky/FusionBrain.

    - prompt — текстовое описание картинки (обязательно).
    - images — количество изображений, которые нужно сгенерировать.
    - width/height — размеры изображения (по умолчанию 1024x1024).
    - style — опционально: название стиля (например, "ANIME", "CINEMATIC").
    - negative_prompt — опционально: описание нежелательных деталей.
    - file_basename — базовое имя файла при сохранении.
    - extension — расширение изображения (.jpg, .png).
    """
    prompt: str = Field(..., description="Описание картинки для генерации")
    images: int = Field(1, ge=1, le=10, description="Количество изображений")
    width: int = Field(1024, description="Ширина изображения в пикселях")
    height: int = Field(1024, description="Высота изображения в пикселях")
    style: str | None = Field(None, description="Стиль (например, ANIME, CINEMATIC)")
    negative_prompt: str | None = Field(None, description="Нежелательные детали")
    file_basename: str = Field("kandinsky", description="Базовое имя файла при сохранении") # noqa
    extension: str = Field(".jpg", description="Расширение выходного файла")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Реалистичное изображение сноубордиста фристайл в прыжке, яркое солнце", # noqa
                "images": 1,
                "width": 1024,
                "height": 1024,
                "style": "CINEMATIC",
                "negative_prompt": "Размытый фон, низкое качество",
                "file_basename": "snowboarder_freestyle",
                "extension": ".jpg",
            }
        }
    }


class KandinskyGeneratorResponse(BaseModel):
    """
    Ответ генератора через Kandinsky.
    - image_urls — список URL к сгенерированным изображениям.
    """
    image_urls: list[str] = Field(..., description="Список URL сгенерированных изображений") # noqa

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_urls": [
                    "https://example.com/images_out/snowboarder_freestyle-1.jpg"
                ]
            }
        }
    }
