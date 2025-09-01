# generate_kandinsky_sdk.py
import base64
from pathlib import Path
from typing import Optional, List

from fusionbrain_sdk_python import FBClient, PipelineType  # SDK из репозитория


def save_images_b64_to_root(images_b64: List[str], base_name: str = "kandinsky") -> List[Path]:
    """
    Сохраняет список base64-строк в КОРЕНЬ проекта (Path.cwd()).
    Возвращает список абсолютных путей.
    """
    out_paths = []
    root = Path.cwd()
    for i, b64str in enumerate(images_b64, start=1):
        fname = f"{base_name}-{i}.jpg"
        fpath = root / fname
        fpath.write_bytes(base64.b64decode(b64str))
        out_paths.append(fpath.resolve())
    return out_paths


def generate_image_with_sdk(
    prompt: str,
    *,
    images: int = 1,
    width: int = 1024,
    height: int = 1024,
    style: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    file_basename: str = "kandinsky",
) -> List[Path]:
    """
    Генерирует изображение(я) через FusionBrain SDK и сохраняет результат(ы) в корень проекта.
    Возвращает список путей к сохранённым файлам.
    """
    # 1) Инициализация клиента: SDK сам возьмёт ключи из .env (или можно передать x_key/x_secret)
    client = FBClient()  # см. README (Auth/Getting Started) :contentReference[oaicite:2]{index=2}

    # 2) Найдём пайплайн для текст→картинка
    pipelines = client.get_pipelines_by_type(PipelineType.TEXT2IMAGE)  # :contentReference[oaicite:3]{index=3}
    if not pipelines:
        raise RuntimeError("Не найден ни один TEXT2IMAGE пайплайн.")
    pipe = pipelines[0]

    # 3) Запускаем генерацию
    run_result = client.run_pipeline(
        pipeline_id=pipe.id,
        prompt=prompt,
        num_images=images,
        width=width,
        height=height,
        style=style,                       # можно None
        negative_prompt=negative_prompt,   # можно None
    )  # см. README (run_pipeline) :contentReference[oaicite:4]{index=4}

    # 4) Ждём готовности
    final = client.wait_for_completion(
        request_id=run_result.uuid,
        initial_delay=run_result.status_time,
    )  # см. README (wait_for_completion) :contentReference[oaicite:5]{index=5}

    if final.status != "DONE":
        raise RuntimeError(f"Генерация не удалась: status={final.status}")

    # 5) Сохраняем base64-изображения в корень проекта
    return save_images_b64_to_root(final.result.files, base_name=file_basename)


if __name__ == "__main__":
    paths = generate_image_with_sdk(
        prompt="Реалистичное изображение сноубордиста фристайл в прыжке, яркое солнце.",
        images=1,
        width=1024,
        height=1024,
        style=None,  # пример: "ANIME" — список стилей смотрите в документации FusionBrain
        negative_prompt=None,
        file_basename="snowboarder_freestyle",
    )
    print("Сохранено:", *map(str, paths), sep="\n- ")
