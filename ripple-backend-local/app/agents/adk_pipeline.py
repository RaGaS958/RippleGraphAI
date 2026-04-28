from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# ── Logger first ──────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Load .env explicitly ──────────────────────────────────────────────────────
_here = Path(__file__).resolve()
for _parent in [_here.parent, _here.parent.parent, _here.parent.parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(dotenv_path=str(_env), override=True)
        break

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ML_SERVER_URL  = os.getenv("ML_SERVER_URL", "http://localhost:8081")
print("🔑 GEMINI KEY LENGTH:", len(GEMINI_API_KEY) if GEMINI_API_KEY else 0)

# ── Import ADK ────────────────────────────────────────────────────────────────
ADK_AVAILABLE = False
try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    try:
        from google.adk.tools import tool as _adk_tool
    except ImportError:
        def _adk_tool(fn): return fn

    ADK_AVAILABLE = True
    logger.info("Google ADK loaded")

except ImportError as e:
    logger.warning(f"google-adk not available: {e}")

    def _adk_tool(fn): return fn

    class Agent:
        def __init__(self, **kw): pass

    class Runner:
        def __init__(self, **kw): pass

    class InMemorySessionService:
        pass


def _tool(fn):
    return _adk_tool(fn) if ADK_AVAILABLE else fn

print("ADK AVAILABLE:", ADK_AVAILABLE)
# ── Tools ─────────────────────────────────────────────────────────────────────

@_tool
def get_supplier_info(supplier_id: str) -> dict:
    """Retrieve full supplier details — tier, country, category, revenue, risk score."""
    from app.services.database import Database
    s = Database.get_supplier(supplier_id)
    if not s:
        return {"error": f"Supplier {supplier_id} not found"}
    return {
        "id": s["id"], "name": s["name"], "tier": s["tier"],
        "country": s["country"], "category": s["category"],
        "revenue_usd": s.get("annual_revenue_usd", 0),
        "risk_score": s.get("risk_score", 0), "risk_level": s.get("risk_level", "low"),
        "delay_rate": s.get("historical_delay_rate", 0),
    }


@_tool
def get_downstream_suppliers(supplier_id: str) -> dict:
    """Find all suppliers that depend on the given supplier — maps cascade scope."""
    from app.services.database import Database
    ids = Database.get_downstream_ids(supplier_id)
    sample = []
    for sid in ids[:10]:
        s = Database.get_supplier(sid)
        if s:
            sample.append({"id": s["id"], "name": s["name"], "tier": s["tier"], "country": s["country"]})
    return {"trigger_supplier_id": supplier_id, "downstream_count": len(ids), "downstream_sample": sample}


@_tool
def call_gnn_prediction(supplier_id: str, severity: float, horizon_days: int = 45) -> dict:
    """Call the GNN prediction server for 45-day cascade risk forecasts."""
    from app.services.database import Database
    from app.services.ml_client import _node_features, _edge_features

    suppliers   = Database.list_suppliers()
    edges       = Database.list_edges()
    tier_lookup = {s["id"]: s["tier"] for s in suppliers}

    for s in suppliers:
        if s["id"] == supplier_id:
            s["risk_score"] = severity
            break

    nodes = [{"id": s["id"], "features": _node_features(s),
              "tier": s["tier"], "risk_score": float(s.get("risk_score", 0))}
             for s in suppliers]

    graph_edges = []
    for e in edges:
        src, tgt = e.get("source_supplier_id", ""), e.get("target_supplier_id", "")
        if src in tier_lookup and tgt in tier_lookup:
            ef = _edge_features({**e, "src_tier": tier_lookup[src], "tgt_tier": tier_lookup[tgt]})
            graph_edges.append({"source": src, "target": tgt, "features": ef,
                                 "dependency_weight": float(e.get("dependency_weight", 0.5)),
                                 "is_sole_source": bool(e.get("is_sole_source", False))})

    try:
        resp = httpx.post(f"{ML_SERVER_URL}/predict",
                          json={"graph_nodes": nodes, "graph_edges": graph_edges,
                                "trigger_event_id": str(uuid.uuid4()), "horizon_days": horizon_days},
                          timeout=15.0)
        resp.raise_for_status()
        result      = resp.json()
        predictions = result.get("predictions", {})
        peaks       = [p.get("peak_risk_score", 0) for p in predictions.values()]
        critical    = [sid for sid, p in predictions.items() if p.get("risk_level") == "critical"]
        high        = [sid for sid, p in predictions.items() if p.get("risk_level") == "high"]
        return {
            "model_version":       result.get("model_version", "unknown"),
            "nodes_predicted":     len(predictions),
            "max_risk_score":      round(max(peaks, default=0), 4),
            "avg_risk_score":      round(sum(peaks) / max(len(peaks), 1), 4),
            "critical_count":      len(critical),
            "high_count":          len(high),
            "critical_ids":        critical[:5],
            "revenue_at_risk_usd": round(sum(p.get("peak_risk_score", 0) * 5e8 for p in predictions.values()), 2),
            "raw_predictions":     predictions,
        }
    except Exception as e:
        return {"error": str(e)}


@_tool
def get_risk_summary() -> dict:
    """Get current portfolio-wide risk summary from the database."""
    from app.services.database import Database
    s = Database.get_risk_summary()
    return {
        "total_revenue_at_risk_usd": float(s.get("total_revenue_at_risk_usd") or 0),
        "affected_suppliers":        int(s.get("affected_suppliers") or 0),
        "avg_risk_score":            float(s.get("avg_risk_score") or 0),
        "critical_count":            int(s.get("critical_count") or 0),
        "high_count":                int(s.get("high_count") or 0),
    }


@_tool
def save_prediction_to_db(
    trigger_event_id: str, supplier_id: str,
    peak_risk_score: float, risk_level: str,
    revenue_at_risk_usd: float, affected_count: int,
    critical_count: int, high_count: int,
    urgency: str, recommendations: list,
    model_version: str = "gnn-v1",
) -> dict:
    """Persist prediction results to the database — makes them visible on the dashboard."""
    from app.services.database import Database
    pid = str(uuid.uuid4())
    Database.save_prediction({
        "id": pid, "trigger_event_id": trigger_event_id, "supplier_id": supplier_id,
        "peak_risk_score": round(peak_risk_score, 4), "peak_risk_day": 7,
        "risk_level": risk_level, "confidence": 0.87,
        "total_revenue_at_risk_usd": round(revenue_at_risk_usd, 2),
        "affected_supplier_count": affected_count, "critical_count": critical_count,
        "high_count": high_count, "model_version": model_version,
        "recommendations": json.dumps(recommendations[:5]), "urgency": urgency,
    })
    logger.info(f"Prediction saved: {pid} | {urgency} | ${revenue_at_risk_usd/1e9:.2f}B")
    return {"prediction_id": pid, "saved": True}


@_tool
def push_risk_scores_to_websocket(risk_scores: dict) -> dict:
    """Push updated risk scores to all connected 3D graph clients via WebSocket."""
    from app.services.websocket_manager import ws_manager
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(ws_manager.broadcast_risk_update(risk_scores))
        else:
            loop.run_until_complete(ws_manager.broadcast_risk_update(risk_scores))
        return {"pushed": True, "nodes_updated": len(risk_scores)}
    except Exception as e:
        return {"pushed": False, "error": str(e)}


# ── ADK Agent definitions ─────────────────────────────────────────────────────

def _make_monitor_agent():
    if not ADK_AVAILABLE: return None
    return Agent(
        name="MonitorAgent", model="gemini-2.0-flash",
        description="Monitors disruption alerts. Validates events and enriches with supplier context.",
        instruction="""You are a supply chain disruption monitor for a Fortune 500 manufacturer.
When you receive a disruption event:
1. Use get_supplier_info to retrieve full supplier details
2. Use get_downstream_suppliers to map cascade scope
3. Assess: is this Tier-3 hidden risk or visible Tier-1 issue?
4. Provide: supplier summary, downstream count, severity (LOW/MEDIUM/HIGH/CRITICAL), action (MONITOR/INVESTIGATE/ESCALATE)
Be concise. This feeds directly into the GNN analyst.""",
        tools=[get_supplier_info, get_downstream_suppliers, get_risk_summary],
    )


def _make_analyst_agent():
    if not ADK_AVAILABLE: return None
    return Agent(
        name="AnalystAgent", model="gemini-2.0-flash",
        description="Calls GNN model to predict 45-day supply chain cascade risk.",
        instruction="""You are a supply chain risk analyst with a Graph Neural Network model.
When given a disruption:
1. Call call_gnn_prediction with supplier_id and severity
2. Interpret: critical nodes (>70% risk), peak day, revenue at risk, tier exposure
3. Report: total revenue at risk ($B), critical count, cascade timeline, tier-by-tier summary
Use precise numbers. The recommender needs your analysis.""",
        tools=[call_gnn_prediction, get_supplier_info],
    )


def _make_recommender_agent():
    if not ADK_AVAILABLE: return None
    return Agent(
        name="RecommenderAgent", model="gemini-2.0-flash",
        description="Generates rerouting recommendations and saves results to DB and 3D graph.",
        instruction="""You are a senior supply chain strategist.
Given the analyst's risk report:
1. Generate 3-5 ranked recommendations (specific regions, lead times, cost impact, confidence)
2. Assign urgency: CRITICAL/HIGH/MEDIUM/LOW
3. Call save_prediction_to_db with complete results
4. Call push_risk_scores_to_websocket to update the 3D graph
Always save and push — required for the demo dashboard.""",
        tools=[save_prediction_to_db, push_risk_scores_to_websocket],
    )


def _make_orchestrator(monitor, analyst, recommender):
    if not ADK_AVAILABLE: return None
    return Agent(
        name="RippleGraphOrchestrator", model="gemini-2.0-flash",
        description="Orchestrates supply chain analysis across Monitor, Analyst, and Recommender agents.",
        instruction="""You are the RippleGraph AI orchestrator.
You coordinate three agents:
- MonitorAgent: validates events, maps supplier context
- AnalystAgent: GNN predictions, quantifies risk
- RecommenderAgent: rerouting strategies, saves results

For each disruption: Monitor → Analyst → Recommender.
For questions: answer directly or route to the right agent.
Always be decisive — supply chain decisions cost money every minute.""",
        tools=[get_risk_summary],
        sub_agents=[monitor, analyst, recommender],
    )


# ── Pipeline ──────────────────────────────────────────────────────────────────

class ADKMultiAgentPipeline:

    def __init__(self):
        self._adk_ready       = False
        self._runner          = None
        self._session_service = None
        self._app_name        = "ripple-graph-ai"

        if ADK_AVAILABLE and GEMINI_API_KEY:
            try:
                self._setup_adk()
                self._adk_ready = True
                logger.info("ADK pipeline ready with Gemini")
            except Exception as e:
                logger.warning(f"ADK setup failed: {e} — using fallback")
        else:
            if not GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY not set — add to .env for full ADK")
            logger.info("Using manual pipeline fallback")

    def _setup_adk(self):
        # ✅ FIX: Use GOOGLE_API_KEY env var — ADK reads it automatically.
        # Removed deprecated `import google.generativeai` and `genai.configure()`.
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

        monitor      = _make_monitor_agent()
        analyst      = _make_analyst_agent()
        recommender  = _make_recommender_agent()
        orchestrator = _make_orchestrator(monitor, analyst, recommender)
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=orchestrator,
            app_name=self._app_name,
            session_service=self._session_service,
        )
        logger.info("ADK Runner: Orchestrator → [Monitor, Analyst, Recommender]")

    async def run(self, event: dict) -> dict:
        if self._adk_ready:
            return await self._run_adk(event)
        return await self._run_fallback(event)

    async def _run_adk(self, event: dict) -> dict:
        session_id = f"sess-{event.get('id','x')[:8]}"
        try:
            await self._session_service.create_session(
                app_name=self._app_name, user_id="system", session_id=session_id)
        except Exception:
            pass

        prompt = f"""
New disruption alert:
Event ID: {event.get('id','?')}  Supplier: {event.get('supplier_id','?')}
Type: {event.get('disruption_type','?')}  Severity: {float(event.get('severity',0.8)):.0%}
Capacity affected: {event.get('affected_capacity_pct',40):.0f}%
Country: {event.get('country','?')}  Category: {event.get('category','?')}
Description: {event.get('description','No description')}

Run full analysis: Monitor → Analyst (GNN) → Recommender (save + push to 3D graph).
"""
        message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
        logger.info(f"ADK pipeline start | {event.get('id','?')[:8]}")

        final, events = "", []
        async for e in self._runner.run_async(
            user_id="system", session_id=session_id, new_message=message
        ):
            if hasattr(e, "author"):
                events.append({"agent": e.author, "type": type(e).__name__})
                logger.info(f"  [{e.author}] {type(e).__name__}")
            if e.is_final_response() and e.content and e.content.parts:
                final = e.content.parts[0].text

        logger.info(f"ADK pipeline done | {len(events)} events")
        return {"mode": "adk", "agent_events": events, "final_response": final}

    async def _run_fallback(self, event: dict) -> dict:
        import numpy as np
        from app.services.database import Database
        from app.services.websocket_manager import ws_manager

        logger.info(f"Fallback pipeline | {event.get('id','?')[:8]}")

        supplier   = Database.get_supplier(event.get("supplier_id", "")) or {}
        downstream = Database.get_downstream_ids(event.get("supplier_id", ""))
        logger.info(f"  [MonitorAgent] {supplier.get('name','?')} downstream={len(downstream)}")

        gnn = call_gnn_prediction(
            supplier_id=event.get("supplier_id", ""),
            severity=float(event.get("severity", 0.7)),
        )

        if "error" in gnn:
            suppliers = Database.list_suppliers()
            sev       = float(event.get("severity", 0.5))
            DECAY     = {"tier_3":1.0,"tier_2":0.65,"tier_1":0.40,"oem":0.20}
            raw = {}
            for s in suppliers:
                base   = sev * DECAY.get(s["tier"], 0.5) * (1.0 if s["id"] == event.get("supplier_id") else 0.5)
                scores = [max(0.0,min(1.0,base*np.exp(-0.06*abs(d-7))+np.random.uniform(-0.01,0.01))) for d in range(45)]
                peak   = max(scores)
                raw[s["id"]] = {"risk_scores":scores,"peak_risk_score":round(peak,4),
                                 "peak_risk_day":scores.index(peak),"risk_level":_level(peak)}
            gnn = {
                "model_version":"rule-based-fallback","nodes_predicted":len(raw),
                "max_risk_score":max(p["peak_risk_score"] for p in raw.values()),
                "critical_count":sum(1 for p in raw.values() if p["risk_level"]=="critical"),
                "high_count":    sum(1 for p in raw.values() if p["risk_level"]=="high"),
                "revenue_at_risk_usd":sum(p["peak_risk_score"]*5e8 for p in raw.values()),
                "raw_predictions":raw,
            }

        logger.info(f"  [AnalystAgent] nodes={gnn['nodes_predicted']} crit={gnn['critical_count']} ${gnn['revenue_at_risk_usd']/1e9:.2f}B")

        recs    = [
            f"Activate backup {event.get('category','component')} suppliers in Malaysia/Vietnam",
            "Increase Tier-1 safety stock by 30% immediately",
            f"Issue dual-source RFQ for {event.get('category','components')} to 5 vendors",
        ]
        urgency = "CRITICAL" if gnn["max_risk_score"]>0.7 else "HIGH" if gnn["max_risk_score"]>0.4 else "MEDIUM"

        # ✅ FIX: was `pred_id` (undefined) — corrected to `pid` throughout
        pid = str(uuid.uuid4())
        Database.save_prediction({
            "id": pid, "trigger_event_id": event.get("id", ""),
            "supplier_id": event.get("supplier_id", ""),
            "peak_risk_score": round(gnn["max_risk_score"], 4), "peak_risk_day": 7,
            "risk_level": _level(gnn["max_risk_score"]), "confidence": 0.85,
            "total_revenue_at_risk_usd": round(gnn["revenue_at_risk_usd"], 2),
            "affected_supplier_count": gnn["nodes_predicted"],
            "critical_count": gnn["critical_count"], "high_count": gnn["high_count"],
            "model_version": gnn["model_version"], "recommendations": json.dumps(recs),
            "urgency": urgency,
        })

        for sid, pred in gnn.get("raw_predictions", {}).items():
            Database.update_supplier_risk(sid, pred.get("peak_risk_score", 0), pred.get("risk_level", "low"))

        ws_scores = {sid: {"score": p.get("peak_risk_score", 0), "level": p.get("risk_level", "low"), "peak_day": p.get("peak_risk_day", 7)}
                     for sid, p in gnn.get("raw_predictions", {}).items()}
        await ws_manager.broadcast_risk_update(ws_scores)
        await ws_manager.broadcast_prediction_complete({
            "event_id": event.get("id", ""), "urgency": urgency,
            "critical": gnn["critical_count"], "high": gnn["high_count"],
            "revenue": gnn["revenue_at_risk_usd"], "model": gnn["model_version"],
            "summary": f"{urgency} — ${gnn['revenue_at_risk_usd']/1e9:.2f}B at risk",
            "recommendations": recs,
        })

        logger.info(f"  [RecommenderAgent] urgency={urgency} saved={pid[:8]}")
        return {"mode": "fallback", "prediction_id": pid, "urgency": urgency,
                "affected_count": gnn["nodes_predicted"], "revenue": gnn["revenue_at_risk_usd"]}


def _level(s: float) -> str:
    if s >= 0.70: return "critical"
    if s >= 0.40: return "high"
    if s >= 0.20: return "medium"
    return "low"


# ── Singletons ────────────────────────────────────────────────────────────────

pipeline = ADKMultiAgentPipeline()


async def handle_disruption_event(event: dict) -> None:
    await pipeline.run(event)


async def chat_with_orchestrator(message: str, session_id: str = "chat-default") -> str:
    if not pipeline._adk_ready:
        return ("ADK not active. Add GEMINI_API_KEY to .env and restart.\n"
                "pip install google-adk google-genai")

    try:
        await pipeline._session_service.create_session(
            app_name=pipeline._app_name, user_id="user", session_id=session_id)
    except Exception:
        pass

    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=message)])
    response = ""
    async for e in pipeline._runner.run_async(
        user_id="user", session_id=session_id, new_message=msg
    ):
        if e.is_final_response() and e.content and e.content.parts:
            response = e.content.parts[0].text
    return response or "No response."
