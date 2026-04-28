"""
ADK-style 3-agent pipeline — Monitor → Analyst → Recommender.
Fully local. No google-adk or cloud required.
Registered as the EventQueue handler at startup.
"""
from __future__ import annotations
import json, logging, uuid
from datetime import datetime
from typing import Dict, Any

from app.services.database import Database
from app.services.ml_client import MLClient
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)
_ml_client = MLClient()


# ── Agent 1: Monitor ──────────────────────────────────────────────────────────

class MonitorAgent:
    """
    Receives raw event dict from EventQueue.
    Validates supplier exists, enriches with DB data, passes to Analyst.
    """
    name = "MonitorAgent"

    async def process(self, event: dict) -> dict:
        logger.info(f"[{self.name}] Processing event {event.get('id','?')[:8]}…")

        supplier = Database.get_supplier(event.get("supplier_id",""))
        if not supplier:
            logger.warning(f"[{self.name}] Supplier not found: {event.get('supplier_id')}")
            # Still continue — ML server can handle unknown suppliers
            supplier = {}

        return {
            "agent":    self.name,
            "event":    event,
            "supplier": supplier,
            "enriched": bool(supplier),
        }


# ── Agent 2: Analyst ──────────────────────────────────────────────────────────

class AnalystAgent:
    """
    Calls the ML prediction server (local FastAPI on port 8081).
    Returns 45-day risk predictions for all suppliers in the graph.
    """
    name = "AnalystAgent"

    async def analyze(self, monitor_out: dict) -> dict:
        event    = monitor_out["event"]
        supplier = monitor_out.get("supplier", {})
        logger.info(f"[{self.name}] Running GNN inference for event {event.get('id','?')[:8]}…")

        ml_reachable = await _ml_client.is_reachable()

        if ml_reachable:
            try:
                result = await _ml_client.predict(event)
                predictions = result.get("predictions", {})
                model_version = result.get("model_version", "unknown")
                inference_ms  = result.get("inference_ms", 0)
            except Exception as e:
                logger.error(f"[{self.name}] ML call failed: {e} — using rule-based fallback")
                predictions, model_version, inference_ms = self._rule_based(event), "rule-based-fallback", 0
        else:
            logger.warning(f"[{self.name}] ML server unreachable — using rule-based fallback")
            predictions, model_version, inference_ms = self._rule_based(event), "rule-based-fallback", 0

        # Aggregate stats
        peak_scores = [p.get("peak_risk_score",0) for p in predictions.values()]
        critical_count = sum(1 for p in predictions.values() if p.get("risk_level")=="critical")
        high_count     = sum(1 for p in predictions.values() if p.get("risk_level")=="high")
        total_rev      = sum(p.get("peak_risk_score",0) * 5e8 for p in predictions.values())

        return {
            "agent":            self.name,
            "event":            event,
            "supplier":         supplier,
            "predictions":      predictions,
            "model_version":    model_version,
            "inference_ms":     inference_ms,
            "peak_risk":        max(peak_scores, default=0),
            "critical_count":   critical_count,
            "high_count":       high_count,
            "revenue_at_risk":  total_rev,
            "affected_count":   len(predictions),
        }

    def _rule_based(self, event: dict) -> dict:
        """Fallback when ML server is down."""
        import numpy as np
        suppliers = Database.list_suppliers()
        sev = float(event.get("severity", 0.5))
        DECAY = {"tier_3":1.0,"tier_2":0.65,"tier_1":0.40,"oem":0.20}
        result = {}
        for s in suppliers:
            base = sev * DECAY.get(s["tier"],0.5) if s["id"]==event.get("supplier_id") else sev * DECAY.get(s["tier"],0.3) * 0.5
            scores = [round(max(0.0, min(1.0, base * np.exp(-0.06*abs(d-7)) + np.random.uniform(-0.01,0.01))),4) for d in range(45)]
            peak = max(scores)
            result[s["id"]] = {"risk_scores": scores, "peak_risk_score": round(peak,4),
                               "peak_risk_day": scores.index(peak),
                               "risk_level": _level(peak), "confidence": 0.50}
        return result


# ── Agent 3: Recommender ──────────────────────────────────────────────────────

class RecommenderAgent:
    """
    Calls local Ollama LLM for rerouting recommendations.
    Falls back to template if Ollama is not running.
    """
    name = "RecommenderAgent"

    async def recommend(self, analyst_out: dict) -> dict:
        logger.info(f"[{self.name}] Generating recommendations…")
        event       = analyst_out["event"]
        predictions = analyst_out["predictions"]
        try:
            from app.agents.local_llm_recommender import LocalLLMRecommender
            rec    = LocalLLMRecommender()
            result = rec.recommend(event, predictions)
        except Exception as e:
            logger.error(f"[{self.name}] LLM failed: {e} — using template")
            result = self._template(event, analyst_out)

        return {
            "agent":          self.name,
            "urgency":        result.get("urgency","MEDIUM"),
            "summary":        result.get("summary",""),
            "recommendations":result.get("recommendations",[]),
            "generated_by":   result.get("generated_by","template"),
            "analyst_output": analyst_out,
        }

    def _template(self, event: dict, analyst: dict) -> dict:
        sev = float(event.get("severity",0.5))
        cat = event.get("category","components")
        return {
            "urgency": "CRITICAL" if sev>0.7 else "HIGH" if sev>0.4 else "MEDIUM",
            "generated_by": "template-fallback",
            "summary": f"Disruption in {event.get('country','region')} affecting {cat}.",
            "recommendations": [
                {"rank":1,"action":f"Activate backup {cat} suppliers","lead_time_days":21,"confidence":0.80},
                {"rank":2,"action":"Increase safety stock by 30% at Tier-1","lead_time_days":3,"confidence":0.90},
                {"rank":3,"action":f"Issue dual-source RFQ for {cat}","lead_time_days":45,"confidence":0.75},
            ],
        }


# ── Pipeline orchestrator ──────────────────────────────────────────────────────

class ADKPipeline:
    """Monitor → Analyst → Recommender, then write results to DB + push via WebSocket."""

    def __init__(self):
        self.monitor     = MonitorAgent()
        self.analyst     = AnalystAgent()
        self.recommender = RecommenderAgent()

    async def run(self, raw_event: dict) -> dict:
        logger.info(f"ADK pipeline START | event={raw_event.get('id','?')[:8]}")

        monitor_out = await self.monitor.process(raw_event)
        analyst_out = await self.analyst.analyze(monitor_out)
        rec_out     = await self.recommender.recommend(analyst_out)

        predictions = analyst_out["predictions"]
        rec_list    = [r.get("action","") for r in rec_out.get("recommendations",[])]

        # ── Persist top-level prediction to DB ────────────────────────────────
        pred_id = str(uuid.uuid4())
        Database.save_prediction({
            "id":                       pred_id,
            "trigger_event_id":         raw_event.get("id",""),
            "supplier_id":              raw_event.get("supplier_id",""),
            "peak_risk_score":          round(analyst_out["peak_risk"],4),
            "peak_risk_day":            7,
            "risk_level":               _level(analyst_out["peak_risk"]),
            "confidence":               0.75,
            "total_revenue_at_risk_usd":round(analyst_out["revenue_at_risk"],2),
            "affected_supplier_count":  analyst_out["affected_count"],
            "critical_count":           analyst_out["critical_count"],
            "high_count":               analyst_out["high_count"],
            "model_version":            analyst_out["model_version"],
            "recommendations":          rec_list,
            "urgency":                  rec_out["urgency"],
        })

        # ── Update per-supplier risk scores in DB ─────────────────────────────
        for sid, pred in predictions.items():
            Database.update_supplier_risk(sid, pred.get("peak_risk_score",0), pred.get("risk_level","low"))

        # ── Update event with downstream affected suppliers ───────────────────
        affected_ids = [sid for sid,p in predictions.items() if p.get("peak_risk_score",0)>0.2]
        Database.update_event_risk(raw_event.get("id",""), affected_ids, analyst_out["revenue_at_risk"])

        # ── Push live risk scores to all WebSocket clients ────────────────────
        ws_scores = {sid: {"score": p.get("peak_risk_score",0), "level": p.get("risk_level","low"),
                           "peak_day": p.get("peak_risk_day",7)}
                     for sid, p in predictions.items()}
        await ws_manager.broadcast_risk_update(ws_scores)
        await ws_manager.broadcast_prediction_complete({
            "event_id":    raw_event.get("id",""),
            "urgency":     rec_out["urgency"],
            "critical":    analyst_out["critical_count"],
            "high":        analyst_out["high_count"],
            "revenue":     analyst_out["revenue_at_risk"],
            "model":       analyst_out["model_version"],
            "summary":     rec_out.get("summary",""),
            "recommendations": rec_list[:3],
        })

        logger.info(f"ADK pipeline DONE | critical={analyst_out['critical_count']} "
                    f"rev=${analyst_out['revenue_at_risk']/1e9:.2f}B urgency={rec_out['urgency']}")
        return {"prediction_id": pred_id, "urgency": rec_out["urgency"],
                "affected_count": analyst_out["affected_count"]}


def _level(s: float) -> str:
    if s >= 0.70: return "critical"
    if s >= 0.40: return "high"
    if s >= 0.20: return "medium"
    return "low"


# Singleton pipeline registered as EventQueue handler
pipeline = ADKPipeline()

async def handle_disruption_event(event: dict) -> None:
    """Entry point called by EventQueue worker for every new disruption event."""
    await pipeline.run(event)
