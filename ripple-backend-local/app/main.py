"""
RippleGraph AI — Backend (local, zero cloud)
FastAPI app wiring DB, EventQueue, ADK pipeline, WebSocket.

Start:
  uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.services.database import Database
from app.services.event_queue import EventQueue
from app.agents.adk_pipeline import handle_disruption_event
from app.api.routes import health, auth, suppliers, events, predictions, graph, websocket
from app.api.routes import agent        # ADK agent chat route
from app.api.routes import simulation   # Simulation injection route  ← NEW

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    Database.init()
    EventQueue.register_handler(handle_disruption_event)
    await EventQueue.start_worker()
    yield
    await EventQueue.stop_worker()


app = FastAPI(
    title="RippleGraph AI API",
    description="Supply chain disruption prediction — ADK multi-agent + GNN",
    version="2.0.0",
    lifespan=lifespan,
)

cfg = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=cfg.ALLOWED_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health.router,      prefix="/api/v1",              tags=["health"])
app.include_router(auth.router,        prefix="/api/v1/auth",         tags=["auth"])
app.include_router(suppliers.router,   prefix="/api/v1/suppliers",    tags=["suppliers"])
app.include_router(events.router,      prefix="/api/v1/events",       tags=["events"])
app.include_router(predictions.router, prefix="/api/v1/predictions",  tags=["predictions"])
app.include_router(graph.router,       prefix="/api/v1/graph",        tags=["graph"])
app.include_router(agent.router,       prefix="/api/v1/agent",        tags=["agent"])
app.include_router(simulation.router,  prefix="/api/v1/simulation",   tags=["simulation"])  # ← NEW
app.include_router(websocket.router,   prefix="/ws",                  tags=["websocket"])


@app.get("/")
def root():
    return {
        "service": "RippleGraph AI Backend",
        "version": "2.0.0",
        "agents":  ["MonitorAgent", "AnalystAgent", "RecommenderAgent"],
        "mode":    "adk" if __import__("app.agents.adk_pipeline", fromlist=["pipeline"]).pipeline._adk_ready else "fallback",
    }