"""Prediction analytics routes."""
from fastapi import APIRouter, HTTPException
from app.services.database import Database
from app.models.schemas import RiskSummary

router = APIRouter()


@router.get("/summary", response_model=RiskSummary)
def summary():
    data = Database.get_risk_summary()
    # SQLite returns None for aggregate functions on empty tables — coerce to 0
    return RiskSummary(
        total_revenue_at_risk_usd=float(data.get("total_revenue_at_risk_usd") or 0),
        affected_suppliers=int(data.get("affected_suppliers") or 0),
        avg_risk_score=float(data.get("avg_risk_score") or 0),
        max_risk_score=float(data.get("max_risk_score") or 0),
        critical_count=int(data.get("critical_count") or 0),
        high_count=int(data.get("high_count") or 0),
    )


@router.get("/tier-breakdown")
def tier_breakdown():
    return Database.get_tier_risk_breakdown()


@router.get("/event/{event_id}")
def predictions_for_event(event_id: str):
    preds = Database.get_predictions_for_event(event_id)
    if not preds:
        raise HTTPException(404, "No predictions for this event")
    return preds