import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, get_db, SessionLocal
from app.rate_limiter import check_rate_limit
from app.routers import auth, billing, lessons, conversation, vocabulary, progress, usage, analytics

logger = logging.getLogger("texted.api")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify DB connectivity on startup
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully.")
    except Exception as exc:
        logger.error("Database connection check failed on startup: %s", exc)
    yield


app = FastAPI(
    title="Texted API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

# Production CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)


@app.middleware("http")
async def rate_limit_and_error_middleware(request: Request, call_next):
    # 1. Rate Limiting Check
    try:
        check_rate_limit(request)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        raise exc

    # 2. Execute request with sanitized error handling
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled application error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Something went wrong. Please try again later."},
        )


# Include Routers
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(conversation.router)
app.include_router(usage.router)
app.include_router(analytics.router)
app.include_router(lessons.router)
app.include_router(vocabulary.router)
app.include_router(progress.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/ready")
def readiness():
    """Readiness probe verifying DB connection."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "unreachable"},
        )
