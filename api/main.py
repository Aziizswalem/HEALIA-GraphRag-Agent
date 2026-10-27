"""FastAPI application factory — lifespan, middleware, routers."""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.audit_log import AuditLogMiddleware
from api.middleware.auth import AuthMiddleware
from api.middleware.pii_filter import PIIFilterMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.routers import chat, copilotkit, health, sessions
from config.settings import get_settings
from observability.langfuse_tracer import shutdown_langfuse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    from graph.client import close_driver

    shutdown_langfuse()
    close_driver()


def create_app() -> FastAPI:
    app = FastAPI(title="GraphRAG Health Insurance API", lifespan=lifespan)
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins() or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)
    if settings.PII_FILTER_ENABLED:
        app.add_middleware(PIIFilterMiddleware)
    app.include_router(health.router, tags=["health"])
    app.include_router(chat.router, tags=["chat"])
    app.include_router(sessions.router, tags=["sessions"])
    copilotkit.register_copilotkit(app, path="/copilotkit")
    return app


app = create_app()
