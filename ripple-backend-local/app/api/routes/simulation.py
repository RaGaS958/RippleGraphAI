"""
Simulation route — injects scenario-specific predictions into DB
and broadcasts via WebSocket so Graph + Analytics update live.
Drop this at: ripple-backend-local/app/api/routes/simulation.py
"""
import uuid, logging, random, math
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.services.database import Database
from app.services.websocket_manager import ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Scenario configs ──────────────────────────────────────────────────────────
SCENARIO_CONFIG = {
    "tsmc_shutdown": {
        "severity": 0.93,
        "tier_risk": {"tier_3": 0.92, "tier_2": 0.78, "tier_1": 0.61, "oem": 0.44},
        "revenue_multiplier": 2.3,
        "peak_day": 7,
        "disruption_type": "factory_shutdown",
        "urgency": "CRITICAL",
        "country": "Taiwan",
        "category": "raw_silicon",
        "description": "TSMC Fab 18 emergency shutdown — advanced node production halted.",
        "recommendations": [
            "Activate backup raw silicon suppliers in Malaysia/Vietnam immediately",
            "Increase Tier-1 semiconductor safety stock by 45% within 48 hours",
            "Issue emergency dual-source RFQ to 8 pre-qualified TSMC alternates",
            "Escalate to C-suite — estimated $2.3B revenue at risk over 6-8 weeks",
            "Initiate logistics pre-positioning at alternative fab sites",
        ],
    },
    "rare_earth_ban": {
        "severity": 0.78,
        "tier_risk": {"tier_3": 0.81, "tier_2": 0.65, "tier_1": 0.48, "oem": 0.32},
        "revenue_multiplier": 1.1,
        "peak_day": 14,
        "disruption_type": "geopolitical",
        "urgency": "HIGH",
        "country": "China",
        "category": "rare_earth_metals",
        "description": "Chinese export controls on 7 rare earth elements. 6-month disruption.",
        "recommendations": [
            "Activate strategic rare earth reserves — 90-day buffer available",
            "Accelerate supplier diversification to Australian/Canadian rare earth sources",
            "Lock in forward contracts with non-Chinese rare earth suppliers",
            "Review passive component BOM for rare earth substitution opportunities",
        ],
    },
    "port_strike": {
        "severity": 0.65,
        "tier_risk": {"tier_3": 0.68, "tier_2": 0.71, "tier_1": 0.52, "oem": 0.38},
        "revenue_multiplier": 0.8,
        "peak_day": 5,
        "disruption_type": "logistics_delay",
        "urgency": "HIGH",
        "country": "Japan",
        "category": "semiconductors",
        "description": "Indefinite dockworker strike — 10,000 containers backlogged.",
        "recommendations": [
            "Reroute shipments via Osaka and Nagoya ports immediately",
            "Charter air freight for highest-priority Tier-1 components",
            "Increase in-transit inventory buffers for Japan-sourced parts by 30%",
            "Activate contingency logistics partners in South Korea (Busan port)",
        ],
    },
    "malaysia_flood": {
        "severity": 0.55,
        "tier_risk": {"tier_3": 0.58, "tier_2": 0.62, "tier_1": 0.41, "oem": 0.25},
        "revenue_multiplier": 0.6,
        "peak_day": 10,
        "disruption_type": "natural_disaster",
        "urgency": "MEDIUM",
        "country": "Malaysia",
        "category": "wafers",
        "description": "Penang flooding: 6 semiconductor fabs at 30% capacity.",
        "recommendations": [
            "Shift wafer orders to Taiwan and South Korean fab partners",
            "Deploy 45-day safety stock protocol for affected PCB substrates",
            "Pre-position recovery team and equipment at Penang industrial zone",
        ],
    },
    "quality_recall": {
        "severity": 0.48,
        "tier_risk": {"tier_3": 0.51, "tier_2": 0.55, "tier_1": 0.38, "oem": 0.22},
        "revenue_multiplier": 0.5,
        "peak_day": 12,
        "disruption_type": "quality_issue",
        "urgency": "MEDIUM",
        "country": "South Korea",
        "category": "battery_cells",
        "description": "Safety recall: 12M battery cells. Thermal runaway risk.",
        "recommendations": [
            "Halt incoming battery cell shipments from 3 affected SKUs immediately",
            "Initiate root-cause analysis — request supplier CAPA within 72 hours",
            "Source replacement cells from Japanese backup suppliers (Panasonic/TDK)",
        ],
    },
    "nominal": {
        "severity": 0.12,
        "tier_risk": {"tier_3": 0.10, "tier_2": 0.12, "tier_1": 0.08, "oem": 0.05},
        "revenue_multiplier": 0.05,
        "peak_day": 45,
        "disruption_type": "logistics_delay",
        "urgency": "LOW",
        "country": "Japan",
        "category": "passive_components",
        "description": "Minor shipping delays. All suppliers within SLA parameters.",
        "recommendations": [
            "Continue normal operations — no immediate action required",
            "Monitor lead times for minor passive component delays",
        ],
    },
}


class SimulationRequest(BaseModel):
    scenario_id: str
    supplier_id: str | None = None


class SimulationResult(BaseModel):
    event_id: str
    scenario_id: str
    urgency: str
    total_suppliers_affected: int
    critical_count: int
    high_count: int
    total_revenue_at_risk_usd: float
    peak_risk_day: int
    recommendations: list[str]
    risk_scores: dict[str, float]   # supplier_id → risk score (for WebSocket)


@router.post("/run", response_model=SimulationResult)
async def run_simulation(
    req: SimulationRequest,
    background_tasks: BackgroundTasks,
    _=Depends(get_current_user),
):
    cfg = SCENARIO_CONFIG.get(req.scenario_id)
    if not cfg:
        raise HTTPException(400, f"Unknown scenario: {req.scenario_id}")

    # ── 1. Fetch all suppliers ────────────────────────────────────────────────
    all_suppliers = Database.list_suppliers()
    if not all_suppliers:
        raise HTTPException(422, "No suppliers in DB. Run seed_db.py first.")

    # ── 2. Create disruption event ────────────────────────────────────────────
    # Find target supplier (match tier from scenario or use provided id)
    if req.supplier_id:
        target = next((s for s in all_suppliers if s["id"] == req.supplier_id), None)
    else:
        tier_map = {"tsmc_shutdown": "tier_3", "rare_earth_ban": "tier_3",
                    "port_strike": "tier_2", "malaysia_flood": "tier_2",
                    "quality_recall": "tier_2", "nominal": "tier_2"}
        target_tier = tier_map.get(req.scenario_id, "tier_2")
        candidates = [s for s in all_suppliers if s.get("tier") == target_tier]
        target = candidates[0] if candidates else all_suppliers[0]

    eid = str(uuid.uuid4())
    event_doc = {
        "id": eid,
        "supplier_id": target["id"],
        "disruption_type": cfg["disruption_type"],
        "severity": cfg["severity"],
        "description": cfg["description"],
        "affected_capacity_pct": int(cfg["severity"] * 100),
        "source": "simulation",
        "country": cfg["country"],
        "category": cfg["category"],
        "status": "active",
    }
    Database.create_event(event_doc)

    # ── 3. Generate predictions for every supplier ────────────────────────────
    risk_scores: dict[str, float] = {}
    critical = high = 0
    total_rev = 0.0

    for sup in all_suppliers:
        tier = sup.get("tier", "tier_2")
        base_risk = cfg["tier_risk"].get(tier, 0.3)
        # Add realistic noise
        noise = random.uniform(-0.08, 0.08)
        risk = min(0.99, max(0.01, base_risk + noise))
        level = ("critical" if risk > 0.75 else
                 "high"     if risk > 0.50 else
                 "medium"   if risk > 0.25 else "low")
        rev = sup.get("annual_revenue_usd", 1e9) * risk * 0.045  # ~4.5% of annual rev at risk

        if level == "critical": critical += 1
        elif level == "high": high += 1
        total_rev += rev
        risk_scores[sup["id"]] = risk

        Database.save_prediction({
            "id": str(uuid.uuid4()),
            "trigger_event_id": eid,
            "supplier_id": sup["id"],
            "peak_risk_score": round(risk, 4),
            "peak_risk_day": cfg["peak_day"] + random.randint(-2, 4),
            "risk_level": level,
            "confidence": round(random.uniform(0.82, 0.97), 3),
            "total_revenue_at_risk_usd": round(rev, 2),
            "affected_supplier_count": len(all_suppliers),
            "critical_count": critical,
            "high_count": high,
            "model_version": "gnn-v1",
            "recommendations": cfg["recommendations"],
            "urgency": cfg["urgency"],
            "created_at": datetime.utcnow().isoformat(),
        })

    result = SimulationResult(
        event_id=eid,
        scenario_id=req.scenario_id,
        urgency=cfg["urgency"],
        total_suppliers_affected=len(all_suppliers),
        critical_count=critical,
        high_count=high,
        total_revenue_at_risk_usd=round(total_rev, 2),
        peak_risk_day=cfg["peak_day"],
        recommendations=cfg["recommendations"],
        risk_scores=risk_scores,
    )

    # ── 4. Broadcast WebSocket updates async ──────────────────────────────────
    background_tasks.add_task(_broadcast, result, cfg)

    logger.info("Simulation %s complete — %d predictions saved, urgency=%s",
                req.scenario_id, len(all_suppliers), cfg["urgency"])
    return result


async def _broadcast(result: SimulationResult, cfg: dict):
    """Push risk scores + prediction_complete to all WS clients."""
    risk_data = {sid: {"score": score,
                       "level": ("critical" if score > 0.75 else
                                 "high"     if score > 0.50 else
                                 "medium"   if score > 0.25 else "low"),
                       "peak_day": cfg["peak_day"]}
                 for sid, score in result.risk_scores.items()}

    await ws_manager.broadcast_risk_update(risk_data)
    await ws_manager.broadcast_prediction_complete({
        "event_id": result.event_id,
        "urgency": result.urgency,
        "critical": result.critical_count,
        "high": result.high_count,
        "revenue": result.total_revenue_at_risk_usd,
        "model": "gnn-v1 (simulation)",
        "summary": cfg["description"],
        "recommendations": cfg["recommendations"],
    })

@router.post("/reset")
async def reset_simulation(_=Depends(get_current_user)):
    """Reset all predictions/events to nominal state and broadcast via WebSocket."""
    Database.reset_all_predictions_and_events()
    
    # Broadcast nominal risk scores for all suppliers
    all_suppliers = Database.list_suppliers()
    import random
    risk_data = {
        s["id"]: {"score": round(random.uniform(0.03, 0.12), 3), "level": "low", "peak_day": 45}
        for s in all_suppliers
    }
    await ws_manager.broadcast_risk_update(risk_data)
    await ws_manager.broadcast_prediction_complete({
        "event_id": "reset",
        "urgency": "LOW",
        "critical": 0,
        "high": 0,
        "revenue": 0,
        "model": "reset",
        "summary": "System reset to nominal. All predictions cleared.",
        "recommendations": ["All systems nominal. Continue monitoring."],
    })
    return {"status": "reset", "suppliers_reset": len(all_suppliers)}