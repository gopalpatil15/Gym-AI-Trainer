import os
from typing import Any, Dict

import yaml

_DEFAULTS: Dict[str, Any] = {
    "database": {"connection_string": os.getenv("DATABASE_URL", "sqlite:///./demo.db"), "pool_size": 10},
    "embeddings": {"model": "sentence-transformers/all-MiniLM-L6-v2", "batch_size": 32},
    "cache": {"ttl_seconds": 300, "max_size": 1000},
}

_CONFIG_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "config.yml")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "config.yaml")),
]


def _env_expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _env_expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_env_expand(v) for v in value]
    return value


_cached: Dict[str, Any] | None = None


def get_settings() -> Dict[str, Any]:
    global _cached
    if _cached is not None:
        return _cached

    cfg: Dict[str, Any] = {**_DEFAULTS}
    for path in _CONFIG_PATHS:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                cfg = {**cfg, **_env_expand(loaded)}
            break
    _cached = cfg
    return cfg
