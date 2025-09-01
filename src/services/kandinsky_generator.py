""" Сервис генерации «сложных/красочных» изображений через FusionBrain (Kandinsky). """
from __future__ import annotations

import base64
from functools import partial
from pathlib import Path

import anyio
from fusionbrain_sdk_python import FBClient, PipelineType

from src.configs.environment import get_environment_settings
from src.configs.logging import get_logger
from src.schemas.errors.kandinsky_generator import KandinskyGeneratorError
from src.schemas.pydantic.kandinsky_generator import (
    KandinskyGeneratorRequest,
    KandinskyGeneratorResponse,
)


class KandinskyGeneratorService:
    """
    Сервис генерации «сложных/красочных» изображений через FusionBrain (Kandinsky).
    - Инициализация SDK-клиента
    - Поиск пайплайна TEXT2IMAGE
    - Запуск генерации и ожидание результата
    - Сохранение в images_out (или указанный каталог)
    - Сборка публичных URLов
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        env = get_environment_settings()
        self._images_dir = Path(getattr(env, "IMAGES_OUT_DIR", "images_out"))
        self._images_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Images directory set to: {self._images_dir}")
        
        self._public_base_url: str | None = getattr(env, "PUBLIC_BASE_URL", None)

        # FBClient читает ключи из .env (.ENV_*), но можно и явно передать:
        # self._client = FBClient(x_key=env.FB_API_KEY, x_secret=env.FB_API_SECRET)
        # Оставим автозагрузку из .env для совместимости с твоим проектом:
        self._client = FBClient()
        self.logger.info("FusionBrain client initialized successfully")

    # ---------- Публичный API ----------

    async def generate(
        self, 
        request: KandinskyGeneratorRequest
    ) -> KandinskyGeneratorResponse:
        """
        Главная точка входа: принимает Pydantic-запрос, возвращает Pydantic-ответ.
        """
        prompt: str = request.prompt

        # безопасные дефолты — чтобы сервис был толерантен к схеме
        images: int = int(getattr(request, "images", 1) or 1)
        width: int = int(getattr(request, "width", 1024) or 1024)
        height: int = int(getattr(request, "height", 1024) or 1024)
        style: str | None = getattr(request, "style", None)
        negative_prompt: str | None = getattr(request, "negative_prompt", None)
        file_basename: str = getattr(
            request, 
            "file_basename", 
            "kandinsky"
        ) or "kandinsky"
        extension: str = getattr(request, "extension", ".jpg") or ".jpg"

        if not prompt or not prompt.strip():
            raise KandinskyGeneratorError("Пустой prompt.")

        # 1) получаем id пайплайна (TEXT2IMAGE)
        pipeline_id = await self._get_text2image_pipeline_id()

        # 2) запускаем генерацию и ждём
        files_b64 = await self._run_and_wait(
            pipeline_id=pipeline_id,
            prompt=prompt,
            images=images,
            width=width,
            height=height,
            style=style,
            negative_prompt=negative_prompt,
        )

        # 3) сохраняем в images_out и строим URL’ы
        paths = await self._save_images(
            files_b64, 
            base_name=file_basename, 
            extension=extension
        )
        urls = [self._to_public_url(p) for p in paths]

        # 4) формируем ответ, поддерживая разные варианты твоей схемы
        try:
            # если в модели есть image_urls: List[str]
            return KandinskyGeneratorResponse(image_urls=urls)  # type: ignore[arg-type]
        except TypeError:
            # если модель ожидает один image_url: str — вернём первый
            return KandinskyGeneratorResponse(image_url=urls[0])  # type: ignore[arg-type]

    # ---------- Внутренние методы ----------

    async def _get_text2image_pipeline_id(self) -> str:
        try:
            pipelines = await anyio.to_thread.run_sync(
                self._client.get_pipelines_by_type, PipelineType.TEXT2IMAGE
            )
        except Exception as e:
            raise KandinskyGeneratorError(
                f"Не удалось получить список пайплайнов: {e}"
            ) from e

        if not pipelines:
            raise KandinskyGeneratorError("Не найден ни один пайплайн TEXT2IMAGE.")
        return pipelines[0].id

    async def _run_and_wait(
        self,
        *,
        pipeline_id: str,
        prompt: str,
        images: int,
        width: int,
        height: int,
        style: str | None,
        negative_prompt: str | None,
    ) -> list[str]:
        # Запуск — заворачиваем kwargs через partial
        try:
            run_result = await anyio.to_thread.run_sync(
                partial(
                    self._client.run_pipeline,
                    pipeline_id=pipeline_id,
                    prompt=prompt,
                    num_images=images,
                    width=width,
                    height=height,
                    style=style,
                    negative_prompt=negative_prompt,
                )
            )
        except Exception as e:
            raise KandinskyGeneratorError(f"Не удалось запустить генерацию: {e}") from e

        # Ожидание — тоже через partial для kwargs
        try:
            final = await anyio.to_thread.run_sync(
                partial(
                    self._client.wait_for_completion,
                    request_id=run_result.uuid,
                    initial_delay=run_result.status_time,
                )
            )
        except Exception as e:
            raise KandinskyGeneratorError(f"Ошибка ожидания результата: {e}") from e

        if getattr(final, "status", None) != "DONE":
            raise KandinskyGeneratorError(
                f"Генерация не удалась: status={getattr(final, 'status', 'UNKNOWN')}"
            )

        return list(getattr(final.result, "files", []) or [])

    async def _save_images(
        self, files_b64: list[str], *, base_name: str, extension: str = ".jpg"
    ) -> list[Path]:
        if not extension.startswith("."):
            extension = "." + extension
        # сохраняем в images_out, имена — base_name-1.jpg, base_name-2.jpg, …
        paths: list[Path] = []
        for i, b64str in enumerate(files_b64, start=1):
            fname = f"{base_name}-{i}{extension}"
            fpath = self._images_dir / fname
            try:
                await anyio.to_thread.run_sync(
                    fpath.write_bytes, base64.b64decode(b64str)
                )
            except Exception as e:
                raise KandinskyGeneratorError(
                    f"Не удалось записать файл {fpath}: {e}"
                ) from e
            paths.append(fpath.resolve())
        return paths

    def _to_public_url(self, file_path: Path) -> str:
        """
        Если задан PUBLIC_BASE_URL — собирает https://.../<relpath>,
        иначе возвращает file:/// абсолютный путь.
        """
        if self._public_base_url:
            try:
                rel = file_path.relative_to(Path.cwd())
            except ValueError:
                rel = file_path.name
            return f"{self._public_base_url.rstrip('/')}/{rel.as_posix()}"
        return file_path.resolve().as_uri()
