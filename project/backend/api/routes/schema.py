from __future__ import annotations

from fastapi import APIRouter

from ..utils.state import get_state

router = APIRouter()


@router.get("/schema")
async def get_schema():
    state = get_state()
    return state.schema or {}
