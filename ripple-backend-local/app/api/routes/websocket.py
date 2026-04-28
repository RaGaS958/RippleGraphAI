"""WebSocket endpoint — replaces Firebase Realtime DB."""
import asyncio, logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/live")
async def ws_live(ws: WebSocket):
    """
    Frontend connects here for live risk score updates.
    ws://localhost:8080/ws/live

    Message types received by frontend:
      {type: "snapshot",           data: {supplier_id: {score, level, peak_day}}}
      {type: "risk_update",        data: {supplier_id: {score, level, peak_day}}}
      {type: "new_event",          data: DisruptionEvent}
      {type: "prediction_complete",data: {event_id, urgency, critical, high, revenue, recommendations}}
      {type: "ping"}
    """
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep connection alive — heartbeat every 30s
            await asyncio.sleep(30)
            try:
                import json
                await ws.send_text(json.dumps({"type": "ping"}))
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WS closed: {e}")
    finally:
        ws_manager.disconnect(ws)
