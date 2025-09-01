#!/usr/bin/env python3
"""
CLI для генерации 3D-моделей через GigaChat (text2model3d).
Пример запуска:
    python model3d_cli.py 
        --prompt "Простая низкополигональная модель стула"
        --mode lowpoly
"""

import argparse
import asyncio
import sys

from src.schemas.pydantic.model3d_generator import Model3DGeneratorRequest
from src.services.model3d_generator import Model3DGeneratorService


async def main() -> None:
    parser = argparse.ArgumentParser(description="GigaChat 3D Model Generator (text2model3d)") # noqa
    parser.add_argument("--prompt", type=str, required=True, help="Описание модели для генерации") # noqa
    parser.add_argument("--mode", choices=["lowpoly", "realistic"], default="lowpoly", help="Режим генерации") # noqa
    parser.add_argument("--style", type=str, default=None, help="Опциональный system-промпт (перепишет встроенный)") # noqa
    parser.add_argument("--filename-prefix", type=str, default="model", help="Префикс имени файла (по умолчанию 'model')") # noqa
    parser.add_argument("--extension", type=str, default=".fbx", help="Расширение файла (.fbx по умолчанию)") # noqa
    parser.add_argument("--no-fewshot", action="store_true", help="Отключить few-shot подсказку") # noqa

    args = parser.parse_args()

    # собираем pydantic-запрос
    req = Model3DGeneratorRequest(
        prompt=args.prompt,
        mode=args.mode,
        style=args.style,
        filename_prefix=args.filename_prefix,
        extension=args.extension,
        fewshot=not args.no_fewshot,
    )

    service = Model3DGeneratorService()
    try:
        resp = await service.generate(req)
        print(f"✅ Модель сгенерирована: {resp.model_url}")
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
