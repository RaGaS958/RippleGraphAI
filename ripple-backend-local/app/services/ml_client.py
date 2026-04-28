"""
ML client — calls the local ML prediction server (replaces Vertex AI).
Sends graph payload to http://localhost:8081/predict and returns predictions.
"""
from __future__ import annotations
import logging, time
from typing import Dict, List, Optional, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.database import Database

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "raw_silicon":0,"rare_earth_metals":1,"specialty_chemicals":2,"advanced_glass":3,
    "photoresists":4,"wafers":5,"pcb_substrate":6,"passive_components":7,
    "display_panels":8,"battery_cells":9,"semiconductors":10,"memory_chips":11,
    "power_management_ics":12,"displays":13,"battery_packs":14,"consumer_electronics":15,
    "automotive":16,"industrial_equipment":17,"aerospace":18,"medical_devices":19,
}
TIER_MAP   = {"tier_3":0,"tier_2":1,"tier_1":2,"oem":3}
REGION_MAP = {"Asia Pacific":0,"Europe":1,"North America":2,"South Asia":3,"Other":4}


def _node_features(s: dict) -> List[float]:
    """Build 16-dim feature vector for a supplier dict."""
    import numpy as np
    tier_n = TIER_MAP.get(s.get("tier","tier_3"),0)/3.0
    cat_n  = CATEGORY_MAP.get(s.get("category","semiconductors"),0)/max(len(CATEGORY_MAP)-1,1)
    reg_n  = REGION_MAP.get(s.get("region","Other"),4)/4.0
    rev_n  = np.log1p(max(float(s.get("annual_revenue_usd",1e8)),1))/np.log1p(5e9)
    emp_n  = np.log1p(max(float(s.get("employee_count",1000)),1))/np.log1p(100_000)
    lat_n  = (float(s.get("latitude",0))+90)/180.0
    lon_n  = (float(s.get("longitude",0))+180)/360.0
    delay  = float(s.get("historical_delay_rate",0.05))
    risk   = float(s.get("risk_score",0.0))
    return [tier_n,cat_n,reg_n,rev_n,emp_n,lat_n,lon_n,delay,risk,0.0,0.0,0.0,0.0,0.0,0.0,0.0]


def _edge_features(e: dict) -> List[float]:
    """Build 6-dim feature vector for a supply edge dict."""
    import numpy as np
    lead  = min(int(e.get("lead_time_days",30)),120)/120.0
    wt    = float(e.get("dependency_weight",0.5))
    vol   = np.log1p(max(float(e.get("annual_volume_usd",1e6)),1))/np.log1p(5e8)
    sole  = float(bool(e.get("is_sole_source",False)))
    src_t = TIER_MAP.get(e.get("src_tier","tier_3"),0)
    tgt_t = TIER_MAP.get(e.get("tgt_tier","tier_2"),1)
    delta = (tgt_t - src_t + 3)/6.0
    cat   = CATEGORY_MAP.get(e.get("component_category","semiconductors"),0)/max(len(CATEGORY_MAP)-1,1)
    return [lead, wt, vol, sole, delta, cat]


class MLClient:
    """Calls the local ML prediction server and returns structured predictions."""

    def __init__(self):
        cfg = self._cfg()
        self._predict_url = f"{cfg.ML_SERVER_URL}{cfg.ML_PREDICT_PATH}"
        self._health_url  = f"{cfg.ML_SERVER_URL}/health"
        self._timeout     = cfg.ML_TIMEOUT_SEC

    @staticmethod
    def _cfg():
        return get_settings()

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(self._health_url)
                return r.status_code == 200
        except Exception:
            return False

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def predict(self, event: dict, horizon_days: int = 45) -> dict:
        """
        Fetch all suppliers + edges from DB, build graph payload,
        call ML server, return raw prediction dict.
        """
        suppliers = Database.list_suppliers()
        edges     = Database.list_edges()

        if not suppliers:
            logger.warning("No suppliers in DB — returning empty predictions")
            return {"predictions": {}, "model_version": "no-data", "inference_ms": 0}

        # Set trigger node risk score from event severity
        trigger_id = event.get("supplier_id")
        for s in suppliers:
            if s["id"] == trigger_id:
                s["risk_score"] = float(event.get("severity", 0.7))
                break

        # Build tier lookup for edge features
        tier_lookup = {s["id"]: s["tier"] for s in suppliers}

        nodes = [{"id": s["id"], "features": _node_features(s),
                  "tier": s["tier"], "risk_score": float(s.get("risk_score",0))}
                 for s in suppliers]

        graph_edges = []
        for e in edges:
            src = e.get("source_supplier_id","")
            tgt = e.get("target_supplier_id","")
            if src not in tier_lookup or tgt not in tier_lookup:
                continue
            ef = _edge_features({**e, "src_tier": tier_lookup[src], "tgt_tier": tier_lookup[tgt]})
            graph_edges.append({
                "source": src, "target": tgt, "features": ef,
                "dependency_weight": float(e.get("dependency_weight",0.5)),
                "is_sole_source": bool(e.get("is_sole_source",False)),
            })

        payload = {
            "graph_nodes": nodes,
            "graph_edges": graph_edges,
            "trigger_event_id": event.get("id",""),
            "horizon_days": horizon_days,
        }

        t0 = time.time()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(self._predict_url, json=payload)
            resp.raise_for_status()
            result = resp.json()

        result["inference_ms"] = round((time.time()-t0)*1000, 2)
        logger.info(f"ML prediction done in {result['inference_ms']}ms | "
                    f"model={result.get('model_version','?')} | "
                    f"nodes={len(nodes)}")
        return result
