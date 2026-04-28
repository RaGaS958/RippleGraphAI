"""Health check routes."""
import logging
from datetime import datetime
from fastapi import APIRouter
from app.services.database import Database
from app.services.ml_client import MLClient
from app.services.websocket_manager import ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    db_ok = False
    try:
        stats = Database.stats()
        db_ok = True
    except Exception:
        stats = {}

    ml_ok = await MLClient().is_reachable()

    return {
        "status":             "healthy",
        "version":            "1.0.0",
        "timestamp":          datetime.utcnow().isoformat(),
        "db_connected":       db_ok,
        "ml_server_reachable":ml_ok,
        "ws_clients":         ws_manager.client_count,
        "db_stats":           stats,
    }

@router.get("/health/ready")
async def ready():
    return {"status": "ready"}

@router.get("/health/live")
async def live():
    return {"status": "alive"}
