"""Asynchronous batch job manager for large evaluations (1 to 5,000 tickets)."""

import json
import uuid
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
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

    def __init__(
        self,
        job_id: str,
        tickets: List[BatchRequestTicket],
        model_version: str,
        status: JobStatus = JobStatus.QUEUED,
        total: Optional[int] = None,
        processed: int = 0,
        created_at: Optional[str] = None,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
        expires_at: Optional[str] = None,
        error: Optional[BatchJobError] = None,
        predictions: Optional[List[PredictResponse]] = None,
        cancelled: bool = False,
    ):
        self.job_id = job_id
        self.tickets = tickets
        self.total = total if total is not None else len(tickets)
        self.processed = processed
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.started_at = started_at
        self.finished_at = finished_at
        self.expires_at = expires_at
        self.model_version = model_version
        self.error = error
        self.predictions: List[PredictResponse] = predictions or []
        self.cancelled = cancelled


class BatchJobManager:
    """Thread-safe manager handling queuing, background processing, idempotency,

    concurrency limits, pagination, persistence, and retention rules for batch jobs.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, JobRecord] = {}
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> job_id
        self._queue: List[str] = []
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._storage_dir: Path = settings.JOBS_STORAGE_DIR
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._recover_stored_jobs()
        self._start_worker()

    def _recover_stored_jobs(self):
        """Recover persisted jobs and handle restart tolerance."""
        now_utc = datetime.now(timezone.utc)
        retention_exp = (now_utc + timedelta(hours=settings.JOB_RETENTION_HOURS)).isoformat()

        try:
            for job_file in self._storage_dir.glob("job-*.json"):
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    job_id = data.get("job_id")
                    if not job_id:
                        continue

                    status = JobStatus(data.get("status", JobStatus.FAILED.value))
                    error_data = data.get("error")
                    error = BatchJobError(**error_data) if error_data else None

                    # If container restarted while job was running/queued -> mark interrupted
                    if status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                        status = JobStatus.FAILED
                        error = BatchJobError(
                            code="interrupted",
                            message="Service restarted while the job was running."
                        )
                        data["status"] = status.value
                        data["finished_at"] = now_utc.isoformat()
                        data["expires_at"] = retention_exp
                        data["error"] = error.model_dump()
                        with open(job_file, "w", encoding="utf-8") as f:
                            json.dump(data, f)

                    predictions = [
                        PredictResponse(**p) for p in data.get("predictions", [])
                    ]
                    tickets = [
                        BatchRequestTicket(**t) for t in data.get("tickets", [])
                    ]

                    record = JobRecord(
                        job_id=job_id,
                        tickets=tickets,
                        model_version=data.get("model_version", settings.MODEL_VERSION),
                        status=status,
                        total=data.get("total", len(tickets)),
                        processed=data.get("processed", len(predictions)),
                        created_at=data.get("created_at"),
                        started_at=data.get("started_at"),
                        finished_at=data.get("finished_at"),
                        expires_at=data.get("expires_at"),
                        error=error,
                        predictions=predictions,
                    )
                    self._jobs[job_id] = record
                except Exception:
                    pass
        except Exception:
            pass

    def _save_job_to_disk(self, job: JobRecord):
        """Persist a job record and results to disk."""
        try:
            job_file = self._storage_dir / f"{job.job_id}.json"
            data = {
                "job_id": job.job_id,
                "status": job.status.value if isinstance(job.status, JobStatus) else job.status,
                "total": job.total,
                "processed": job.processed,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
                "expires_at": job.expires_at,
                "model_version": job.model_version,
                "error": job.error.model_dump() if job.error else None,
                "tickets": [t.model_dump() for t in job.tickets],
                "predictions": [p.model_dump() for p in job.predictions],
            }
            with open(job_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _delete_job_from_disk(self, job_id: str):
        """Delete stored job file from disk."""
        try:
            job_file = self._storage_dir / f"{job_id}.json"
            if job_file.exists():
                job_file.unlink()
        except Exception:
            pass

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
                        self._save_job_to_disk(job_to_run)

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
                        now_utc = datetime.now(timezone.utc)
                        job.status = JobStatus.CANCELLED
                        job.finished_at = now_utc.isoformat()
                        job.expires_at = (now_utc + timedelta(hours=settings.JOB_RETENTION_HOURS)).isoformat()
                        self._save_job_to_disk(job)
                    return

                chunk = job.tickets[i : i + batch_size]
                chunk_preds = pipeline.predict_batch(chunk)
                results.extend(chunk_preds)

                with self._lock:
                    job.processed = len(results)

                # Brief yield so other tasks are never starved
                time.sleep(0.005)

            with self._lock:
                now_utc = datetime.now(timezone.utc)
                job.predictions = results
                job.status = JobStatus.SUCCEEDED
                job.finished_at = now_utc.isoformat()
                job.expires_at = (now_utc + timedelta(hours=settings.JOB_RETENTION_HOURS)).isoformat()
                self._save_job_to_disk(job)

        except Exception as exc:
            with self._lock:
                now_utc = datetime.now(timezone.utc)
                job.status = JobStatus.FAILED
                job.finished_at = now_utc.isoformat()
                job.expires_at = (now_utc + timedelta(hours=settings.JOB_RETENTION_HOURS)).isoformat()
                job.error = BatchJobError(code="interrupted", message=str(exc))
                self._save_job_to_disk(job)

    def submit_job(
        self,
        tickets: List[BatchRequestTicket],
        idempotency_key: Optional[str] = None
    ) -> Tuple[Optional[BatchJobStatus], bool, int]:
        """Submit a new job or return existing one if idempotency key matches.

        Returns: (BatchJobStatus, is_existing, http_status_code)
        """
        with self._lock:
            # 1. Idempotency check
            if idempotency_key and idempotency_key in self._idempotency_map:
                existing_id = self._idempotency_map[idempotency_key]
                if existing_id in self._jobs:
                    return self._to_status_schema(self._jobs[existing_id]), True, 202

            # 2. Concurrency checks: max 1 running, max 3 queued (4 active total)
            running_count = sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)
            queued_count = sum(1 for j in self._jobs.values() if j.status == JobStatus.QUEUED)

            if queued_count >= settings.MAX_QUEUED_JOBS or (running_count + queued_count) >= (settings.MAX_CONCURRENT_JOBS + settings.MAX_QUEUED_JOBS):
                return None, False, 429

            # 3. Create job
            job_id = f"job-{uuid.uuid4().hex[:12]}"
            job = JobRecord(job_id=job_id, tickets=tickets, model_version=pipeline.model_version)
            self._jobs[job_id] = job
            self._queue.append(job_id)
            self._save_job_to_disk(job)

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
                try:
                    exp = datetime.fromisoformat(job.expires_at)
                    if datetime.now(timezone.utc) > exp:
                        return None, 410
                except Exception:
                    pass

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
                try:
                    exp = datetime.fromisoformat(job.expires_at)
                    if datetime.now(timezone.utc) > exp:
                        return None, 410
                except Exception:
                    pass

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
        """Cancel a running/queued job or discard a finished job.

        Per OpenAPI spec: Afterwards the job id returns 404.
        Returns HTTP status code.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return 404

            if job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                job.cancelled = True
                job.status = JobStatus.CANCELLED
                now_utc = datetime.now(timezone.utc)
                job.finished_at = now_utc.isoformat()
                job.expires_at = (now_utc + timedelta(hours=settings.JOB_RETENTION_HOURS)).isoformat()

            # Discard job from active map and disk so subsequent requests return 404
            self._jobs.pop(job_id, None)
            self._delete_job_from_disk(job_id)

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

