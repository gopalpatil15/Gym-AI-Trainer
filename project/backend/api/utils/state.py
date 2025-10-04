from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .cache import TTLCache
from .jobs import JobManager


@dataclass
class QueryRecord:
    query: str
    query_type: str
    took_ms: float
    cache_hit: bool


@dataclass
class AppState:
    connection_string: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    query_cache: TTLCache = field(default_factory=lambda: TTLCache())
    query_history: List[QueryRecord] = field(default_factory=list)
    job_manager: JobManager = field(default_factory=JobManager)
    vector_store: Any | None = None
    document_index: List[Dict[str, Any]] = field(default_factory=list)
    query_engine: Any | None = None


_state: AppState | None = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
