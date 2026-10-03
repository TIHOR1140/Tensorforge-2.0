"""Asynchronous batch jobs endpoints for large evaluations (1 to 5,000 tickets)."""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from backend.api.dependencies import verify_api_key, get_request_id
from backend.core.constants import JobStatus
from backend.schemas.batch_jobs import (
    BatchJobRequest,
    BatchJobStatus,
    BatchJobResults,
)
from backend.services.job_manager import job_manager

router = APIRouter(prefix="/batch/jobs", tags=["Evaluation"])


@router.post(
    "",
    response_model=BatchJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a large batch as an asynchronous job",
    description="Submit 1 to 5,000 tickets for background evaluation. Requires API key."
)
async def submit_batch_job(
    request: BatchJobRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    request_id: Optional[str] = Depends(get_request_id),
    _api_key: str = Depends(verify_api_key),
) -> BatchJobStatus:
    if request_id:
        response.headers["X-Request-ID"] = request_id

    job_status, _is_existing, code = job_manager.submit_job(
        tickets=request.tickets,
        idempotency_key=idempotency_key
    )

    if code == 429:
        response.headers["Retry-After"] = "10"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Too many active or queued jobs. Try again later."}
        )

    response.status_code = status.HTTP_202_ACCEPTED
    response.headers["Location"] = f"/batch/jobs/{job_status.job_id}"
    response.headers["Retry-After"] = "5"
    return job_status


@router.get(
    "/{job_id}",
    response_model=BatchJobStatus,
    summary="Poll job status",
    description="Poll progress and status of an asynchronous job. Requires API key."
)
async def get_job_status(
    job_id: str,
    response: Response,
    request_id: Optional[str] = Depends(get_request_id),
    _api_key: str = Depends(verify_api_key),
) -> BatchJobStatus:
    if request_id:
        response.headers["X-Request-ID"] = request_id

    job_status, code = job_manager.get_job_status(job_id)

    if code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": f"Job '{job_id}' not found."}
        )
    if code == 410:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "expired", "message": f"Job '{job_id}' has expired and was discarded."}
        )

    # If job is still queued or running, supply Retry-After header
    if job_status.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
        response.headers["Retry-After"] = "3"

    return job_status


@router.get(
    "/{job_id}/results",
    response_model=BatchJobResults,
    summary="Fetch results once the job is complete",
    description="Fetch paginated predictions from a succeeded job. Requires API key."
)
async def get_job_results(
    job_id: str,
    response: Response,
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Items per page"),
    request_id: Optional[str] = Depends(get_request_id),
    _api_key: str = Depends(verify_api_key),
) -> BatchJobResults:
    if request_id:
        response.headers["X-Request-ID"] = request_id

    results, code = job_manager.get_job_results(job_id=job_id, offset=offset, limit=limit)

    if code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": f"Job '{job_id}' not found."}
        )
    if code == 410:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "expired", "message": f"Job '{job_id}' results have expired."}
        )
    if code == 409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "conflict", "message": f"Job '{job_id}' is not yet completed."}
        )

    return results


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel or discard job",
    description="Cancels a running job or discards a finished one. Requires API key."
)
async def cancel_or_discard_job(
    job_id: str,
    response: Response,
    request_id: Optional[str] = Depends(get_request_id),
    _api_key: str = Depends(verify_api_key),
):
    if request_id:
        response.headers["X-Request-ID"] = request_id

    code = job_manager.cancel_or_discard_job(job_id)
    if code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": f"Job '{job_id}' not found."}
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
