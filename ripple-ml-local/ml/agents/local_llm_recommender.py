"""
LocalLLMRecommender — uses Ollama (local) instead of Gemini.

Setup:
  1. Install Ollama: https://ollama.com/download
  2. Pull a model: ollama pull llama3.2
  3. Ollama runs at http://localhost:11434 automatically

Falls back to a template if Ollama is not running.
"""
from __future__ import annotations
import json, logging
from typing import Dict, Any, Optional
import httpx
from ml.config import get_config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a supply chain risk analyst AI.
Given a disruption alert and GNN-predicted risk data, generate actionable rerouting recommendations.
Respond ONLY with valid JSON. No explanation outside the JSON.
Schema: {"urgency":"CRITICAL|HIGH|MEDIUM|LOW","summary":"one sentence","recommendations":[{"rank":1,"action":"...","rationale":"...","lead_time_days":30,"cost_impact":"+15%","confidence":0.8}],"key_risk_drivers":["..."],"monitoring_triggers":["..."]}"""


class LocalLLMRecommender:
    """Calls Ollama for structured recommendations. Falls back to templates."""

    def __init__(self):
        cfg = get_config().llm
        self.base_url    = cfg.base_url
        self.model       = cfg.model
        self.temperature = cfg.temperature
        self.max_tokens  = cfg.max_tokens

    def _is_ollama_running(self) -> bool:
        try:
            httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return True
        except Exception:
            return False

    def recommend(self, event: Dict[str, Any], risk_predictions: Dict[str, Any],
                  supplier_context: Optional[Dict] = None) -> Dict[str, Any]:
        if not self._is_ollama_running():
            logger.warning("Ollama not running — using template fallback")
            return self._template(event, risk_predictions)

        prompt = self._build_prompt(event, risk_predictions)
        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt,
                      "system": SYSTEM_PROMPT, "stream": False,
                      "options": {"temperature": self.temperature, "num_predict": self.max_tokens}},
                timeout=30.0,
            )
            resp.raise_for_status()
            raw = resp.json()["response"].strip()
            # Strip markdown fences if model wraps in ```json
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            result = json.loads(raw)
            result["generated_by"] = f"ollama/{self.model}"
            result["revenue_at_risk_usd"]       = self._rev(risk_predictions)
            result["affected_supplier_count"]   = len(risk_predictions)
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"LLM JSON parse error: {e} — using template")
            return self._template(event, risk_predictions)
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return self._template(event, risk_predictions)

    def _build_prompt(self, event, preds) -> str:
        top5 = sorted(preds.items(), key=lambda x: x[1].get("peak_risk_score",0), reverse=True)[:5]
        critical = sum(1 for _,p in preds.items() if p.get("risk_level")=="critical")
        return f"""
DISRUPTION: {event.get('disruption_type')} at {event.get('country','unknown')}
Severity: {event.get('severity',0.7):.0%} | Capacity: {event.get('affected_capacity_pct',30):.0f}%
Description: {event.get('description','')}
Critical nodes: {critical} | Total analysed: {len(preds)}
Revenue at risk: ${self._rev(preds)/1e9:.2f}B
Top 5 risk: {json.dumps([{"id":k[:8],"peak":round(v.get('peak_risk_score',0),2),"day":v.get('peak_risk_day',7)} for k,v in top5])}
Generate 3-4 ranked recommendations.
""".strip()

    def _rev(self, preds):
        return sum(p.get("peak_risk_score",0) * 5e8 for p in preds.values())

    def _template(self, event, preds) -> Dict[str, Any]:
        sev = event.get("severity", 0.5)
        cat = event.get("category","components")
        return {
            "urgency": "CRITICAL" if sev > 0.7 else "HIGH" if sev > 0.4 else "MEDIUM",
            "generated_by": "template-fallback",
            "summary": f"Disruption in {event.get('country','region')} affecting {cat} supply.",
            "recommendations": [
                {"rank":1,"action":f"Activate backup {cat} suppliers in Malaysia and Vietnam",
                 "rationale":"Geographic diversification reduces single-region exposure",
                 "lead_time_days":21,"cost_impact":"+12%","confidence":0.80},
                {"rank":2,"action":"Increase Tier-1 safety stock by 30% immediately",
                 "rationale":"Buffer while alternate suppliers are onboarded",
                 "lead_time_days":3,"cost_impact":"+8% carrying cost","confidence":0.90},
                {"rank":3,"action":f"Issue dual-sourcing RFQ for {cat} to 5 pre-qualified vendors",
                 "rationale":"Long-term resilience against concentration risk",
                 "lead_time_days":45,"cost_impact":"+5%","confidence":0.75},
            ],
            "key_risk_drivers":["Single-region concentration","Sole-source dependency","High-severity Tier-3 event"],
            "monitoring_triggers":["Watch Tier-2 lead times for >10% increase","Monitor alternate port capacity"],
            "revenue_at_risk_usd": self._rev(preds),
            "affected_supplier_count": len(preds),
        }
