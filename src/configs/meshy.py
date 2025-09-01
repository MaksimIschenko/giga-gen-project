""" Meshy config """
from dataclasses import dataclass


@dataclass
class _MeshyConfig:
    """ Meshy config """
    api_key: str
    base_url: str = "https://api.meshy.ai"
    poll_interval_sec: float = 2.5
    preview_timeout_sec: int = 600
    refine_timeout_sec: int = 1200
    # backoff
    retry_tries: int = 5
    retry_base: float = 0.5
    retry_cap: float = 4.0