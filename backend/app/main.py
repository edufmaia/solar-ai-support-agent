from fastapi import FastAPI

from .api.chat import router as chat_router
from .api.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Solar AI Support Agent",
        description="Minimal API bootstrap for the Solar AI Support Agent project.",
        version="0.1.0",
    )
    app.include_router(chat_router)
    app.include_router(health_router)

    return app


app = create_app()
