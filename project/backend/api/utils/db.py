from __future__ import annotations

from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import get_settings
from .logger import get_logger

_logger = get_logger(__name__)

_engine_cache: dict[str, Engine] = {}


def get_engine(connection_string: Optional[str] = None) -> Engine:
    settings = get_settings()
    conn_str = connection_string or settings["database"]["connection_string"]
    if conn_str in _engine_cache:
        return _engine_cache[conn_str]
    pool_size = int(settings["database"].get("pool_size", 10))
    engine = create_engine(
        conn_str,
        pool_size=pool_size,
        pool_pre_ping=True,
        future=True,
    )
    _engine_cache[conn_str] = engine
    return engine


def test_connection(connection_string: str) -> bool:
    try:
        engine = get_engine(connection_string)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        _logger.error("DB connection failed: %s", exc)
        return False
