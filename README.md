<div align="center">

<img src="https://img.shields.io/badge/RippleGraph-AI-6366f1?style=for-the-badge&logoColor=white" alt="RippleGraph AI"/>

# 🌐 RippleGraph AI
### *Supply Chain Disruption Prediction — Before the Ripple Becomes a Wave*

[![Hackathon 2024](https://img.shields.io/badge/Hackathon-2024-gold?style=flat-square&logo=trophy)](.)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](.)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](.)
[![React](https://img.shields.io/badge/React-18+TypeScript-61DAFB?style=flat-square&logo=react)](.)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4-EE4C2C?style=flat-square&logo=pytorch)](.)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?style=flat-square&logo=google)](.)
[![Three.js](https://img.shields.io/badge/Three.js-3D%20Globe-black?style=flat-square&logo=threedotjs)](.)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](.)

**A full-stack AI platform that predicts cascade disruptions across 29-node supplier networks — 45 days ahead — using GraphSAGE GNN, a multi-agent Google ADK pipeline, and a real-time 3D Earth visualization.**

### 🔗 Live Deployments

| Service | URL | Status |
|---------|-----|--------|
| 🖥️ **Frontend** | [ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/) | Vercel |
| 🧠 **ML / GNN Server** | [ragas111-rippleai-ml.hf.space](https://ragas111-rippleai-ml.hf.space/) | Hugging Face Spaces |
| ⚡ **Backend API** | [ripplegraphai-1.onrender.com](https://ripplegraphai-1.onrender.com/) | Render |

[🚀 Quick Start](#-quick-start) · [🏗️ Architecture](#️-system-architecture) · [🤖 AI Pipeline](#-multi-agent-ai-pipeline) · [🧠 ML Model](#-graphsage-gnn) · [📊 Analytics](#-analytics--stats) · [🎬 Demo](#-mvp--demo)

</div>

---

## 📌 The Problem

> *"Most companies only detect disruptions **after** production has already been affected."*

```
$4.4T  ──── Annual cost of global supply chain disruptions
 23%   ──── Companies with zero real-time sub-tier visibility  
3–8wk  ──── Avg time from Tier-3 disruption → OEM production impact
  0    ──── Existing tools with AI-powered cascade graph prediction
```

Traditional ERPs track inventory. They cannot model **how risk propagates** through a multi-tier supplier graph. RippleGraph AI does.

---

## ✨ Key Stats & Metrics

<div align="center">

| 🎯 Metric | 📊 Value | 📝 Detail |
|-----------|----------|-----------|
| **GNN Confidence** | **94.2%** | Held-out test split |
| **Prediction Horizon** | **45 days** | Per-node daily risk score |
| **Supplier Nodes** | **29** | Real lat/lon pinned on 3D globe |
| **Crisis Scenarios** | **6** | TSMC, Rare Earth, Port Strike, Flood, Recall, Nominal |
| **API Endpoints** | **12** | REST + 1 WebSocket channel |
| **Agent Pipeline** | **3 agents** | Monitor → Analyst → Recommender |
| **DB Tables** | **5** | Users, Suppliers, Edges, Events, Predictions |
| **Frontend Routes** | **8** | Including live 3D globe + AI chat |
| **GNN Layers** | **3** | GraphSAGE + skip connections + BatchNorm |
| **Model Size** | **~848 KB** | Lightweight, runs fully offline |

</div>

---

## 🚀 Quick Start

> ⚠️ **IMPORTANT — Services must be started in this exact order:**
>
> **Step 1 → ML Server first** → **Step 2 → Backend second** → **Step 3 → Frontend last**
>
> The backend depends on the ML server being ready. The frontend depends on the backend being ready.

---

### ☁️ Option A — Use Live Deployments (Recommended — No Setup Required)

> **Follow this warm-up order to avoid cold-start timeouts:**

#### 1️⃣ Wake Up the ML Server
Open the ML server first and wait for it to fully load (Hugging Face Spaces may take ~30–60 seconds on a cold start):

👉 **[https://ragas111-rippleai-ml.hf.space/](https://ragas111-rippleai-ml.hf.space/)**

Wait until you see a `{"status":"ok"}` or health response before proceeding.

#### 2️⃣ Wake Up the Backend
Open the backend API — Render free tier may take ~30–60 seconds to spin up:

👉 **[https://ripplegraphai-1.onrender.com/](https://ripplegraphai-1.onrender.com/)**

You can verify it's healthy at:
```
https://ripplegraphai-1.onrender.com/api/v1/health
```

#### 3️⃣ Open the Frontend
Once both services are running, open the app:

👉 **[https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/)**

---

### 🖥️ Option B — Run Locally

#### Prerequisites

```
Python 3.11+   Node 18+   Git
Optional: GEMINI_API_KEY (falls back to rule-based without it)
```

#### Clone the Repo

```bash
git clone https://github.com/RaGaS958/RippleGraphAI.git
cd RippleGraphAI
```

#### Step 1 — Start ML Server First (Port 8081)

> 🔴 **Must be running before the backend starts.**

```bash
cd ripple-ml-local
pip install -r requirements.txt
python -m ml.serving.prediction_server
# Serves GraphSAGE model from artifacts/model.pt
# Wait for: "ML server running on :8081" before proceeding
```

Verify it's up:
```bash
curl http://localhost:8081/health
# Expected: {"status": "ok"}
```

#### Step 2 — Start Backend Second (Port 8080)

> 🔴 **Only start after the ML server is healthy.**

```bash
# Open a new terminal tab
cd ripple-backend-local
pip install -r requirements.txt
# Optional: add GEMINI_API_KEY to .env for AI-powered recommendations
echo "GEMINI_API_KEY=your_key_here" >> .env
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
# Wait for: "Application startup complete" before proceeding
```

Verify it's up:
```bash
curl http://localhost:8080/api/v1/health
# Expected: {"status": "ok"}
```

#### Step 3 — Start Frontend Last (Port 5173)

> 🔴 **Only start after both the ML server and backend are healthy.**

```bash
# Open a new terminal tab
cd ripple-frontend
npm install
npm run dev
# Open http://localhost:5173
```

#### ✅ All-Services Health Check

```bash
curl http://localhost:8081/health      # ML Server
curl http://localhost:8080/api/v1/health  # Backend
# Then open http://localhost:5173 in your browser
```

---

### 🎬 Live Demo Walkthrough

> Works with both the [live deployment](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/) and local setup.

1. **Login** → [`/login`](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/login) with demo credentials
2. **Navigate** → [`/app/graph`](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/graph) — observe 29 supplier nodes on 3D Earth
3. **Inject** → [`/app/simulation`](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/simulation) — select "TSMC Fab Shutdown"
4. **Watch** → Globe nodes turn red in real-time via WebSocket
5. **Inspect** → [`/app/analytics`](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/analytics) — KPIs: revenue at risk, critical nodes, 45-day chart
6. **Ask** → [`/app/agent`](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/agent) — *"Which Tier-2 suppliers are most at risk from the TSMC event?"*

---

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph CLIENT["🖥️ Frontend — React 18 + TypeScript + Vite · vercel.app"]
        LP[Landing Page<br/>Three.js Hero]
        GP[3D Globe<br/>GraphPage]
        SIM[Simulation<br/>Page]
        AN[Analytics<br/>Dashboard]
        CHAT[Agent Chat<br/>NL Interface]
    end

    subgraph BACKEND["⚡ Backend — FastAPI · ripplegraphai-1.onrender.com"]
        API[REST API Layer<br/>12 endpoints]
        WS[WebSocket<br/>Broadcast Manager]
        EQ[Event Queue<br/>Async Worker]
        AUTH[JWT Auth<br/>Middleware]
    end

    subgraph AGENTS["🤖 Multi-Agent Pipeline — Google ADK"]
        MA[MonitorAgent<br/>Severity Scoring]
        AA[AnalystAgent<br/>GNN Caller]
        RA[RecommenderAgent<br/>Gemini / Rule-Based]
    end

    subgraph ML["🧠 ML Server — GraphSAGE · ragas111-rippleai-ml.hf.space"]
        GNN[GraphSAGE GNN<br/>PyTorch Geometric]
        MDLS[Model Artifacts<br/>best_model.pt ~848KB]
    end

    subgraph DB["🗄️ SQLite — SQLAlchemy ORM"]
        U[users]
        S[suppliers]
        E[supply_edges]
        DE[disruption_events]
        RP[risk_predictions]
    end

    GP -- WebSocket :ws/live --> WS
    AN -- REST polling 8s --> API
    CHAT -- POST /agent/chat --> API
    SIM -- POST /simulation/run --> API

    API --> AUTH
    API --> EQ
    EQ --> MA
    MA --> AA
    AA --> GNN
    GNN --> MDLS
    AA --> RA
    RA --> WS
    WS -- risk_update / prediction_complete --> GP
    WS -- alerts --> AN

    API --> DB
    ML --> DB
```

---

## 🔄 Data Flow — Event to Visualization

```mermaid
sequenceDiagram
    actor User
    participant FE as React Frontend<br/>(vercel.app)
    participant API as FastAPI Backend<br/>(onrender.com)
    participant EQ as EventQueue
    participant ADK as ADK Pipeline
    participant GNN as GNN Server<br/>(hf.space)
    participant WS as WebSocket
    participant DB as SQLite

    User->>FE: Trigger disruption scenario
    FE->>API: POST /api/v1/simulation/run
    API->>DB: Create disruption_event record
    API-->>FE: 200 OK (immediate response)
    API->>EQ: Enqueue event (async)

    EQ->>ADK: MonitorAgent.process(event)
    ADK->>ADK: Score severity [0–1]
    ADK->>GNN: POST /predict {nodes, edges, event}
    GNN-->>ADK: {supplier_id: {scores[45], peak_day, peak_score}}
    ADK->>ADK: RecommenderAgent → Gemini/rule-based
    ADK->>DB: Save risk_predictions (29 rows)
    ADK->>WS: Broadcast risk_update
    WS->>FE: Live push → Globe recolors nodes
    WS->>FE: prediction_complete → KPI refresh
```

---

## 🤖 Multi-Agent AI Pipeline

```mermaid
flowchart LR
    EV([📥 Disruption\nEvent]) --> MA

    subgraph MA["MonitorAgent"]
        M1[Scan 29 nodes\nfor relationships]
        M2[Score severity\n0–1 scale]
        M3{severity\n> 0.3?}
        M1 --> M2 --> M3
    end

    M3 -- Yes / Escalate --> AA
    M3 -- No / Suppress --> DONE([✅ No-op])

    subgraph AA["AnalystAgent"]
        A1[Call GNN · hf.space\nwith graph payload]
        A2[Receive 45-day\nper-node scores]
        A3[Calculate peak_risk_day\npeak_risk_score per supplier]
        A4[Aggregate revenue\nat risk across nodes]
        A1 --> A2 --> A3 --> A4
    end

    AA --> RA

    subgraph RA["RecommenderAgent"]
        R1{Gemini\nAPI key?}
        R2[Gemini LLM\nRecommendations]
        R3[Rule-Based\nFallback]
        R4[Rank by urgency\n& impact — top 5]
        R1 -- Yes --> R2
        R1 -- No --> R3
        R2 & R3 --> R4
    end

    RA --> OUT([📡 Broadcast\nprediction_complete])
```

**Graceful Degradation:** All three agents fall back to rule-based logic if Gemini API or the GNN server is unreachable — the demo runs **100% offline**.

---

## 🧠 GraphSAGE GNN

> 🔗 ML Server: **[ragas111-rippleai-ml.hf.space](https://ragas111-rippleai-ml.hf.space/)**

### Model Architecture

```mermaid
graph LR
    IN["Node Features\n[tier, category, revenue,\ncountry, risk_score,\nconnected_count]\ndim=16"] --> NE

    subgraph NE["NodeEncoder"]
        L1[Linear → LayerNorm\n→ LeakyReLU]
        L2[Linear → LayerNorm]
        L1 --> L2
    end

    NE --> BB

    subgraph BB["GraphSAGE Backbone — 3 Layers"]
        C1["SAGEConv\n(mean agg, normalize)"] --> BN1[BatchNorm] --> S1[+Skip]
        S1 --> C2["SAGEConv"] --> BN2[BatchNorm] --> S2[+Skip]
        S2 --> C3["SAGEConv"] --> BN3[BatchNorm] --> S3[+Skip]
    end

    BB --> HEAD["Prediction Head\nLinear → ReLU → Linear\noutput_dim=45"]
    HEAD --> OUT["Per-Node\nRisk Scores\n45-day trajectory\n[0, 1]"]
```

### Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `hidden_dim` | 128 | Balanced capacity for 29-node graph |
| `num_layers` | 3 | 3-hop neighbourhood → Tier-3 reaches OEM |
| `dropout` | 0.3 | Prevents overfitting on small graph |
| `aggregation` | mean | Stable, no attention overhead |
| `loss_fn` | Huber (δ=0.5) | Robust to outlier risk spikes |
| `scheduler` | Cosine + 5ep warmup | Smooth convergence |
| `neighbor_samples` | [15, 10, 5] | Layer-wise mini-batch sampling |
| `epochs` | 100 + early stopping (patience=15) | Prevents over-training |
| `device` | auto (CUDA → MPS → CPU) | Cross-platform |

---

## 📊 Analytics & Stats

### Scenario Risk Matrix

```mermaid
xychart-beta
    title "Peak Risk Score by Supplier Tier — All Scenarios"
    x-axis ["TSMC Shutdown", "Rare Earth Ban", "Port Strike", "Penang Flood", "Battery Recall", "Normal Ops"]
    y-axis "Risk Score" 0 --> 1
    bar [0.92, 0.81, 0.68, 0.58, 0.51, 0.10]
    line [0.44, 0.32, 0.38, 0.25, 0.22, 0.05]
```

> 📊 **Bar = Tier-3 (origin)** · **Line = OEM (downstream impact)**

### Cascade Propagation Timeline

```mermaid
gantt
    title Risk Cascade — Days to Peak by Scenario
    dateFormat  D
    axisFormat Day %d

    section TSMC Shutdown
    Tier-3 Peak     :crit, t3a, 1, 7d
    Tier-2 Impact   :      t2a, 3, 10d
    Tier-1 Impact   :      t1a, 5, 14d
    OEM Impact      :      oema, 7, 18d

    section Rare Earth Ban
    Tier-3 Peak     :crit, t3b, 1, 14d
    Tier-2 Impact   :      t2b, 5, 19d
    Tier-1 Impact   :      t1b, 9, 24d
    OEM Impact      :      oemb, 14, 28d

    section Port Strike
    Tier-3 Peak     :crit, t3c, 1, 5d
    Tier-2 Impact   :      t2c, 2, 8d
    Tier-1 Impact   :      t1c, 3, 12d
    OEM Impact      :      oemc, 5, 15d
```

### API Surface Map

```mermaid
mindmap
  root((RippleGraph API<br/>onrender.com))
    Auth
      POST /auth/login
      POST /auth/register
    Suppliers
      GET /suppliers/
    Events
      POST /events/
      GET /events/active
    Simulation
      POST /simulation/run
      POST /simulation/reset
    Predictions
      GET /predictions/summary
      GET /predictions/tier-breakdown
    Graph
      GET /graph/
    Agent
      POST /agent/chat
    WebSocket
      WS /ws/live
```

---

## 🗄️ Database Schema

```mermaid
erDiagram
    users {
        int id PK
        string email
        string password_hash
        string name
        datetime created_at
    }
    suppliers {
        int id PK
        string name
        int tier
        string country
        string category
        float annual_revenue_usd
        float latitude
        float longitude
        float risk_score
        string risk_level
    }
    supply_edges {
        int id PK
        int source_id FK
        int target_id FK
        float dependency_weight
        string edge_type
    }
    disruption_events {
        int id PK
        int supplier_id FK
        string disruption_type
        float severity
        string description
        float affected_capacity_pct
        string source
        string country
        string category
        string status
        datetime created_at
    }
    risk_predictions {
        int id PK
        int trigger_event_id FK
        int supplier_id FK
        float peak_risk_score
        int peak_risk_day
        string risk_level
        float confidence
        float total_revenue_at_risk_usd
        int affected_supplier_count
        int critical_count
        int high_count
        string model_version
        json recommendations
        string urgency
        datetime created_at
    }

    users ||--o{ disruption_events : "creates"
    suppliers ||--o{ supply_edges : "source"
    suppliers ||--o{ supply_edges : "target"
    suppliers ||--o{ disruption_events : "affected"
    disruption_events ||--o{ risk_predictions : "triggers"
    suppliers ||--o{ risk_predictions : "predicted for"
```

---

## 🖥️ Frontend Route Map

> Base URL: **[ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/)**

```mermaid
graph TD
    ROOT["/"] --> HOME["🏠 HomePage<br/>Three.js hero + parallax<br/>GSAP entrance animations"]
    ROOT --> ABOUT["/about<br/>📄 AboutPage"]
    ROOT --> LOGIN["/login<br/>🔐 LoginPage — JWT"]

    LOGIN -->|JWT token| APP["/app — Protected"]

    APP --> GRAPH["/app/graph<br/>🌍 3D Earth Globe<br/>29 supplier nodes live"]
    APP --> SIM["/app/simulation<br/>⚡ Scenario Injection<br/>ADK terminal log"]
    APP --> EVENTS["/app/events<br/>📋 Event Feed"]
    APP --> ANALYTICS["/app/analytics<br/>📊 KPI Dashboard<br/>8-sec polling + WS override"]
    APP --> AGENT["/app/agent<br/>💬 AgentChat<br/>Natural language queries"]

    style GRAPH fill:#1e40af,color:#fff
    style ANALYTICS fill:#065f46,color:#fff
    style AGENT fill:#7c3aed,color:#fff
```

| Route | Live Link |
|-------|-----------|
| 🏠 Home | [/](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/) |
| 🔐 Login | [/login](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/login) |
| 🌍 3D Globe | [/app/graph](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/graph) |
| ⚡ Simulation | [/app/simulation](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/simulation) |
| 📊 Analytics | [/app/analytics](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/analytics) |
| 💬 Agent Chat | [/app/agent](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/agent) |

---

## 🌐 WebSocket Events

> WebSocket endpoint: `wss://ripplegraphai-1.onrender.com/ws/live`

| Event Type | Trigger | Payload Shape |
|---|---|---|
| `snapshot` | On WS connect | `{supplier_id: {score, level, peak_day}}` |
| `risk_update` | After simulation/event | Same as snapshot |
| `prediction_complete` | Pipeline finished | `{event_id, urgency, critical, high, revenue, summary, recommendations[]}` |
| `new_event` | Disruption created | Full disruption_event object |

```javascript
// Connect to live backend
const ws = new WebSocket("wss://ripplegraphai-1.onrender.com/ws/live");
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.type === "risk_update") updateGlobe(msg.payload);
  if (msg.type === "prediction_complete") refreshKPIs(msg.payload);
};
```

---

## 🧱 Project Structure

```
ripplegraph-ai/
├── ripple-backend-local/           # → deployed: ripplegraphai-1.onrender.com
│   └── app/
│       ├── agents/          # Google ADK pipeline (3 agents)
│       ├── api/routes/      # 12 FastAPI route modules
│       ├── core/            # Auth (JWT), config, logging
│       ├── models/          # Pydantic schemas
│       └── services/        # DB, EventQueue, WS manager, ML client
├── ripple-frontend/                # → deployed: vercel.app
│   └── src/
│       ├── components/      # graph/, dashboard/, auth/
│       ├── hooks/           # TanStack Query, WebSocket
│       ├── services/        # Axios client + interceptors
│       ├── store/           # Zustand auth state
│       └── types/           # TypeScript interfaces
└── ripple-ml-local/                # → deployed: ragas111-rippleai-ml.hf.space
    ├── ml/
    │   ├── model/           # GraphSAGE + GAT architectures
    │   ├── data/            # Dataset, graph builder, DB
    │   ├── serving/         # Prediction server + stub
    │   ├── evaluation/      # Metrics
    │   └── agents/          # Local LLM recommender (Ollama)
    ├── artifacts/
    │   ├── checkpoints/     # model_ep0020 … model_ep0100 + best
    │   └── model.pt         # ~848KB serving artifact
    └── configs/ml_config.yaml
```

---

## 🎬 MVP / Demo

> **[ 🖼️ Add screenshots / GIF / Loom video here ]**

```
┌─────────────────────────────────────────────────────────────┐
│                    DEMO ASSETS — TODO                       │
├─────────────────────────────────────────────────────────────┤
│  📸 Screenshot: 3D Globe with live risk nodes               │
│  📸 Screenshot: Analytics dashboard — KPI cards             │
│  📸 Screenshot: Simulation page — scenario injection        │
│  📸 Screenshot: Agent Chat — natural language query         │
│  🎬 GIF: TSMC scenario cascade animation (45-day timeline)  │
│  🎬 GIF: WebSocket live update — globe node recoloring      │
│  🔗 Loom / YouTube: Full demo walkthrough (< 3 min)         │
└─────────────────────────────────────────────────────────────┘
```

### Live Demo Links

| Step | Action | Link |
|------|--------|------|
| 1 | 🧠 Wake ML Server | [ragas111-rippleai-ml.hf.space](https://ragas111-rippleai-ml.hf.space/) |
| 2 | ⚡ Wake Backend | [ripplegraphai-1.onrender.com](https://ripplegraphai-1.onrender.com/) |
| 3 | 🔐 Login | [/login](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/login) |
| 4 | 🌍 View 3D Globe | [/app/graph](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/graph) |
| 5 | ⚡ Inject Scenario | [/app/simulation](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/simulation) |
| 6 | 📊 View Analytics | [/app/analytics](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/analytics) |
| 7 | 💬 Ask Agent | [/app/agent](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/app/agent) |

---

## 🛠️ Tech Stack

```mermaid
graph LR
    subgraph FE["Frontend · vercel.app"]
        R18[React 18]
        TS[TypeScript]
        THREE[Three.js]
        TANSTACK[TanStack Query v5]
        ZUSTAND[Zustand]
        FM[Framer Motion]
        GSAP[GSAP]
    end

    subgraph BE["Backend · onrender.com"]
        FAPI[FastAPI 0.115]
        UV[Uvicorn]
        SQLA[SQLAlchemy]
        SQLITE[SQLite]
        JWT[JWT Auth]
    end

    subgraph AI["AI / ML · hf.space"]
        ADK[Google ADK]
        GEMINI[Gemini API]
        PT[PyTorch 2.4]
        PTG[PyTorch Geometric]
        GRAPHSAGE[GraphSAGE]
    end
```

---

## 🏆 Why RippleGraph Wins

| Judging Criterion | RippleGraph Advantage |
|---|---|
| **Innovation** | Graph Neural Network applied to supply chain cascade — rare combination |
| **Technical Depth** | Full-stack: GNN + multi-agent AI + WebSocket + 3D globe, all wired together |
| **Real-world Impact** | $4.4T problem; 45-day early warning turns reactive → proactive |
| **Demo Quality** | Live 3D Earth, real-time WebSocket, 6 crisis scenarios, AI chat — visually stunning |
| **Offline Resilience** | 100% functional without Gemini key or cloud — judges can run it anywhere |
| **Code Quality** | Type-safe (TypeScript + Pydantic), modular architecture, clean separation of concerns |

---

## 📈 Model Performance

| Metric | Value |
|---|---|
| Test Accuracy | **94.2%** |
| Training Epochs | 100 (early stopping patience=15) |
| Loss Function | Huber (δ=0.5) — robust to spikes |
| Inference Latency | < 10s timeout (configurable) |
| Model File Size | ~848 KB |
| Checkpoints Saved | Every 20 epochs (ep020→ep100 + best) |

> 🔗 Model served at: **[ragas111-rippleai-ml.hf.space](https://ragas111-rippleai-ml.hf.space/)**

---

## 📄 License

MIT License — built for Hackathon 2024. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for Hackathon 2024**

*RippleGraph AI — Predict the ripple. Prevent the wave.*

| 🖥️ Frontend | 🧠 ML Server | ⚡ Backend |
|------------|-------------|----------|
| [vercel.app](https://ripplegraph-ccj0s7nz7-pushkar-khattri-s-projects.vercel.app/) | [hf.space](https://ragas111-rippleai-ml.hf.space/) | [onrender.com](https://ripplegraphai-1.onrender.com/) |

[![Star this repo](https://img.shields.io/github/stars/RaGaS958/RippleGraphAI?style=social)](.)

</div>
