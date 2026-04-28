# RippleGraph AI — ML/DL (Local, Zero GCP)

No Google Cloud required. Everything runs on your machine.

## Stack

| Was (GCP)         | Now (local)                        |
|-------------------|------------------------------------|
| BigQuery          | SQLite (`data/ripple_graph.db`)    |
| Vertex AI         | `python -m ml.model.train`         |
| Cloud Storage     | `artifacts/` folder                |
| Firebase Realtime | WebSocket at `ws://localhost:8081` |
| Gemini API        | Ollama (local LLM) or template     |

## Quick start

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install torch==2.4.1
pip install torch-geometric==2.6.1 \
  -f https://data.pyg.org/whl/torch-2.4.1+cpu.html
pip install -r requirements.txt

# 2. Run all tests (zero cloud, ~20 seconds)
pytest ml/tests/test_ml.py -v
# All 28 tests should PASS

# 3. Generate mock data + seed SQLite
python -m data.mock.generate_mock_data
# creates data/mock/supply_chain_mock.json

# 4. Start stub prediction server (gives Backend team their URL TODAY)
python -m ml.serving.prediction_server
# http://localhost:8081/health   → {"status":"healthy","mode":"stub"}
# http://localhost:8081/predict  → POST endpoint
# ws://localhost:8081/ws/risk-scores → live WebSocket

# 5. Test prediction endpoint
curl -X POST http://localhost:8081/predict \
  -H "Content-Type: application/json" \
  -d '{
    "graph_nodes":[{"id":"n1","features":[0.2,0.5,0.0,0.6,0.4,0.5,0.6,0.08,0.3,0.0,0.3,0.2,1.0,0.0,0.0,0.0],"tier":"tier_3","risk_score":0.85}],
    "graph_edges":[],
    "trigger_event_id":"test-001"
  }'

# 6. Build graph + train GNN
python -m ml.model.train --epochs 5     # smoke test (fast)
python -m ml.model.train                # full 100 epochs

# 7. After training completes, switch to GNN:
#    Edit configs/ml_config.yaml → serving.stub_mode: false
#    Restart server
python -m ml.serving.prediction_server

# 8. (Optional) Local LLM recommendations
# Install Ollama: https://ollama.com/download
# ollama pull llama3.2
# Edit configs/ml_config.yaml → llm.provider: ollama
```

## File structure

```
ripple-ml-local/
├── configs/ml_config.yaml      ← edit this to tune everything
├── data/
│   └── mock/generate_mock_data.py
├── ml/
│   ├── config.py
│   ├── data/
│   │   ├── database.py         ← SQLite (replaces BigQuery)
│   │   ├── graph_builder.py    ← SQLite → PyG Data
│   │   └── dataset.py          ← train/val/test splits
│   ├── model/
│   │   ├── gnn_model.py        ← RippleGNN architecture
│   │   └── train.py            ← local training loop
│   ├── evaluation/
│   │   └── metrics.py
│   ├── serving/
│   │   ├── prediction_server.py  ← FastAPI + WebSocket
│   │   └── stub_predictor.py     ← rule-based (Week 1)
│   ├── agents/
│   │   └── local_llm_recommender.py  ← Ollama (replaces Gemini)
│   └── tests/
│       └── test_ml.py          ← 28 tests, zero cloud
├── artifacts/                  ← created at runtime
│   ├── graph_data.pt
│   ├── model.pt
│   └── checkpoints/
└── requirements.txt
```

## Contract with Backend team

Backend calls `POST http://localhost:8081/predict` (or the Cloud Run URL if deployed).
Frontend connects to `ws://localhost:8081/ws/risk-scores` for live risk updates.

Request body:
```json
{
  "graph_nodes": [{"id":"uuid","features":[16 floats],"tier":"tier_3","risk_score":0.0}],
  "graph_edges": [{"source":"uuid","target":"uuid","features":[6 floats],"dependency_weight":0.8}],
  "trigger_event_id": "event-uuid",
  "horizon_days": 45
}
```

Response:
```json
{
  "predictions": {"<supplier_id>": {"risk_scores":[45 floats],"peak_risk_score":0.87,"risk_level":"critical"}},
  "model_version": "gnn-v1",
  "inference_ms": 18.4
}
```

The stub returns `confidence: 0.60`, the trained GNN returns `confidence: 0.85`.
Backend can use this to show judges "model upgraded" in the demo.
