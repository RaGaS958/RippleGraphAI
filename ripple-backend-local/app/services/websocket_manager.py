"""
WebSocket connection manager — replaces Firebase Realtime DB.
Pushes live risk score updates to all connected frontend clients.

Frontend connects to: ws://localhost:8080/ws/live
On connect: receives current snapshot of all risk scores.
On prediction: receives updated node risk scores in real time.
"""
from __future__ import annotations
import asyncio, json, logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WSManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._snapshot: Dict[str, dict] = {}   # latest risk scores per supplier

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        # Send current snapshot immediately on connect
        await ws.send_text(json.dumps({
            "type": "snapshot",
            "data": self._snapshot,
        }))
        logger.info(f"WS connected. Total clients: {len(self._clients)}")

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)
        logger.info(f"WS disconnected. Total clients: {len(self._clients)}")

    async def broadcast_risk_update(self, scores: Dict[str, dict]) -> None:
        """
        Called after each prediction run.
        scores = {supplier_id: {score: float, level: str, peak_day: int}}
        """
        self._snapshot.update(scores)
        if not self._clients:
            return
        msg = json.dumps({"type": "risk_update", "data": scores})
        dead: Set[WebSocket] = set()
        for ws in self._clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    async def broadcast_event(self, event: dict) -> None:
        """Push a new disruption event alert to all clients."""
        if not self._clients:
            return
        msg = json.dumps({"type": "new_event", "data": event})
        dead: Set[WebSocket] = set()
        for ws in self._clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    async def broadcast_prediction_complete(self, result: dict) -> None:
        """Notify frontend that a prediction run finished (triggers demo animation)."""
        if not self._clients:
            return
        msg = json.dumps({"type": "prediction_complete", "data": result})
        dead: Set[WebSocket] = set()
        for ws in self._clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    @property
    def client_count(self) -> int:
        return len(self._clients)


# Singleton shared across all routes
ws_manager = WSManager()
