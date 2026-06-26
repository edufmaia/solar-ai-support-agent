from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import router as admin_router
from .api.chat import router as chat_router
from .api.chatwoot import router as chatwoot_router
from .api.conversations import router as conversations_router
from .api.health import router as health_router
from .api.metrics import router as metrics_router

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Solar AI Support Agent",
        description="Minimal API bootstrap for the Solar AI Support Agent project.",
        version="0.1.0",
    )
    app.include_router(chat_router)
    app.include_router(chatwoot_router)
    app.include_router(conversations_router)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(admin_router)

    if STATIC_DIR.is_dir():
        app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="ui")

        @app.get("/", include_in_schema=False)
        def root() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

    return app


app = create_app()
