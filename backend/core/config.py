"""Application configuration and environment settings."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    SCHEMAS_DIR: Path = BASE_DIR / "schemas"
    ARTIFACTS_DIR: Path = BASE_DIR / "ml" / "artifacts"
    JOBS_STORAGE_DIR: Path = BASE_DIR / "runtime" / "jobs"

    # API & Authentication
    API_KEY: Optional[str] = os.getenv("API_KEY", None)
    MODEL_VERSION: str = "v1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Limits per OpenAPI specification
    MAX_SYNC_BATCH_ITEMS: int = 100
    MAX_ASYNC_JOB_ITEMS: int = 5000
    MAX_SINGLE_PAYLOAD_BYTES: int = 1 * 1024 * 1024    # 1 MB for /predict
    MAX_SYNC_PAYLOAD_BYTES: int = 5 * 1024 * 1024      # 5 MB for /predict/batch
    MAX_ASYNC_PAYLOAD_BYTES: int = 25 * 1024 * 1024   # 25 MB for /batch/jobs

    # Concurrency & Retention rules
    MAX_CONCURRENT_JOBS: int = 1
    MAX_QUEUED_JOBS: int = 3
    JOB_RETENTION_HOURS: int = 6

    # Model inference settings
    HUMAN_REVIEW_CONFIDENCE_THRESHOLD: float = 0.50

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
