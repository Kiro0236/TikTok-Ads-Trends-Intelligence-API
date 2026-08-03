"""FastAPI application factory."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.exceptions.handlers import register_exception_handlers
from app.routers import ads, trends

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        description=(
            "Discover winning TikTok advertisements and analyze competitor "
            "campaigns. Returns clean, normalized JSON derived from the "
            "configured data provider.\n\n"
            "**Note:** this deployment runs in `mock` data-provider mode "
            "by default, returning realistic sample data so the API can "
            "be explored and integrated against before a live data "
            "source is connected."
        ),
        contact={"name": "API Support"},
    )

    # CORS: open to any origin so requests work from the RapidAPI testing
    # console (and any frontend consumers) directly in the browser.
    # allow_credentials must stay False when allow_origins is "*" per the
    # CORS spec — this API is header-based (RapidAPI proxy secret), not
    # cookie-based, so that's not a limitation here.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(ads.router)
    app.include_router(trends.router)

    @app.get("/health", tags=["Health"], summary="Health check")
    async def health() -> dict:
        return {"status": "ok", "provider_mode": settings.data_provider_mode}

    return app


app = create_app()
