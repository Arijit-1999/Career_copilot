"""FastAPI Application Entrypoint and Lifespan Configuration."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import AppBaseException, EntityNotFoundException, ValidationException
from app.api.health import router as health_router
from app.api.v1.router import api_v1_router

# Initialize structured logging
setup_logging()
logger = get_logger("career_copilot")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.app_name} in [{settings.app_env}] environment")
    
    # Auto-synchronize tables on startup if database is accessible
    try:
        from app.common.models import Base
        from app.core.database import engine
        import app.candidate.models  # Register candidate tables
        import app.career_profiles.models  # Register career profile tables
        import app.jobs.models  # Register jobs tables
        import app.matching.models  # Register matching tables
        import app.resumes.models  # Register resumes tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema synchronized successfully")
    except Exception as exc:
        logger.warning(f"Database schema auto-sync skipped/failed: {exc}")

    yield
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.app_name,
        description="Personal AI Career Assistant for smart job discovery, matching, resume tailoring, and tracking.",
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    @app.exception_handler(EntityNotFoundException)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundException):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not Found", "message": exc.message, "details": exc.details}
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Validation Error", "message": exc.message, "details": exc.details}
        )

    @app.exception_handler(AppBaseException)
    async def app_base_exception_handler(request: Request, exc: AppBaseException):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Bad Request", "message": exc.message, "details": exc.details}
        )

    from fastapi.responses import HTMLResponse, FileResponse
    from pathlib import Path

    # Include health endpoints and API routers
    app.include_router(health_router, prefix="/api")
    app.include_router(api_v1_router, prefix="/api")

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    @app.get("/dashboard", include_in_schema=False, response_class=HTMLResponse)
    async def root_dashboard():
        """Serves the Developer Control Center & Visual Testing UI."""
        frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "index.html"
        if frontend_path.exists():
            return FileResponse(frontend_path, media_type="text/html")
        return HTMLResponse("<h1>Career Copilot API is running.</h1><p>Visit <a href='/docs'>/docs</a> for Swagger.</p>")

    return app


app = create_app()
