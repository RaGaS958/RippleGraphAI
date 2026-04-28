"""Disruption event routes — POST triggers the ADK pipeline via EventQueue."""
import uuid, logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.core.auth import get_current_user
from app.models.schemas import DisruptionEvent, DisruptionEventCreate
from app.services.database import Database
from app.services.event_queue import EventQueue
from app.services.websocket_manager import ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=DisruptionEvent, status_code=201)
async def create_event(data: DisruptionEventCreate, background_tasks: BackgroundTasks,
                       _=Depends(get_current_user)):
    """Create event → save to DB → publish to EventQueue → ADK pipeline runs async."""
    eid = str(uuid.uuid4())
    doc = Database.create_event({"id": eid, **data.model_dump()})
    event = DisruptionEvent(**doc)

    # Push to WebSocket immediately so frontend shows new event instantly
    background_tasks.add_task(_trigger, doc)
    return event


async def _trigger(event: dict):
    await ws_manager.broadcast_event(event)
    await EventQueue.publish(event)          # → ADK pipeline runs async


@router.get("/active", response_model=list[DisruptionEvent])
def list_active(limit: int = 50):
    rows = Database.list_active_events(limit)
    return [DisruptionEvent(**r) for r in rows]


@router.get("/", response_model=list[DisruptionEvent])
def list_all(limit: int = 100):
    rows = Database.list_all_events(limit)
    return [DisruptionEvent(**r) for r in rows]


@router.get("/{event_id}", response_model=DisruptionEvent)
def get_event(event_id: str):
    e = Database.get_event(event_id)
    if not e: raise HTTPException(404, "Event not found")
    return DisruptionEvent(**e)


@router.post("/{event_id}/resolve")
def resolve_event(event_id: str, _=Depends(get_current_user)):
    Database.resolve_event(event_id)
    return {"message": "resolved", "event_id": event_id}
