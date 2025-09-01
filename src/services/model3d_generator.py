""" Router for Model3DGenerator """
from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

from bs4 import BeautifulSoup
from gigachat import GigaChat
from gigachat.models import Chat, Function, Messages, MessagesRole

from src.configs.environment import get_environment_settings
from src.configs.logging import get_logger
from src.schemas.pydantic.model3d_generator import (
    Model3DGeneratorRequest,
    Model3DGeneratorResponse,
)


class Model3DGeneratorService:
    """
    Генерация 3D-моделей (FBX) через GigaChat text2model3d.
    - Строит системный промпт (lowpoly/realistic или вручную через style)
    - Делает chat-completions c function_call="auto" и functions=[text2model3d]
    - Извлекает <div data-model-id="..."/> из ответа
    - Скачивает файл через SDK (base64) и сохраняет его
    - Возвращает публичный URL файла
    """

    LOWPOLY_SYSTEM_PROMPT = (
        "Ты — 3D-художник для real-time. Генерируй низкополигональные модели, "
        "оптимизированные для игр: <= 10k трис, аккуратный силуэт, один объект без анимаций, " # noqa
        "PBR-материалы допускаются, UV-развёртка без перекрытий. Масштаб 1.0, ось Z вверх, " # noqa
        "центр модели в (0,0,0). Без лишних подпорок и сцены, только целевой объект."
    )

    REALISTIC_SYSTEM_PROMPT = (
        "Ты — 3D-художник PBR. Генерируй фотореалистичные модели с чистой топологией, "
        "корректной UV-развёрткой, нейтральными материалами. Масштаб 1.0, ось Z вверх, " # noqa
        "центр модели в (0,0,0). Только целевой объект, без окружения и анимаций."
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.environment_settings = get_environment_settings()

        # куда сохранять
        out_dir = getattr(self.environment_settings, "MODELS_OUT_DIR", None) or "models_out" # noqa
        self._models_dir = Path(out_dir)
        self._models_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Models directory set to: {self._models_dir}")

        # публичный базовый URL (для сборки ссылок)
        self._public_base_url: str | None = getattr(
            self.environment_settings, "PUBLIC_BASE_URL", None
        )

        # В 3D-доках рекомендуют увеличить timeout, т.к. генерация долгая
        self._giga = GigaChat(
            credentials=self.environment_settings.GIGACHAT_AUTH_KEY,
            scope=getattr(self.environment_settings, "GIGACHAT_SCOPE", None),
            verify_ssl_certs=bool(getattr(
                self.environment_settings, 
                "GIGACHAT_VERIFY_SSL", 
                True)
            ),
            timeout=int(getattr(self.environment_settings, "GIGACHAT_TIMEOUT", 200)),
        )

        # рабочие поля
        self._current_mode: str = "lowpoly"
        self._current_fewshot: bool = True

    # --------------- Публичный API ---------------

    async def generate(self, req: Model3DGeneratorRequest) -> Model3DGeneratorResponse:
        """
        Принимает Pydantic-запрос, возвращает Pydantic-ответ.
        """
        self._current_mode = (getattr(req, "mode", "lowpoly") or "lowpoly").lower().strip() # noqa
        self._current_fewshot = bool(getattr(req, "fewshot", True))

        file_path = await self._generate_model(
            prompt=req.prompt,
            style_system_prompt=getattr(req, "style", None),
            filename_prefix=getattr(req, "filename_prefix", "model"),
            extension=getattr(req, "extension", ".fbx"),
            fewshot=self._current_fewshot,
        )
        model_url = self._to_public_url(file_path)
        return Model3DGeneratorResponse(model_url=model_url)

    # --------------- Внутренние методы ---------------

    def _build_messages(
        self,
        user_prompt: str,
        mode: str = "lowpoly",
        override_system: str | None = None,
        fewshot: bool = True,
    ) -> list[Messages]:
        """Собираем messages: system/user (+ опц. few-shot assistant)."""
        system_content = override_system or (
            self.REALISTIC_SYSTEM_PROMPT if mode == "realistic" else self.LOWPOLY_SYSTEM_PROMPT # noqa
        )

        msgs = [Messages(role=MessagesRole.SYSTEM, content=system_content)]

        if fewshot:
            # короткий стабилизатор стиля
            msgs.append(
                Messages(
                    role=MessagesRole.ASSISTANT,
                    content="Готовлю чистую, корректно масштабированную 3D-модель целевого объекта.", # noqa
                )
            )

        msgs.append(Messages(role=MessagesRole.USER, content=user_prompt))
        return msgs

    async def _generate_model(
        self,
        *,
        prompt: str,
        style_system_prompt: str | None = None,
        out_dir: str | Path | None = None,
        filename_prefix: str = "model",
        extension: str = ".fbx",
        fewshot: bool = True,
    ) -> Path:
        """Генерирует 3D-модель и сохраняет её. Возвращает абсолютный Path."""
        if not prompt or not prompt.strip():
            raise ValueError("Пустой prompt.")

        # нормализуем расширение (рекомендуемый формат FBX согласно докам)
        if not extension.startswith("."):
            extension = "." + extension
        # если расширение совсем экзотика — принудительно .fbx
        if mimetypes.guess_type(f"file{extension}")[0] is None:
            extension = ".fbx"

        out_root = Path(out_dir) if out_dir else self._models_dir
        out_root.mkdir(parents=True, exist_ok=True)

        # сообщения
        messages = self._build_messages(
            user_prompt=prompt,
            mode=getattr(self, "_current_mode", "lowpoly"),
            override_system=style_system_prompt,
            fewshot=fewshot,
        )

        # обязательно передаём встроенную функцию text2model3d
        payload = Chat(
            messages=messages,
            function_call="auto",
            functions=[Function(name="text2model3d")],
        )

        try:
            resp = self._giga.chat(payload)
        except Exception as e:
            raise RuntimeError(f"GigaChat chat() failed: {e}") from e

        html = (resp.choices[0].message.content or "").strip()
        model_id = self._extract_model_id_from_html(html)
        if not model_id:
            raise RuntimeError(f"Модель не вернула <div data-model-id=.../>. Ответ: {html!r}") # noqa

        # В доках указано, что get_image() подходит и для 3D (возвращает base64)
        try:
            model_obj = self._giga.get_image(model_id)
        except Exception as e:
            raise RuntimeError(f"GigaChat get_image({model_id}) failed: {e}") from e

        safe_prefix = self._slugify(filename_prefix) or "model"
        filename = f"{safe_prefix}-{model_id}{extension}"
        file_path = out_root / filename

        try:
            file_path.write_bytes(base64.b64decode(model_obj.content))
        except Exception as e:
            raise RuntimeError(f"Не удалось записать файл {file_path}: {e}") from e

        return file_path.resolve()

    @staticmethod
    def _extract_model_id_from_html(html: str) -> str | None:
        """
        Ожидаем тег: <div data-model-id="..."/>  (см. оф. доки)
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        return div.get("data-model-id") if div and div.get("data-model-id") else None

    def _to_public_url(self, file_path: Path) -> str:
        """PUBLIC_BASE_URL => https://.../<relpath>, иначе file:///abs/path"""
        if self._public_base_url:
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
