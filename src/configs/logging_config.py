""" Configuration examples for logging """

from src.configs.logging import setup_logging

# Примеры различных конфигураций логирования

def setup_development_logging() -> None:
    """Настройка логирования для разработки."""
    setup_logging(
        log_level="DEBUG",
        log_file="logs/dev.log",
        rotation="1 day",
        retention="3 days",
    )


def setup_production_logging() -> None:
    """Настройка логирования для продакшена."""
    setup_logging(
        log_level="INFO",
        log_file="logs/prod.log",
        rotation="100 MB",
        retention="30 days",
    )


def setup_testing_logging() -> None:
    """Настройка логирования для тестов."""
    setup_logging(
        log_level="WARNING",
        log_file=None,  # Только консоль
    )
