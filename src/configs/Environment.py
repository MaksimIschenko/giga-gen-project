""" Environment settings """
import os
from functools import lru_cache

from pydantic_settings import BaseSettings


@lru_cache
def get_settings() -> str:
    runtime_env = os.getenv("ENV")
    return f".env.{runtime_env}" if runtime_env else ".env"

class EnvironmentSettings(BaseSettings):
    # GIGA
    GIGACHAT_AUTH_KEY: str
    GIGACHAT_CLIENT_SECRET: str
    GIGACHAT_CLIENT_ID: str
    GIGACHAT_SCOPE: str
    GIGACHAT_VERIFY_SSL: int

    # FUSION BRAIN
    FB_API_KEY: str
    FB_API_SECRET: str
    
    # PATHS
    IMAGES_OUT_DIR: str
    MODELS_OUT_DIR: str
    
    class Config:
        env_file = get_settings()
        env_file_encoding = "utf-8"
        
@lru_cache
def get_environment_settings() -> EnvironmentSettings:
    """Возвращает EnvironmentSettings

    :return: EnvironmentSettings
    :rtype: EnvironmentSettings
    """
    return EnvironmentSettings()