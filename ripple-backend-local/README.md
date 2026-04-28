# RippleGraph AI — Backend (Local, Zero Cloud)

FastAPI backend with SQLite, local JWT auth, in-memory event queue,
WebSocket for live updates, and ADK-style 3-agent pipeline.

## What replaced what

| Was (Cloud)           | Now (Local)                             |
|-----------------------|-----------------------------------------|
| Firestore             | SQLite (`data/ripple_backend.db`)       |
| BigQuery              | SQLite analytics queries                |
| Firebase Auth         | Local JWT (python-jose + passlib)       |
| Pub/Sub               | asyncio.Queue (EventQueue)              |
| Firebase Realtime DB  | WebSocket at `ws://localhost:8080/ws/live` |
| Vertex AI             | HTTP call to ML server at port 8081     |

## Quick start

```bash
cd ripple-backend-local

# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Generate mock data (shared with ML team)
python data/mock/generate_mock_data.py

# 3. Seed database
python scripts/seed_db.py

# 4. Run tests (zero cloud, ~10 seconds)
pytest tests/ -v
# All 30 tests should PASS

# 5. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 6. Verify
curl http://localhost:8080/
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/graph/
curl http://localhost:8080/api/v1/suppliers/
```

## API reference

### Auth
```
POST /api/v1/auth/register   {"email":"...","password":"...","name":"..."}
POST /api/v1/auth/login      {"email":"...","password":"..."}
GET  /api/v1/auth/me         (requires Bearer token)
```

### Core routes
```
GET  /api/v1/suppliers/              list all suppliers
GET  /api/v1/suppliers/?tier=tier_3  filter by tier
GET  /api/v1/suppliers/{id}          get one supplier
POST /api/v1/suppliers/              create (auth required)

GET  /api/v1/events/active           list active disruption events
GET  /api/v1/events/                 list all events
GET  /api/v1/events/{id}             get one event
POST /api/v1/events/                 create + trigger ADK pipeline (auth required)
POST /api/v1/events/{id}/resolve     mark resolved (auth required)

GET  /api/v1/graph/                  full supply chain graph (nodes + edges)

GET  /api/v1/predictions/summary     risk KPI summary
GET  /api/v1/predictions/tier-breakdown  risk by tier
GET  /api/v1/predictions/event/{id}  predictions for a specific event

WS   /ws/live                        live risk score stream
```

## How the pipeline works

```
POST /api/v1/events/
  → DB.create_event()
  → EventQueue.publish(event)
        ↓ (async worker)
  → ADKPipeline.run(event)
      → MonitorAgent   — validates + enriches from DB
      → AnalystAgent   — calls ML server (localhost:8081/predict)
          → if ML down: rule-based fallback
      → RecommenderAgent — calls Ollama / template fallback
  → DB.save_prediction()
  → DB.update_supplier_risk() for all nodes
  → WebSocket.broadcast_risk_update() → 3D graph updates in real time
  → WebSocket.broadcast_prediction_complete() → frontend shows recommendations
```

## WebSocket messages (frontend listens to ws://localhost:8080/ws/live)

```json
// On connect — current snapshot
{"type": "snapshot", "data": {"supplier_id": {"score": 0.87, "level": "critical", "peak_day": 7}}}

// After each prediction
{"type": "risk_update", "data": {"supplier_id": {"score": 0.85, "level": "critical", "peak_day": 7}}}

// New disruption event created
{"type": "new_event", "data": {DisruptionEvent}}

// Prediction pipeline complete
{"type": "prediction_complete", "data": {
  "event_id": "...", "urgency": "CRITICAL",
  "critical": 3, "high": 8, "revenue": 2300000000,
  "recommendations": ["Activate backup suppliers...", ...]
}}
```

## File structure

```
ripple-backend-local/
├── app/
│   ├── main.py                       ← FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py                 ← all settings
│   │   ├── auth.py                   ← JWT helpers + dependency
│   │   └── logging.py
│   ├── models/
│   │   └── schemas.py                ← all Pydantic models
│   ├── services/
│   │   ├── database.py               ← SQLite (replaces Firestore+BQ)
│   │   ├── event_queue.py            ← asyncio.Queue (replaces Pub/Sub)
│   │   ├── websocket_manager.py      ← WS (replaces Firebase Realtime DB)
│   │   └── ml_client.py              ← HTTP client to ML server
│   ├── agents/
│   │   ├── pipeline.py               ← Monitor → Analyst → Recommender
│   │   └── local_llm_recommender.py  ← Ollama / template
│   └── api/routes/
│       ├── health.py
│       ├── auth.py
│       ├── suppliers.py
│       ├── events.py
│       ├── predictions.py
│       ├── graph.py
│       └── websocket.py
├── tests/
│   └── test_backend.py               ← 30 tests, zero cloud
├── scripts/
│   └── seed_db.py
├── data/mock/
│   └── generate_mock_data.py
└── requirements.txt
```

## Running with ML team (full system)

```bash
# Terminal 1 — ML prediction server
cd ripple-ml-local && python -m ml.serving.prediction_server
# http://localhost:8081

# Terminal 2 — Backend
cd ripple-backend-local && uvicorn app.main:app --port 8080 --reload
# http://localhost:8080

# Terminal 3 — Frontend (when ready)
cd ripple-frontend && npm run dev
# http://localhost:5173
```
