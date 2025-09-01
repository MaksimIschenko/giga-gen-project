""" Router for Model3DGenerator """
from __future__ import annotations

import asyncio
import mimetypes
import random
from pathlib import Path
from typing import Any

import httpx

from src.configs.environment import get_environment_settings
from src.configs.logging import get_logger
from src.configs.meshy import _MeshyConfig
from src.schemas.errors.model3d_generator import (
    Meshy3DError,
    Meshy3DProviderUnavailableError,
    Meshy3DTimeoutError,
)
from src.schemas.pydantic.model3d_generator import (
    Model3DGeneratorRequest,
    Model3DGeneratorResponse,
)


class Model3DGeneratorService:
    """
    Пайплайн Meshy Text-to-3D:
      preview 
      -> wait SUCCEEDED 
      -> refine (enable_pbr|texture_prompt) 
      -> wait SUCCEEDED -> download
    """

    def __init__(self) -> None:
        self.log = get_logger(__name__)
        env = get_environment_settings()

        api_key = getattr(env, "MESHY_API_KEY", None)
        if not api_key:
            raise Meshy3DError("Отсутствует MESHY_API_KEY в окружении.")

        out_dir = getattr(env, "MODELS_OUT_DIR", None) or "output/models"
        self._models_dir = Path(out_dir)
        self._models_dir.mkdir(parents=True, exist_ok=True)
        self.log.info(f"Models directory set to: {self._models_dir}")

        self._public_base_url: str | None = getattr(env, "PUBLIC_BASE_URL", None)
        self._cfg = _MeshyConfig(api_key=api_key)

        self._client = httpx.AsyncClient(
            base_url=self._cfg.base_url,
            headers={"Authorization": f"Bearer {self._cfg.api_key}"},
            timeout=httpx.Timeout(30.0, connect=30.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # -------- Публичный API --------

    async def generate(self, req: Model3DGeneratorRequest) -> Model3DGeneratorResponse:
        prompt = req.prompt.strip()
        if not prompt:
            raise Meshy3DError("Пустой prompt.")

        # профиль по mode
        mode = (req.mode or "lowpoly").lower()
        defaults = self._defaults_for_mode(mode)

        art_style = req.art_style or defaults["art_style"]
        topology = req.topology or defaults["topology"]
        target_polycount = int(req.target_polycount or defaults["target_polycount"])
        ai_model = req.ai_model
        texture_prompt = req.texture_prompt

        filename_prefix = req.filename_prefix or "model"
        desired_ext = (req.extension or ".fbx").lower()
        if not desired_ext.startswith("."):
            desired_ext = "." + desired_ext

        # preview
        preview_id = await self._create_preview(
            prompt=prompt,
            art_style=art_style,
            ai_model=ai_model,
            topology=topology,
            target_polycount=target_polycount,
            should_remesh=True,
            symmetry_mode="auto",
            is_a_t_pose=False,
        )
        await self._wait_succeeded(
            preview_id, timeout_sec=self._cfg.preview_timeout_sec
        )

        # refine
        enable_pbr = False if art_style == "sculpture" else True
        refine_id = await self._create_refine(
            preview_task_id=preview_id,
            enable_pbr=enable_pbr,
            texture_prompt=texture_prompt,
        )
        task_obj = await self._wait_succeeded(
            refine_id, timeout_sec=self._cfg.refine_timeout_sec
        )

        # download
        model_url, picked_ext = self._pick_model_url(task_obj, desired_ext)
        fpath = await self._download(model_url, filename_prefix, picked_ext)

        return Model3DGeneratorResponse(model_url=self._to_public_url(fpath))

    # -------- Внутреннее --------

    def _defaults_for_mode(self, mode: str) -> dict[str, Any]:
        if mode == "realistic":
            return {
                "art_style": "realistic", 
                "topology": "quad", 
                "target_polycount": 30000
            }
        return {
            "art_style": "realistic", 
            "topology": "triangle", 
            "target_polycount": 10000
        }

    # --- HTTP helpers с ретраями ---

    async def _post(self, path: str, json: dict[str, Any]) -> httpx.Response:
        tries = self._cfg.retry_tries
        for i in range(tries):
            r = await self._client.post(path, json=json)
            if r.status_code in (429,) or r.status_code >= 500:
                delay = min(self._cfg.retry_cap, self._cfg.retry_base * (2 ** i)) + random.uniform(0, 0.2) # noqa
                await asyncio.sleep(delay)
                continue
            return r
        return r  # последний ответ

    async def _get(self, path: str) -> httpx.Response:
        tries = self._cfg.retry_tries
        for i in range(tries):
            r = await self._client.get(path)
            if r.status_code in (429,) or r.status_code >= 500:
                delay = min(self._cfg.retry_cap, self._cfg.retry_base * (2 ** i)) + random.uniform(0, 0.2) # noqa
                await asyncio.sleep(delay)
                continue
            return r
        return r

    # --- Meshy endpoints ---

    async def _create_preview(
        self,
        *,
        prompt: str,
        art_style: str,
        ai_model: str,
        topology: str,
        target_polycount: int,
        should_remesh: bool,
        symmetry_mode: str,
        is_a_t_pose: bool,
    ) -> str:
        payload = {
            "mode": "preview",
            "prompt": prompt,
            "art_style": art_style,
            "ai_model": ai_model,
            "topology": topology,
            "target_polycount": target_polycount,
            "should_remesh": should_remesh,
            "symmetry_mode": symmetry_mode,
            "is_a_t_pose": is_a_t_pose,
        }
        try:
            r = await self._post("/openapi/v2/text-to-3d", payload)
        except Exception as e:
            raise Meshy3DError(f"Сеть/preview: {e}") from e

        if r.status_code == 401 or r.status_code == 403:
            raise Meshy3DProviderUnavailableError(
                "Unauthorized/Forbidden: проверьте MESHY_API_KEY."
            ) 
        if r.status_code != 200:
            raise Meshy3DProviderUnavailableError(
                f"Preview failed {r.status_code}: {r.text}"
            )

        task_id = (r.json() or {}).get("result")
        if not task_id:
            raise Meshy3DError(f"Preview: пустой result: {r.text}")
        return task_id

    async def _create_refine(
        self, 
        *, 
        preview_task_id: str, 
        enable_pbr: bool, 
        texture_prompt: str | None
    ) -> str:
        payload = {
            "mode": "refine", 
            "preview_task_id": preview_task_id, 
            "enable_pbr": enable_pbr,
        }
        if texture_prompt:
            payload["texture_prompt"] = texture_prompt
        try:
            r = await self._post("/openapi/v2/text-to-3d", payload)
        except Exception as e:
            raise Meshy3DError(f"Сеть/refine: {e}") from e

        if r.status_code == 401 or r.status_code == 403:
            raise Meshy3DProviderUnavailableError(
                "Unauthorized/Forbidden: проверьте MESHY_API_KEY."
            )
        if r.status_code != 200:
            raise Meshy3DProviderUnavailableError(
                f"Refine failed {r.status_code}: {r.text}"
            )

        task_id = (r.json() or {}).get("result")
        if not task_id:
            raise Meshy3DError(f"Refine: пустой result: {r.text}")
        return task_id

    async def _wait_succeeded(
        self,
        task_id: str, 
        *, timeout_sec: int
    ) -> dict[str, Any]:
        start = asyncio.get_event_loop().time()
        while True:
            try:
                r = await self._get(f"/openapi/v2/text-to-3d/{task_id}")
            except Exception as e:
                raise Meshy3DError(f"Сеть/status: {e}") from e

            if r.status_code == 401 or r.status_code == 403:
                raise Meshy3DProviderUnavailableError(
                    "Unauthorized/Forbidden: проверьте MESHY_API_KEY."
                )
            if r.status_code != 200:
                raise Meshy3DProviderUnavailableError(
                    f"Status failed {r.status_code}: {r.text}"
                )

            obj = r.json() or {}
            status = obj.get("status")
            if status == "SUCCEEDED":
                return obj
            if status in {"FAILED", "CANCELED"}:
                msg = (obj.get("task_error") or {}).get("message") or "Meshy task failed" # noqa
                raise Meshy3DProviderUnavailableError(msg)

            if asyncio.get_event_loop().time() - start > timeout_sec:
                raise Meshy3DTimeoutError(f"Превышено время ожидания: {task_id}")

            await asyncio.sleep(self._cfg.poll_interval_sec)

    def _pick_model_url(
        self, task_obj: dict[str, Any], desired_ext: str
    ) -> tuple[str, str]:
        model_urls = task_obj.get("model_urls") or {}
        order = [desired_ext, ".fbx", ".glb", ".obj", ".usdz"]
        keys = {".fbx": "fbx", ".glb": "glb", ".obj": "obj", ".usdz": "usdz"}
        for ext in order:
            key = keys.get(ext)
            url = model_urls.get(key) if key else None
            if url:
                return url, ext
        raise Meshy3DError("В ответе нет доступных model_urls (fbx/glb/obj/usdz).")

    async def _download(self, url: str, prefix: str, ext: str) -> Path:
        if not ext.startswith("."):
            ext = "." + ext
        if mimetypes.guess_type(f"x{ext}")[0] is None:
            ext = ".fbx"
        fpath = self._models_dir / f"{prefix}{ext}"
        try:
            async with self._client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise Meshy3DProviderUnavailableError(
                        f"Download failed {resp.status_code}"
                    )
                with fpath.open("wb") as fd:
                    async for chunk in resp.aiter_bytes():
                        fd.write(chunk)
        except Exception as e:
            raise Meshy3DError(f"Не удалось скачать модель: {e}") from e
        return fpath.resolve()

    def _to_public_url(self, file_path: Path) -> str:
        if self._public_base_url:
            try:
                rel = file_path.relative_to(Path.cwd())
            except ValueError:
                rel = file_path.name
            return f"{self._public_base_url.rstrip('/')}/{rel.as_posix()}"
        return file_path.as_uri()
