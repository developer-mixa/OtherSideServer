"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from application.bootstrap import bootstrap_admin_user
from config.ioc.providers import AppProvider
from config.logging import setup_logging
from config.settings import settings
from presentation.api.v1.exceptions import register_exception_handlers
from presentation.api.v1.router import router as v1_router
from presentation.middleware.maintenance import MaintenanceMiddleware
from presentation.middleware.rate_limit import RateLimitMiddleware
from presentation.middleware.security_headers import SecurityHeadersMiddleware


def _make_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # One-shot engine, disposed right after bootstrap so its pool doesn't sit
    # open and unused for the app's whole lifetime.
    bootstrap_engine = _make_engine()
    try:
        session_factory = async_sessionmaker(bootstrap_engine, expire_on_commit=False)
        await bootstrap_admin_user(session_factory)
    finally:
        await bootstrap_engine.dispose()
    yield
    await app.state.dishka_container.close()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/api/docs" if settings.is_local else None,
        redoc_url="/api/redoc" if settings.is_local else None,
        openapi_url="/api/openapi.json" if settings.is_local else None,
        lifespan=lifespan,
    )

    # Own engine per create_app() call (not the module-level infrastructure.db.session
    # singleton): create_app() is invoked once per test in the API test suite, each
    # under its own event loop, so a shared pooled asyncpg connection would end up bound
    # to the wrong loop across tests. In production create_app() is called once per
    # worker process, so this is a single extra pool per worker, not per request.
    maintenance_session_factory = async_sessionmaker(_make_engine(), expire_on_commit=False)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        # Auth is a Bearer token in the Authorization header, never a cookie, so
        # credentialed CORS is unnecessary attack surface. Keeping it False also
        # avoids the wildcard-origin + credentials combination outright.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        # Browsers hide every response header cross-origin unless it is listed here,
        # and the client needs Retry-After to say how long the cooldown has left.
        expose_headers=["Retry-After"],
    )
    app.add_middleware(MaintenanceMiddleware, session_factory=maintenance_session_factory)

    container = make_async_container(AppProvider())
    setup_dishka(container, app)

    register_exception_handlers(app)
    app.include_router(v1_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
