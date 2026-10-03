"""Main FastAPI application initialization and configuration."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import settings
from src.models.pipeline import pipeline
from src.api.routes import health, predict, batch_jobs
from src.api.error_handlers import (
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load ML models and warmup pipeline
    pipeline.load()
    yield
    # Shutdown logic if any


def create_app() -> FastAPI:
    app = FastAPI(
        title="TensorForge 2.0 Support Ticket API",
        version=settings.MODEL_VERSION,
        description="Ticket classification and routing system for RideEat platform.",
        lifespan=lifespan,
    )

    # Register centralized error handlers strictly adhering to JSON Schema
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Payload size and content-type enforcement middleware
    @app.middleware("http")
    async def validate_request_middleware(request: Request, call_next):
        # Exclude GET/DELETE and UI routes from content-type enforcement
        if request.method == "POST" and not request.url.path.startswith("/static"):
            content_type = request.headers.get("content-type", "")
            if "application/json" not in content_type:
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error": {
                            "code": "unsupported_media_type",
                            "message": "Content-Type must be 'application/json'.",
                        }
                    },
                )

            # Check payload size
            content_length = request.headers.get("content-length")
            if content_length:
                length = int(content_length)
                max_bytes = (
                    settings.MAX_ASYNC_PAYLOAD_BYTES
                    if request.url.path.startswith("/batch/jobs")
                    else settings.MAX_SYNC_PAYLOAD_BYTES
                )
                if length > max_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "payload_too_large",
                                "message": f"Payload size exceeds allowed limit of {max_bytes // (1024 * 1024)} MB.",
                            }
                        },
                    )

        response = await call_next(request)
        return response

    # Include API routers
    app.include_router(health.router)
    app.include_router(predict.router)
    app.include_router(batch_jobs.router)

    # Serve static assets and interactive demo UI
    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    static_dir = ui_dir / "static"
    templates_dir = ui_dir / "templates"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        index_file = templates_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"message": "TensorForge 2.0 API is running. Visit /docs for OpenAPI UI."})

    return app


app = create_app()
