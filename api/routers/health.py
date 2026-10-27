from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from observability.prometheus_metrics import render_metrics

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    return {"ready": True}


@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")
