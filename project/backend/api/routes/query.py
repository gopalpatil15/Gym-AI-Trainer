from __future__ import annotations

import time
from typing import Any, Dict, List

from fastapi import APIRouter

from ..services.query_engine import QueryEngine
from ..utils.logger import get_logger
from ..utils.state import QueryRecord, get_state

router = APIRouter()
_logger = get_logger(__name__)


@router.post("/query")
async def process_query(query: str):
    state = get_state()
    if state.query_engine is None:
        return {"error": "Database not connected"}

    t0 = time.time()
    result = state.query_engine.process_query(query)
    took_ms = int((time.time() - t0) * 1000)
    cache_hit = bool(result.get("performance_metrics", {}).get("cache_hit", False))
    state.query_history.append(
        QueryRecord(query=query, query_type=result.get("query_type", "unknown"), took_ms=took_ms, cache_hit=cache_hit)
    )
    # Attach cache hit explicitly
    result["performance_metrics"]["took_ms"] = took_ms
    return result


@router.get("/query/history")
async def get_history():
    state = get_state()
    return [qr.__dict__ for qr in state.query_history[-50:]]
