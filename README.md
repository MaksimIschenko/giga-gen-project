# Giga Gen Project

API для генерации изображений и 3D-моделей с использованием искусственного интеллекта.

## Описание

Giga Gen Project предоставляет REST API для генерации:
- **Простых изображений** (логотипы, иконки) через GigaChat
- **Сложных изображений** (художественные картины) через Kandinsky/FusionBrain
- **3D-моделей** (FBX файлы) через GigaChat

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/MaksimIschenko/giga-gen-project
cd giga-gen-project
```

2. Установите зависимости:
```bash
uv sync
```

3. Настройте переменные окружения в файле `.env`:
```env
# GigaChat настройки
GIGACHAT_AUTH_KEY=your_auth_key
GIGACHAT_CLIENT_SECRET=your_client_secret
GIGACHAT_CLIENT_ID=your_client_id
GIGACHAT_SCOPE=your_scope
GIGACHAT_VERIFY_SSL=1

# FusionBrain настройки
FB_API_KEY=your_fb_api_key
FB_API_SECRET=your_fb_api_secret

# Пути для сохранения файлов
IMAGES_OUT_DIR=images_out
MODELS_OUT_DIR=models_out

# Публичный базовый URL (опционально)
PUBLIC_BASE_URL=https://your-domain.com
```

4. Запустите приложение:
```bash
uv run uvicorn main:app --reload
```

## API Endpoints

### 1. Генерация простых изображений

**POST** `/v1/simple/generate`

Генерирует простые изображения (логотипы, иконки) через GigaChat.

#### Параметры запроса:

```json
{
  "prompt": "Простой логотип для компании, которая делает программное обеспечение для малых бизнесов",
  "mode": "logo",
  "fewshot": true,
  "style": "Минималистичный стиль, плоская геометрия, белый фон",
  "filename_prefix": "company_logo",
  "extension": ".png"
}
```

#### Параметры:

- `prompt` (string, обязательный) - Описание изображения
- `mode` (string, опциональный) - Режим генерации: `"icon"` или `"logo"` (по умолчанию: `"icon"`)
- `fewshot` (boolean, опциональный) - Добавлять ли демонстрационный ответ ассистента (по умолчанию: `true`)
- `style` (string, опциональный) - Кастомный системный промпт
- `filename_prefix` (string, опциональный) - Префикс имени файла (по умолчанию: `"gen"`)
- `extension` (string, опциональный) - Расширение файла (по умолчанию: `".jpg"`)

#### Ответ:

```json
{
  "image_url": "https://example.com/images_out/company_logo-abc123.png"
}
```

### 2. Генерация сложных изображений

**POST** `/v1/kandinsky/generate`

Генерирует сложные художественные изображения через Kandinsky/FusionBrain.

#### Параметры запроса:

```json
{
  "prompt": "Реалистичное изображение сноубордиста фристайл в прыжке, яркое солнце",
  "images": 1,
  "width": 1024,
  "height": 1024,
  "style": "CINEMATIC",
  "negative_prompt": "Размытый фон, низкое качество",
  "file_basename": "snowboarder_freestyle",
  "extension": ".jpg"
}
```

#### Параметры:

- `prompt` (string, обязательный) - Описание изображения
- `images` (integer, опциональный) - Количество изображений (1-10, по умолчанию: `1`)
- `width` (integer, опциональный) - Ширина в пикселях (по умолчанию: `1024`)
- `height` (integer, опциональный) - Высота в пикселях (по умолчанию: `1024`)
- `style` (string, опциональный) - Стиль (например, `"ANIME"`, `"CINEMATIC"`)
- `negative_prompt` (string, опциональный) - Нежелательные детали
- `file_basename` (string, опциональный) - Базовое имя файла (по умолчанию: `"kandinsky"`)
- `extension` (string, опциональный) - Расширение файла (по умолчанию: `".jpg"`)

#### Ответ:

```json
{
  "image_urls": [
    "https://example.com/images_out/snowboarder_freestyle-1.jpg"
  ]
}
```

### 3. Генерация 3D-моделей

**POST** `/v1/model3d/generate`

Генерирует 3D-модели в формате FBX через GigaChat.

#### Параметры запроса:

```json
{
  "prompt": "3D-модель кубка соревнований из золота",
  "mode": "lowpoly",
  "fewshot": true,
  "style": "Кастомный системный промпт для 3D-модели",
  "filename_prefix": "reward",
  "extension": ".fbx"
}
```

#### Параметры:

- `prompt` (string, обязательный) - Описание 3D-модели
- `mode` (string, опциональный) - Стиль генерации: `"lowpoly"` или `"realistic"` (по умолчанию: `"lowpoly"`)
- `fewshot` (boolean, опциональный) - Добавлять ли демонстрационный ответ (по умолчанию: `true`)
- `style` (string, опциональный) - Кастомный системный промпт
- `filename_prefix` (string, опциональный) - Префикс имени файла (по умолчанию: `"model"`)
- `extension` (string, опциональный) - Расширение файла (по умолчанию: `".fbx"`)

#### Ответ:

```json
{
  "model_url": "https://example.com/models_out/reward-xyz789.fbx"
}
```

## Коды ошибок

- `400` - Неверный запрос (некорректные параметры)
- `422` - Ошибка валидации данных
- `502` - Ошибка внешнего сервиса (GigaChat/FusionBrain)
- `504` - Превышено время ожидания
- `500` - Внутренняя ошибка сервера

## Логирование

Проект использует [loguru](https://github.com/Delgan/loguru) для логирования. Логи сохраняются в папку `logs/` с автоматической ротацией.

### Конфигурация логирования:

- **Уровень**: INFO (по умолчанию)
- **Файл**: `logs/app.log`
- **Ротация**: 10 MB
- **Хранение**: 7 дней
- **Сжатие**: ZIP

### Примеры использования:

```python
from src.configs.logging import get_logger

logger = get_logger(__name__)
logger.info("Сообщение для логирования")
logger.error("Ошибка", exc_info=True)
```

## Структура проекта

```
giga-gen-project/
├── main.py                 # Точка входа FastAPI приложения
├── src/
│   ├── configs/           # Конфигурация
│   │   ├── environment.py # Настройки окружения
│   │   └── logging.py     # Конфигурация логирования
│   ├── routers/           # API роутеры
│   │   └── v1/
│   │       ├── simple_generator.py
│   │       ├── kandinsky_generator.py
│   │       └── model3d_generator.py
│   ├── services/          # Бизнес-логика
│   │   ├── simple_generator.py
│   │   ├── kandinsky_generator.py
│   │   └── model3d_generator.py
│   └── schemas/           # Pydantic модели
│       ├── pydantic/
│       └── errors/
├── logs/                  # Логи приложения
├── images_out/           # Сгенерированные изображения
├── models_out/           # Сгенерированные 3D-модели
└── pyproject.toml        # Зависимости проекта
```

## Разработка

### Запуск в режиме разработки:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Проверка кода:

```bash
uv run ruff check . --fix
```

### Документация API:

После запуска приложения документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Лицензия

Проект распространяется под лицензией [MIT](./LICENSE).