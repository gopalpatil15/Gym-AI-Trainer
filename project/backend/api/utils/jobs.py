from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class JobStatus:
    job_id: str
    total: int = 0
    completed: int = 0
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    started_at: float = field(default_factory=lambda: time.time())
    finished_at: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "total": self.total,
            "completed": self.completed,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "progress": (self.completed / self.total) if self.total else 0.0,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobStatus] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, total: int) -> JobStatus:
        job_id = str(uuid.uuid4())
        status = JobStatus(job_id=job_id, total=total, status="pending")
        async with self._lock:
            self._jobs[job_id] = status
        return status

    async def get(self, job_id: str) -> Optional[JobStatus]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(self, job_id: str, *, completed: Optional[int] = None, status: Optional[str] = None, error: Optional[str] = None) -> None:
        async with self._lock:
            js = self._jobs.get(job_id)
            if not js:
                return
            if completed is not None:
                js.completed = completed
            if status is not None:
                js.status = status
                if status == "completed":
                    js.finished_at = time.time()
            if error is not None:
                js.error = error
                js.status = "failed"
                js.finished_at = time.time()

    async def list_jobs(self) -> Dict[str, Dict]:
        async with self._lock:
            return {k: v.to_dict() for k, v in self._jobs.items()}
