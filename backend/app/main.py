from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import initialize_database
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.routes.auth import router as auth_router
from app.routers.api import router as api_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.reports import router as reports_router
from app import models as _models  # noqa: F401

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title=settings.app_name, version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(reports_router)
    app.include_router(dashboard_router)
    app.include_router(api_router)

    @app.on_event("startup")
    async def startup() -> None:
        await initialize_database()

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database request failed", exc_info=exc)
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled application error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
