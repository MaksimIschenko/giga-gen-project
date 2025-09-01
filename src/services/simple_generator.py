""" Сервис «простых» изображений (логотипы, простая графика) через GigaChat. """

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

from bs4 import BeautifulSoup
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from src.configs.environment import get_environment_settings
from src.schemas.errors.simple_generator import SimpleGeneratorError
from src.schemas.pydantic.simple_generator import (
    SimpleGeneratorRequest,
    SimpleGeneratorResponse,
)


class SimpleGeneratorService:
    """
    Сервис «простых» изображений (логотипы, простая графика) через GigaChat.
    - Инициализирует singleton-клиент GigaChat
    - Делает chat-completions с function_call="auto" (вызов text2image)
    - Достаёт <img src="..."> с file_id, скачивает картинку и сохраняет её
    - Возвращает image_url в SimpleGeneratorResponse
    """

    ICON_SYSTEM_PROMPT = (
        "Ты — дизайнер пиктограмм. Всегда создавай простые монохромные или двухцветные иконки " # noqa
        "на белом фоне, без теней и градиентов, плоский векторный стиль, высокая контрастность, " # noqa
        "одна ключевая форма, толстые чёткие линии. Без текста и водяных знаков."
    )
    LOGO_SYSTEM_PROMPT = (
        "Ты — дизайнер логотипов в минималистичном стиле. Создавай лаконичные знаки на белом фоне, " # noqa
        "без теней/градиентов/фото, 1–2 цвета, плоская геометрия, чистые контуры, читабельность в малом размере. " # noqa
        "Без текста, если не указан явно."
    )

    def __init__(self) -> None:
        self.environment_settings = get_environment_settings()

        self._images_dir = Path(
            self.environment_settings.IMAGES_OUT_DIR 
            or "images_out"
        )
        self._images_dir.mkdir(parents=True, exist_ok=True)

        self._public_base_url: str | None = getattr(
            self.environment_settings, "PUBLIC_BASE_URL", None
        )

        self._giga = GigaChat(
            credentials=self.environment_settings.GIGACHAT_AUTH_KEY,
            scope=self.environment_settings.GIGACHAT_SCOPE,
            verify_ssl_certs=bool(self.environment_settings.GIGACHAT_VERIFY_SSL),
        )

        # рабочие поля (устанавливаются в generate)
        self._current_mode: str = "icon"
        self._current_fewshot: bool = True

    # --------------- Публичный API ---------------

    async def generate(self, req: SimpleGeneratorRequest) -> SimpleGeneratorResponse:
        """
        Главная точка входа: принимает Pydantic-запрос, возвращает Pydantic-ответ.
        """
        # режим и few-shot берём из запроса, если есть
        self._current_mode = (getattr(req, "mode", "icon") or "icon").lower().strip()
        self._current_fewshot = bool(getattr(req, "fewshot", True))

        file_path = await self._generate_image(
            prompt=req.prompt,
            style_system_prompt=getattr(req, "style", None), 
            filename_prefix=getattr(req, "filename_prefix", "gen"),
            extension=getattr(req, "extension", ".jpg"),
            fewshot=self._current_fewshot,
        )
        image_url = self._to_public_url(file_path)
        return SimpleGeneratorResponse(image_url=image_url)
    
    
    # --------------- Внутренние методы ---------------

    def _build_messages(
        self,
        user_prompt: str,
        mode: str = "icon",
        override_system: str | None = None,
        fewshot: bool = True,
    ) -> list[Messages]:
        """
        Собираем массив messages с ролями system/user 
        (+необязательный few-shot assistant).
        """
        system_content = override_system or (
            self.LOGO_SYSTEM_PROMPT if mode == "logo" else self.ICON_SYSTEM_PROMPT
        )

        msgs = [
            Messages(role=MessagesRole.SYSTEM, content=system_content),
        ]

        if fewshot:
            # Текстовый patterн-ответ ассистента, усиливающий минималистичный стиль
            msgs.append(
                Messages(
                    role=MessagesRole.ASSISTANT,
                    content=(
                        "Готовлю плоскую, контрастную, "
                        "безградиентную иконку на белом фоне "
                        "с одной доминантной формой."
                    ),
                )
            )

        msgs.append(Messages(role=MessagesRole.USER, content=user_prompt))
        return msgs

    async def _generate_image(
        self,
        prompt: str,
        style_system_prompt: str | None = None,
        out_dir: str | Path | None = None,
        filename_prefix: str = "gen",
        extension: str = ".jpg",
        fewshot: bool = True,
    ) -> Path:
        """
        Генерирует изображение и сохраняет его в images_out (или указанный out_dir).
        Возвращает абсолютный Path к файлу.
        """
        if not prompt or not prompt.strip():
            raise SimpleGeneratorError("Пустой prompt.")

        # нормализуем расширение
        if not extension.startswith("."):
            extension = "." + extension
        if not mimetypes.guess_type(f"file{extension}")[0]:
            extension = ".jpg"

        out_root = Path(out_dir) if out_dir else self._images_dir
        out_root.mkdir(parents=True, exist_ok=True)

        # Сборка сообщений с учётом выбранного режима и (опционально) override_system
        messages = self._build_messages(
            user_prompt=prompt,
            mode=getattr(self, "_current_mode", "icon"),
            override_system=style_system_prompt,
            fewshot=fewshot,
        )

        payload = Chat(messages=messages, function_call="auto")  # позволяем text2image
        try:
            resp = self._giga.chat(payload)
        except Exception as e:
            raise SimpleGeneratorError(f"GigaChat chat() failed: {e}") from e

        html = (resp.choices[0].message.content or "").strip()
        file_id = self._extract_file_id_from_html(html)
        if not file_id:
            raise SimpleGeneratorError(
                f"Модель не вернула <img/> с file_id. Ответ: {html!r}"
            )

        try:
            image_obj = self._giga.get_image(file_id)  # содержит base64 контент
        except Exception as e:
            raise SimpleGeneratorError(
                f"GigaChat get_image({file_id}) failed: {e}"
            ) from e

        # безопасное имя файла
        safe_prefix = self._slugify(filename_prefix) or "gen"
        filename = f"{safe_prefix}-{file_id}{extension}"
        file_path = out_root / filename

        try:
            file_path.write_bytes(base64.b64decode(image_obj.content))
        except Exception as e:
            raise SimpleGeneratorError(
                f"Не удалось записать файл {file_path}: {e}"
            ) from e

        return file_path.resolve()

    @staticmethod
    def _extract_file_id_from_html(html: str) -> str | None:
        """
        Ищет <img src="..."> и возвращает значение src (file_id).
        """
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img")
        return img.get("src") if img and img.get("src") else None

    def _to_public_url(self, file_path: Path) -> str:
        """
        Если задан PUBLIC_BASE_URL — собирает https://.../<relpath>,
        иначе возвращает file:/// абсолютный путь.
        """
        if self._public_base_url:
            # вычислим относительный путь от каталога проекта
            try:
                rel = file_path.relative_to(Path.cwd())
            except ValueError:
                rel = file_path.name
            return f"{self._public_base_url.rstrip('/')}/{rel.as_posix()}"
        return file_path.resolve().as_uri()

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"[^\w\-\.]+", "-", text, flags=re.U)
        text = re.sub(r"-{2,}", "-", text).strip("-")
        return text
