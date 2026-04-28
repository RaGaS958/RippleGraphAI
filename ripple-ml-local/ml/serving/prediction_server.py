"""
Local prediction server — FastAPI + WebSocket.
Replaces Vertex AI endpoint + Firebase Realtime DB.

Endpoints:
  GET  /health           — status
  POST /predict          — batch GNN/stub prediction
  WS   /ws/risk-scores   — live risk score stream (replaces Firebase Realtime DB)

Run:
  python -m ml.serving.prediction_server
  # or
  uvicorn ml.serving.prediction_server:app --host 0.0.0.0 --port 8081
"""
from __future__ import annotations
import asyncio, json, logging, time
from pathlib import Path
from typing import Dict, List, Optional, Set

import torch
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ml.config import get_config
from ml.model.gnn_model import RippleGNN
from ml.serving.stub_predictor import StubPredictor, NodePrediction

logger = logging.getLogger(__name__)

_model:  Optional[RippleGNN] = None
_stub:   Optional[object]    = None
_device: torch.device        = torch.device("cpu")
_ws_clients: Set[WebSocket]  = set()
_latest_scores: dict         = {}


# ── Schemas ────────────────────────────────────────────────────────────────────

class NodeInput(BaseModel):
    id: str
    features: List[float] = Field(..., min_length=16, max_length=16)
    tier: str = "tier_2"
    risk_score: float = 0.0

class EdgeInput(BaseModel):
    source: str; target: str
    features: List[float] = Field(default_factory=lambda: [0.0]*6)
    dependency_weight: float = 0.5
    is_sole_source: bool = False

class PredictionRequest(BaseModel):
    graph_nodes: List[NodeInput]
    graph_edges: List[EdgeInput] = []
    trigger_event_id: str
    horizon_days: int = 45

class PredictionResponse(BaseModel):
    predictions: Dict[str, NodePrediction]
    trigger_event_id: str
    model_version: str
    inference_ms: float
    affected_count: int

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────────
    global _model, _stub, _device
    cfg = get_config()
    art = Path(cfg.serving.model_artifact_path)

    if cfg.serving.stub_mode or not art.exists():
        from ml.serving.stub_predictor import StubPredictor
        _stub = StubPredictor()
        logger.info("Loaded STUB predictor")
    else:
        ckpt    = torch.load(str(art), map_location="cpu", weights_only=False)
        _model  = RippleGNN(ckpt["gnn_config"])
        _model.load_state_dict(ckpt["model_state_dict"])
        _model.eval()
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _model  = _model.to(_device)
        logger.info(f"Loaded GNN model on {_device}")
    yield

app = FastAPI(title="RippleGNN Local Server", version="1.0.0", lifespan=lifespan)

# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "mode": "stub" if _stub else "gnn",
        "model_loaded": _model is not None or _stub is not None,
        "ws_clients": len(_ws_clients),
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(req: PredictionRequest):
    t0 = time.time()

    if _stub:
        predictions = _stub.predict(req)
        version     = "stub-v0"
    else:
        predictions = _gnn_predict(req)
        version     = "gnn-v1"

    # Push updated scores to all WebSocket clients
    scores = {nid: {"score": p.peak_risk_score, "level": p.risk_level}
              for nid, p in predictions.items()}
    _latest_scores.update(scores)
    asyncio.create_task(_broadcast({"type": "risk_update", "scores": scores}))

    return PredictionResponse(
        predictions=predictions,
        trigger_event_id=req.trigger_event_id,
        model_version=version,
        inference_ms=round((time.time()-t0)*1000, 2),
        affected_count=sum(1 for p in predictions.values() if p.peak_risk_score >= 0.4),
    )


def _gnn_predict(req: PredictionRequest) -> Dict[str, NodePrediction]:
    from torch_geometric.data import Data
    id_to_idx = {n.id: i for i, n in enumerate(req.graph_nodes)}
    x = torch.tensor([n.features for n in req.graph_nodes], dtype=torch.float)
    srcs, tgts, ea = [], [], []
    for e in req.graph_edges:
        if e.source in id_to_idx and e.target in id_to_idx:
            srcs.append(id_to_idx[e.source]); tgts.append(id_to_idx[e.target])
            ea.append(e.features)
    edge_index = torch.tensor([srcs, tgts], dtype=torch.long) if srcs else torch.zeros((2,0),dtype=torch.long)
    edge_attr  = torch.tensor(ea, dtype=torch.float) if ea else torch.zeros((0,6),dtype=torch.float)
    data = Data(x=x.to(_device), edge_index=edge_index.to(_device),
                edge_attr=edge_attr.to(_device), num_nodes=len(req.graph_nodes))
    with torch.no_grad():
        preds = _model(data.x, data.edge_index, data.edge_attr)
    result = {}
    for i, node in enumerate(req.graph_nodes):
        scores = preds[i, :req.horizon_days].cpu().tolist()
        peak   = max(scores)
        result[node.id] = NodePrediction(
            risk_scores=scores, peak_risk_score=round(peak,4),
            peak_risk_day=int(scores.index(peak)),
            risk_level=_level(peak), confidence=0.85,
        )
    return result


def _level(s):
    if s >= 0.70: return "critical"
    if s >= 0.40: return "high"
    if s >= 0.20: return "medium"
    return "low"


# ── WebSocket — replaces Firebase Realtime DB ──────────────────────────────────

@app.websocket("/ws/risk-scores")
async def ws_risk_scores(ws: WebSocket):
    """
    Frontend connects here instead of Firebase Realtime DB.
    On connect: sends current scores snapshot.
    On each prediction: broadcasts updated scores.
    """
    await ws.accept()
    _ws_clients.add(ws)
    logger.info(f"WS client connected. Total: {len(_ws_clients)}")
    try:
        # Send current snapshot immediately on connect
        await ws.send_text(json.dumps({"type": "snapshot", "scores": _latest_scores}))
        # Keep alive — client drives the connection
        while True:
            await asyncio.sleep(30)
            await ws.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)
        logger.info(f"WS client disconnected. Total: {len(_ws_clients)}")


async def _broadcast(msg: dict):
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


if __name__ == "__main__":
    import uvicorn, sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s — %(message)s")
    cfg = get_config()
    uvicorn.run(app, host=cfg.serving.host, port=cfg.serving.port)