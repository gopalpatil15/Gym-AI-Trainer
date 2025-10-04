from __future__ import annotations

import os
import shutil
import tempfile
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, UploadFile

from ..services.document_processor import DocumentProcessor, EmbeddingProvider
from ..services.query_engine import QueryEngine
from ..services.schema_discovery import SchemaDiscovery
from ..utils.db import test_connection
from ..utils.logger import get_logger
from ..utils.state import get_state
from ..utils.vector_store import VectorStore

router = APIRouter()
_logger = get_logger(__name__)


@router.post("/connect-database")
async def connect_database(connection_string: str):
    ok = test_connection(connection_string)
    if not ok:
        return {"success": False, "error": "Failed to connect to database"}

    state = get_state()
    state.connection_string = connection_string
    schema = SchemaDiscovery().analyze_database(connection_string)
    state.schema = schema
    state.query_engine = QueryEngine(connection_string, state)
    return {"success": True, "schema": schema}


@router.post("/ingest/database")
async def ingest_database(connection_string: str):
    return await connect_database(connection_string)


@router.post("/upload-documents")
async def upload_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    state = get_state()
    if state.vector_store is None:
        state.vector_store = VectorStore()

    # Save uploads to temp dir
    tmp_dir = tempfile.mkdtemp(prefix="uploads_")
    file_paths = []
    for f in files:
        dest = os.path.join(tmp_dir, f.filename)
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        file_paths.append(dest)

    job = await state.job_manager.create_job(total=len(file_paths))

    async def on_progress(done: int):
        await state.job_manager.update(job.job_id, completed=done, status="running")

    async def run_job(paths):
        try:
            dp = DocumentProcessor(state.vector_store, EmbeddingProvider())
            await dp.process_documents(paths, job_cb=on_progress)
            # Attach text to stored metadata for display (store in state.document_index)
            await state.job_manager.update(job.job_id, status="completed")
        except Exception as exc:  # noqa: BLE001
            _logger.error("Document ingestion failed: %s", exc)
            await state.job_manager.update(job.job_id, error=str(exc))

    background_tasks.add_task(run_job, file_paths)
    return {"job_id": job.job_id, "total": job.total}


@router.post("/ingest/documents")
async def ingest_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    return await upload_documents(background_tasks, files)


@router.get("/ingestion-status/{job_id}")
async def get_status(job_id: str):
    state = get_state()
    js = await state.job_manager.get(job_id)
    if not js:
        return {"error": "job not found"}
    return js.to_dict()
