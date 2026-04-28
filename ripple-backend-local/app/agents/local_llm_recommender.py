"""Local Ollama LLM recommender — same as ML team's but lives in backend agents."""
from __future__ import annotations
import json, logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

SYSTEM = """You are a supply chain risk analyst AI.
Given a disruption alert and risk prediction data, generate 3-5 ranked rerouting recommendations.
Respond ONLY with valid JSON. Schema:
{"urgency":"CRITICAL|HIGH|MEDIUM|LOW","summary":"one sentence","recommendations":[{"rank":1,"action":"...","rationale":"...","lead_time_days":30,"cost_impact":"+15%","confidence":0.8}],"key_risk_drivers":["..."]}"""

OLLAMA_URL = "http://localhost:11434"
MODEL      = "llama3.2"


class LocalLLMRecommender:
    def _running(self) -> bool:
        try:
            httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2.0)
            return True
        except Exception:
            return False

    def recommend(self, event: dict, predictions: Dict[str, Any]) -> dict:
        if not self._running():
            return self._template(event, predictions)
        sev  = float(event.get("severity",0.5))
        cat  = event.get("category","components")
        crit = sum(1 for p in predictions.values() if p.get("risk_level")=="critical")
        rev  = sum(p.get("peak_risk_score",0)*5e8 for p in predictions.values())
        prompt = (f"Disruption: {event.get('disruption_type')} at {event.get('country','?')} "
                  f"severity={sev:.0%} capacity_affected={event.get('affected_capacity_pct',30):.0f}% "
                  f"category={cat} critical_nodes={crit} revenue_at_risk=${rev/1e9:.2f}B. "
                  "Generate 3-4 ranked rerouting recommendations.")
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/generate",
                           json={"model":MODEL,"prompt":prompt,"system":SYSTEM,
                                 "stream":False,"options":{"temperature":0.2,"num_predict":800}},
                           timeout=25.0)
            r.raise_for_status()
            raw = r.json()["response"].strip()
            if raw.startswith("```"): raw = raw.split("```")[1]; raw = raw[4:] if raw.startswith("json") else raw
            out = json.loads(raw)
            out["generated_by"] = f"ollama/{MODEL}"
            return out
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
            return self._template(event, predictions)

    def _template(self, event: dict, predictions: dict) -> dict:
        sev = float(event.get("severity",0.5))
        cat = event.get("category","components")
        rev = sum(p.get("peak_risk_score",0)*5e8 for p in predictions.values())
        return {
            "urgency": "CRITICAL" if sev>0.7 else "HIGH" if sev>0.4 else "MEDIUM",
            "generated_by": "template-fallback",
            "summary": f"Disruption in {event.get('country','region')} affecting {cat}. Immediate action required.",
            "recommendations": [
                {"rank":1,"action":f"Activate backup {cat} suppliers in Malaysia/Vietnam",
                 "rationale":"Geographic diversification","lead_time_days":21,"cost_impact":"+12%","confidence":0.80},
                {"rank":2,"action":"Increase Tier-1 safety stock by 30% immediately",
                 "rationale":"Buffer while alternates onboard","lead_time_days":3,"cost_impact":"+8%","confidence":0.90},
                {"rank":3,"action":f"Issue dual-source RFQ for {cat} to 5 vendors",
                 "rationale":"Long-term resilience","lead_time_days":45,"cost_impact":"+5%","confidence":0.75},
            ],
            "key_risk_drivers": ["Single-region concentration","Sole-source dependency","High-severity Tier-3 event"],
        }
