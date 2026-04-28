"""Pydantic v2 schemas — request/response models for all routes."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr


# ── Enums ─────────────────────────────────────────────────────────────────────

class SupplierTier(str, Enum):
    TIER_3 = "tier_3"; TIER_2 = "tier_2"; TIER_1 = "tier_1"; OEM = "oem"

class RiskLevel(str, Enum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class DisruptionType(str, Enum):
    FACTORY_SHUTDOWN    = "factory_shutdown"
    NATURAL_DISASTER    = "natural_disaster"
    LOGISTICS_DELAY     = "logistics_delay"
    QUALITY_ISSUE       = "quality_issue"
    GEOPOLITICAL        = "geopolitical"
    FINANCIAL           = "financial"
    CAPACITY_CONSTRAINT = "capacity_constraint"

class EventStatus(str, Enum):
    ACTIVE = "active"; MONITORING = "monitoring"; RESOLVED = "resolved"


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str


# ── Supplier ──────────────────────────────────────────────────────────────────

class SupplierCreate(BaseModel):
    name: str; tier: SupplierTier; country: str; region: str; category: str
    annual_revenue_usd: float; employee_count: int
    latitude: float; longitude: float

class Supplier(SupplierCreate):
    id: str
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    historical_delay_rate: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    class Config: use_enum_values = True


# ── Supply Edge ───────────────────────────────────────────────────────────────

class SupplyEdge(BaseModel):
    id: str; source_supplier_id: str; target_supplier_id: str
    component_category: str; lead_time_days: int
    dependency_weight: float; annual_volume_usd: float; is_sole_source: bool = False


# ── Disruption Event ──────────────────────────────────────────────────────────

class DisruptionEventCreate(BaseModel):
    supplier_id: str
    disruption_type: DisruptionType
    severity: float = Field(..., ge=0.0, le=1.0)
    description: str
    affected_capacity_pct: float = Field(..., ge=0.0, le=100.0)
    source: str = "manual"
    country: str = ""; category: str = ""

class DisruptionEvent(DisruptionEventCreate):
    id: str
    status: EventStatus = EventStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    downstream_suppliers_affected: List[str] = []
    estimated_revenue_at_risk_usd: float = 0.0
    class Config: use_enum_values = True


# ── Prediction ────────────────────────────────────────────────────────────────

class NodePrediction(BaseModel):
    supplier_id: str; risk_scores: List[float]
    peak_risk_score: float; peak_risk_day: int
    risk_level: str; confidence: float

class PredictionRequest(BaseModel):
    trigger_event_id: str; horizon_days: int = 45

class PredictionResponse(BaseModel):
    event_id: str
    predictions: List[NodePrediction]
    total_revenue_at_risk_usd: float
    affected_supplier_count: int
    critical_count: int; high_count: int
    model_version: str; inference_latency_ms: float
    recommendations: List[str] = []
    urgency: str = "MEDIUM"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Graph ─────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str; name: str; tier: str; country: str
    risk_score: float; risk_level: str
    latitude: float; longitude: float
    annual_revenue_usd: float; category: str

class GraphEdge(BaseModel):
    id: str; source: str; target: str
    lead_time_days: int; dependency_weight: float; is_sole_source: bool

class SupplyChainGraph(BaseModel):
    nodes: List[GraphNode]; edges: List[GraphEdge]
    total_nodes: int; total_edges: int
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ── Analytics ─────────────────────────────────────────────────────────────────

class RiskSummary(BaseModel):
    total_revenue_at_risk_usd: float = 0.0
    affected_suppliers: int = 0
    avg_risk_score: float = 0.0
    max_risk_score: float = 0.0
    critical_count: int = 0; high_count: int = 0

class TierRisk(BaseModel):
    tier: str; supplier_count: int; avg_risk: float
    total_revenue_at_risk_usd: float


# ── Generic ───────────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool = True; message: str = "OK"; data: Optional[Any] = None

class HealthResponse(BaseModel):
    status: str; version: str; db_connected: bool; ml_server_reachable: bool
