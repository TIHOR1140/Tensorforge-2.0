import json
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


from backend.core.config import settings
from backend.models.pipeline import pipeline
from backend.api.routes import health, predict, batch_jobs
from backend.api.error_handlers import (
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)

# Resolve frontend build directory (project root / frontend / dist)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"


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

    # --- Middleware ---

    # Enforce exact OpenAPI check ordering: Auth (401) -> Content-Type (415) -> Size (413) -> JSON Parse (400) -> Validation (422)
    # Also guarantee X-Request-ID is echoed on all responses (success and error)
    @app.middleware("http")
    async def request_pipeline_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        path = request.url.path

        # Determine if route is a protected API endpoint
        is_protected_api = (
            path.startswith("/predict") or
            path.startswith("/batch/jobs")
        )

        if is_protected_api:
            # 1. Check Auth (401)
            expected_key = settings.API_KEY
            provided_key = None
            x_api_key = request.headers.get("x-api-key")
            auth_header = request.headers.get("authorization")

            if x_api_key:
                provided_key = x_api_key.strip()
            elif auth_header and auth_header.lower().startswith("bearer "):
                provided_key = auth_header[7:].strip()

            if not expected_key or not provided_key or not secrets.compare_digest(provided_key, expected_key):
                resp = JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": {
                            "code": "unauthorized",
                            "message": "Invalid or missing API key.",
                        }
                    },
                    headers={"WWW-Authenticate": "Bearer", "X-Request-ID": request_id}
                )
                return resp

            # 2. For POST requests: Content-Type check (415)
            if request.method == "POST":
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
                        headers={"X-Request-ID": request_id}
                    )

                # 3. Payload size check (413)
                if path.startswith("/batch/jobs"):
                    max_bytes = settings.MAX_ASYNC_PAYLOAD_BYTES
                elif path.startswith("/predict/batch"):
                    max_bytes = settings.MAX_SYNC_PAYLOAD_BYTES
                else:
                    max_bytes = settings.MAX_SINGLE_PAYLOAD_BYTES

                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "payload_too_large",
                                "message": f"Payload size exceeds allowed limit of {max_bytes // (1024 * 1024)} MB.",
                            }
                        },
                        headers={"X-Request-ID": request_id}
                    )

                # Read body stream and verify size & JSON syntax
                body = await request.body()
                if len(body) > max_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "payload_too_large",
                                "message": f"Payload size exceeds allowed limit of {max_bytes // (1024 * 1024)} MB.",
                            }
                        },
                        headers={"X-Request-ID": request_id}
                    )

                # 4. JSON parse check (400)
                try:
                    import json
                    json.loads(body.decode("utf-8"))
                except Exception:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error": {
                                "code": "malformed_json",
                                "message": "Request body is not valid JSON.",
                            }
                        },
                        headers={"X-Request-ID": request_id}
                    )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


    # Include API routers
    app.include_router(health.router)
    app.include_router(predict.router)
    app.include_router(batch_jobs.router)

    # Serve React frontend build output from frontend/dist/
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"message": "TensorForge 2.0 API is running. Visit /docs for OpenAPI UI."})

    return app


app = create_app()
