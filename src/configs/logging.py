""" Logging configuration using loguru """

import sys
from pathlib import Path

from loguru import logger


def setup_logging(
    log_level: str = "INFO",
    log_file: str | Path | None = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_string: str | None = None,
) -> None:
    """
    Настройка логирования через loguru.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов (если None, логи только в консоль)
        rotation: Ротация логов (например, "10 MB", "1 day")
        retention: Время хранения логов (например, "7 days", "1 month")
        format_string: Кастомный формат логов
    """
    # Удаляем стандартный обработчик loguru
    logger.remove()
    
    # Формат по умолчанию
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # Добавляем обработчик для консоли
    logger.add(
        sys.stderr,
        format=format_string,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Добавляем обработчик для файла, если указан
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_path,
            format=format_string,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
        )


def get_logger(name: str | None = None) -> logger:
    """
    Получить логгер для модуля.
    """
    if name:
        return logger.bind(name=name)
    return logger


# Настройка логирования по умолчанию
def setup_default_logging() -> None:
    """Настройка логирования с параметрами по умолчанию."""
    setup_logging(
        log_level="INFO",
        log_file="logs/app.log",
        rotation="10 MB",
        retention="7 days",
    )
