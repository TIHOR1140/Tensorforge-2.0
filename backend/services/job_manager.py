"""Asynchronous batch job manager for large evaluations (1 to 5,000 tickets)."""

import uuid
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from backend.core.config import settings
from backend.core.constants import JobStatus
from backend.models.pipeline import pipeline
from backend.schemas.batch_jobs import (
    BatchJobStatus,
    BatchJobResults,
    BatchJobError,
)
from backend.schemas.predict import BatchRequestTicket, PredictResponse


class JobRecord:
    """Internal record tracking an async batch job."""

    def __init__(self, job_id: str, tickets: List[BatchRequestTicket], model_version: str):
        self.job_id = job_id
        self.tickets = tickets
        self.total = len(tickets)
        self.processed = 0
        self.status = JobStatus.QUEUED
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.expires_at: Optional[str] = None
        self.model_version = model_version
        self.error: Optional[BatchJobError] = None
        self.predictions: List[PredictResponse] = []
        self.cancelled = False


class BatchJobManager:
    """Thread-safe manager handling queuing, background processing, idempotency,

    concurrency limits, pagination, and retention rules for batch jobs.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, JobRecord] = {}
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> job_id
        self._queue: List[str] = []
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._start_worker()

    def _start_worker(self):
        self._worker_thread = threading.Thread(target=self._process_queue_loop, daemon=True)
        self._worker_thread.start()

    def _process_queue_loop(self):
        """Background worker thread processing jobs one by one without blocking API traffic."""
        while not self._stop_event.is_set():
            job_to_run: Optional[JobRecord] = None
            with self._lock:
                if self._queue:
                    next_job_id = self._queue.pop(0)
                    job_to_run = self._jobs.get(next_job_id)
                    if job_to_run and job_to_run.status == JobStatus.QUEUED:
                        job_to_run.status = JobStatus.RUNNING
                        job_to_run.started_at = datetime.now(timezone.utc).isoformat()

            if job_to_run:
                self._execute_job(job_to_run)
            else:
                time.sleep(0.5)

    def _execute_job(self, job: JobRecord):
        """Execute predictions on job tickets in chunks while updating progress."""
        try:
            batch_size = 50
            results: List[PredictResponse] = []

            for i in range(0, job.total, batch_size):
                if job.cancelled:
                    with self._lock:
                        job.status = JobStatus.CANCELLED
                        job.finished_at = datetime.now(timezone.utc).isoformat()
                    return

                chunk = job.tickets[i : i + batch_size]
                chunk_preds = pipeline.predict_batch(chunk)
                results.extend(chunk_preds)

                with self._lock:
                    job.processed = len(results)

                # Brief yield so other tasks are never starved
                time.sleep(0.005)

            with self._lock:
                job.predictions = results
                job.status = JobStatus.SUCCEEDED
                job.finished_at = datetime.now(timezone.utc).isoformat()
                now_utc = datetime.now(timezone.utc)
                job.expires_at = (now_utc + timedelta(hours=settings.JOB_RETENTION_HOURS)).isoformat()

        except Exception as exc:
            with self._lock:
                job.status = JobStatus.FAILED
                job.finished_at = datetime.now(timezone.utc).isoformat()
                job.error = BatchJobError(code="interrupted", message=str(exc))

    def submit_job(
        self,
        tickets: List[BatchRequestTicket],
        idempotency_key: Optional[str] = None
    ) -> Tuple[BatchJobStatus, bool, int]:
        """Submit a new job or return existing one if idempotency key matches.

        Returns: (BatchJobStatus, is_existing, http_status_code)
        """
        with self._lock:
            # 1. Idempotency check
            if idempotency_key and idempotency_key in self._idempotency_map:
                existing_id = self._idempotency_map[idempotency_key]
                if existing_id in self._jobs:
                    return self._to_status_schema(self._jobs[existing_id]), True, 202

            # 2. Concurrency checks: 1 running, max 3 queued
            running_count = sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)
            queued_count = sum(1 for j in self._jobs.values() if j.status == JobStatus.QUEUED)

            if running_count >= settings.MAX_CONCURRENT_JOBS and queued_count >= settings.MAX_QUEUED_JOBS:
                return None, False, 429

            # 3. Create job
            job_id = f"job-{uuid.uuid4().hex[:12]}"
            job = JobRecord(job_id=job_id, tickets=tickets, model_version=pipeline.model_version)
            self._jobs[job_id] = job
            self._queue.append(job_id)

            if idempotency_key:
                self._idempotency_map[idempotency_key] = job_id

            return self._to_status_schema(job), False, 202

    def get_job_status(self, job_id: str) -> Tuple[Optional[BatchJobStatus], int]:
        """Get status of a job. Returns (status, http_code)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None, 404

            # Check retention / expiration
            if job.expires_at:
                exp = datetime.fromisoformat(job.expires_at)
                if datetime.now(timezone.utc) > exp:
                    return None, 410

            return self._to_status_schema(job), 200

    def get_job_results(
        self, job_id: str, offset: int = 0, limit: int = 100
    ) -> Tuple[Optional[BatchJobResults], int]:
        """Get paginated results of a succeeded job. Returns (results, http_code)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None, 404

            if job.expires_at:
                exp = datetime.fromisoformat(job.expires_at)
                if datetime.now(timezone.utc) > exp:
                    return None, 410

            if job.status != JobStatus.SUCCEEDED:
                return None, 409  # Conflict: Job not completed yet

            total = len(job.predictions)
            page = job.predictions[offset : offset + limit]
            next_off = offset + limit if (offset + limit) < total else None

            results = BatchJobResults(
                job_id=job.job_id,
                status="succeeded",
                total=total,
                offset=offset,
                limit=limit,
                next_offset=next_off,
                model_version=job.model_version,
                predictions=page
            )
            return results, 200

    def cancel_or_discard_job(self, job_id: str) -> int:
        """Cancel a running/queued job or discard a finished job. Returns HTTP status code."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return 404

            if job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                job.cancelled = True
                job.status = JobStatus.CANCELLED
                job.finished_at = datetime.now(timezone.utc).isoformat()
            else:
                # Discard finished job
                del self._jobs[job_id]

            return 204

    @staticmethod
    def _to_status_schema(job: JobRecord) -> BatchJobStatus:
        return BatchJobStatus(
            job_id=job.job_id,
            status=job.status,
            total=job.total,
            processed=job.processed,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            expires_at=job.expires_at,
            model_version=job.model_version,
            error=job.error
        )


job_manager = BatchJobManager()
