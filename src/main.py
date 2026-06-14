"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.ioc.providers import AppProvider
from config.logging import setup_logging
from config.settings import settings
from presentation.api.v1.exceptions import register_exception_handlers
from presentation.api.v1.router import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await app.state.dishka_container.close()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    container = make_async_container(AppProvider())
    setup_dishka(container, app)

    register_exception_handlers(app)
    app.include_router(v1_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
