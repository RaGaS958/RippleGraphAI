"""
SQLite database service — replaces Firestore + BigQuery entirely.
Single file, zero setup, works offline.

Tables:
  users               — local user accounts (replaces Firebase Auth)
  suppliers           — supply chain nodes
  supply_edges        — dependency relationships
  disruption_events   — disruption alerts
  risk_predictions    — GNN/stub prediction results
"""
from __future__ import annotations
import json, logging, uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Database:
    _engine: Optional[Engine] = None

    @classmethod
    def init(cls) -> None:
        cfg = get_settings()
        Path(cfg.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        cls._engine = create_engine(
            f"sqlite:///{cfg.DB_PATH}",
            echo=cfg.DB_ECHO,
            connect_args={"check_same_thread": False},
        )
        cls._create_tables()
        logger.info(f"SQLite ready at {cfg.DB_PATH}")

    @classmethod
    def engine(cls) -> Engine:
        if cls._engine is None:
            cls.init()
        return cls._engine

    @classmethod
    def _create_tables(cls) -> None:
        with cls.engine().connect() as c:
            c.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, name TEXT DEFAULT '',
                created_at TEXT
            )"""))
            c.execute(text("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id TEXT PRIMARY KEY, name TEXT, tier TEXT,
                country TEXT, region TEXT, category TEXT,
                annual_revenue_usd REAL, employee_count INTEGER,
                latitude REAL, longitude REAL,
                historical_delay_rate REAL DEFAULT 0.0,
                risk_score REAL DEFAULT 0.0,
                risk_level TEXT DEFAULT 'low',
                created_at TEXT
            )"""))
            c.execute(text("""
            CREATE TABLE IF NOT EXISTS supply_edges (
                id TEXT PRIMARY KEY,
                source_supplier_id TEXT, target_supplier_id TEXT,
                component_category TEXT, lead_time_days INTEGER,
                dependency_weight REAL, annual_volume_usd REAL,
                is_sole_source INTEGER DEFAULT 0
            )"""))
            c.execute(text("""
            CREATE TABLE IF NOT EXISTS disruption_events (
                id TEXT PRIMARY KEY, supplier_id TEXT,
                disruption_type TEXT, severity REAL,
                description TEXT, affected_capacity_pct REAL,
                source TEXT DEFAULT 'manual',
                country TEXT DEFAULT '', category TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                estimated_revenue_at_risk_usd REAL DEFAULT 0.0,
                downstream_affected TEXT DEFAULT '[]',
                created_at TEXT, resolved_at TEXT
            )"""))
            c.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_predictions (
                id TEXT PRIMARY KEY, trigger_event_id TEXT,
                supplier_id TEXT, peak_risk_score REAL,
                peak_risk_day INTEGER, risk_level TEXT,
                confidence REAL, total_revenue_at_risk_usd REAL,
                affected_supplier_count INTEGER, critical_count INTEGER,
                high_count INTEGER, model_version TEXT,
                recommendations TEXT DEFAULT '[]',
                urgency TEXT DEFAULT 'MEDIUM',
                created_at TEXT
            )"""))

            # Indexes
            for stmt in [
                "CREATE INDEX IF NOT EXISTS idx_sup_tier ON suppliers(tier)",
                "CREATE INDEX IF NOT EXISTS idx_edge_src ON supply_edges(source_supplier_id)",
                "CREATE INDEX IF NOT EXISTS idx_evt_status ON disruption_events(status, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_pred_event ON risk_predictions(trigger_event_id)",
            ]:
                c.execute(text(stmt))
            c.commit()

    # ── Users ──────────────────────────────────────────────────────────────────

    @classmethod
    def create_user(cls, email: str, password_hash: str, name: str = "") -> dict:
        uid = str(uuid.uuid4())
        with cls.engine().begin() as c:
            c.execute(text(
                "INSERT INTO users (id,email,password_hash,name,created_at) "
                "VALUES (:id,:email,:ph,:name,:ts)"
            ), {"id": uid, "email": email, "ph": password_hash,
                "name": name, "ts": datetime.utcnow().isoformat()})
        return {"id": uid, "email": email, "name": name}

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[dict]:
        with cls.engine().connect() as c:
            row = c.execute(text("SELECT * FROM users WHERE email=:e"), {"e": email}).fetchone()
            return dict(row._mapping) if row else None

    # ── Suppliers ──────────────────────────────────────────────────────────────

    @classmethod
    def create_supplier(cls, data: dict) -> dict:
        data.setdefault("id", str(uuid.uuid4()))
        data.setdefault("created_at", datetime.utcnow().isoformat())
        data.setdefault("risk_score", 0.0)
        data.setdefault("risk_level", "low")
        data.setdefault("historical_delay_rate", 0.0)
        with cls.engine().begin() as c:
            c.execute(text("""
                INSERT OR REPLACE INTO suppliers
                (id,name,tier,country,region,category,annual_revenue_usd,
                 employee_count,latitude,longitude,historical_delay_rate,
                 risk_score,risk_level,created_at)
                VALUES (:id,:name,:tier,:country,:region,:category,:annual_revenue_usd,
                        :employee_count,:latitude,:longitude,:historical_delay_rate,
                        :risk_score,:risk_level,:created_at)
            """), data)
        return data

    @classmethod
    def get_supplier(cls, sid: str) -> Optional[dict]:
        with cls.engine().connect() as c:
            row = c.execute(text("SELECT * FROM suppliers WHERE id=:id"), {"id": sid}).fetchone()
            return dict(row._mapping) if row else None

    @classmethod
    def list_suppliers(cls, tier: Optional[str] = None, limit: int = 200) -> List[dict]:
        q = "SELECT * FROM suppliers"
        params: dict = {"limit": limit}
        if tier:
            q += " WHERE tier=:tier"
            params["tier"] = tier
        q += " ORDER BY tier, name LIMIT :limit"
        with cls.engine().connect() as c:
            rows = c.execute(text(q), params).fetchall()
            return [dict(r._mapping) for r in rows]

    @classmethod
    def update_supplier_risk(cls, sid: str, risk_score: float, risk_level: str) -> None:
        with cls.engine().begin() as c:
            c.execute(text(
                "UPDATE suppliers SET risk_score=:s, risk_level=:l WHERE id=:id"
            ), {"s": risk_score, "l": risk_level, "id": sid})

    @classmethod
    def bulk_upsert_suppliers(cls, suppliers: List[dict]) -> int:
        for s in suppliers:
            cls.create_supplier(s)
        return len(suppliers)

    # ── Supply Edges ───────────────────────────────────────────────────────────

    @classmethod
    def list_edges(cls) -> List[dict]:
        with cls.engine().connect() as c:
            rows = c.execute(text("SELECT * FROM supply_edges")).fetchall()
            return [dict(r._mapping) for r in rows]

    @classmethod
    def get_downstream_ids(cls, sid: str) -> List[str]:
        with cls.engine().connect() as c:
            rows = c.execute(
                text("SELECT target_supplier_id FROM supply_edges WHERE source_supplier_id=:id"),
                {"id": sid}
            ).fetchall()
            return [r[0] for r in rows]

    @classmethod
    def bulk_upsert_edges(cls, edges: List[dict]) -> int:
        with cls.engine().begin() as c:
            for e in edges:
                c.execute(text("""
                    INSERT OR REPLACE INTO supply_edges
                    (id,source_supplier_id,target_supplier_id,component_category,
                     lead_time_days,dependency_weight,annual_volume_usd,is_sole_source)
                    VALUES (:id,:source_supplier_id,:target_supplier_id,:component_category,
                            :lead_time_days,:dependency_weight,:annual_volume_usd,:is_sole_source)
                """), e)
        return len(edges)

    # ── Disruption Events ──────────────────────────────────────────────────────

    @classmethod
    def create_event(cls, data: dict) -> dict:
        data.setdefault("id", str(uuid.uuid4()))
        data.setdefault("status", "active")
        data.setdefault("created_at", datetime.utcnow().isoformat())
        data.setdefault("resolved_at", None)
        data.setdefault("estimated_revenue_at_risk_usd", 0.0)
        data.setdefault("downstream_affected", "[]")
        with cls.engine().begin() as c:
            c.execute(text("""
                INSERT INTO disruption_events
                (id,supplier_id,disruption_type,severity,description,
                 affected_capacity_pct,source,country,category,status,
                 estimated_revenue_at_risk_usd,downstream_affected,created_at,resolved_at)
                VALUES (:id,:supplier_id,:disruption_type,:severity,:description,
                        :affected_capacity_pct,:source,:country,:category,:status,
                        :estimated_revenue_at_risk_usd,:downstream_affected,:created_at,:resolved_at)
            """), data)
        return data

    @classmethod
    def get_event(cls, eid: str) -> Optional[dict]:
        with cls.engine().connect() as c:
            row = c.execute(text("SELECT * FROM disruption_events WHERE id=:id"), {"id": eid}).fetchone()
            return dict(row._mapping) if row else None

    @classmethod
    def list_active_events(cls, limit: int = 50) -> List[dict]:
        with cls.engine().connect() as c:
            rows = c.execute(text(
                "SELECT * FROM disruption_events WHERE status='active' "
                "ORDER BY created_at DESC LIMIT :lim"
            ), {"lim": limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @classmethod
    def list_all_events(cls, limit: int = 100) -> List[dict]:
        with cls.engine().connect() as c:
            rows = c.execute(text(
                "SELECT * FROM disruption_events ORDER BY created_at DESC LIMIT :lim"
            ), {"lim": limit}).fetchall()
            return [dict(r._mapping) for r in rows]

    @classmethod
    def resolve_event(cls, eid: str) -> None:
        with cls.engine().begin() as c:
            c.execute(text(
                "UPDATE disruption_events SET status='resolved', resolved_at=:ts WHERE id=:id"
            ), {"ts": datetime.utcnow().isoformat(), "id": eid})

    @classmethod
    def update_event_risk(cls, eid: str, affected: List[str], rev: float) -> None:
        with cls.engine().begin() as c:
            c.execute(text(
                "UPDATE disruption_events SET downstream_affected=:da, "
                "estimated_revenue_at_risk_usd=:rev WHERE id=:id"
            ), {"da": json.dumps(affected), "rev": rev, "id": eid})

    # ── Risk Predictions ───────────────────────────────────────────────────────

    @classmethod
    def save_prediction(cls, data: dict) -> None:
        data.setdefault("id", str(uuid.uuid4()))
        data.setdefault("created_at", datetime.utcnow().isoformat())
        if isinstance(data.get("recommendations"), list):
            data["recommendations"] = json.dumps(data["recommendations"])
        with cls.engine().begin() as c:
            c.execute(text("""
                INSERT OR REPLACE INTO risk_predictions
                (id,trigger_event_id,supplier_id,peak_risk_score,peak_risk_day,
                 risk_level,confidence,total_revenue_at_risk_usd,
                 affected_supplier_count,critical_count,high_count,
                 model_version,recommendations,urgency,created_at)
                VALUES (:id,:trigger_event_id,:supplier_id,:peak_risk_score,:peak_risk_day,
                        :risk_level,:confidence,:total_revenue_at_risk_usd,
                        :affected_supplier_count,:critical_count,:high_count,
                        :model_version,:recommendations,:urgency,:created_at)
            """), data)

    @classmethod
    def get_predictions_for_event(cls, eid: str) -> List[dict]:
        with cls.engine().connect() as c:
            rows = c.execute(text(
                "SELECT * FROM risk_predictions WHERE trigger_event_id=:eid ORDER BY peak_risk_score DESC"
            ), {"eid": eid}).fetchall()
            return [dict(r._mapping) for r in rows]

    @classmethod
    def get_risk_summary(cls) -> dict:
        with cls.engine().connect() as c:
            row = c.execute(text("""
                SELECT
                    ROUND(SUM(total_revenue_at_risk_usd),2) AS total_revenue_at_risk_usd,
                    COUNT(DISTINCT supplier_id) AS affected_suppliers,
                    ROUND(AVG(peak_risk_score),4) AS avg_risk_score,
                    ROUND(MAX(peak_risk_score),4) AS max_risk_score,
                    SUM(CASE WHEN risk_level='critical' THEN 1 ELSE 0 END) AS critical_count,
                    SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) AS high_count
                FROM risk_predictions
                WHERE created_at >= datetime('now','-30 days')
            """)).fetchone()
            return dict(row._mapping) if row else {}

    @classmethod
    def get_tier_risk_breakdown(cls) -> List[dict]:
        with cls.engine().connect() as c:
            rows = c.execute(text("""
                SELECT s.tier,
                    COUNT(DISTINCT p.supplier_id) AS supplier_count,
                    ROUND(AVG(p.peak_risk_score),4) AS avg_risk,
                    ROUND(SUM(p.total_revenue_at_risk_usd),2) AS total_revenue_at_risk_usd
                FROM risk_predictions p
                JOIN suppliers s ON p.supplier_id = s.id
                WHERE p.created_at >= datetime('now','-7 days')
                GROUP BY s.tier ORDER BY avg_risk DESC
            """)).fetchall()
            return [dict(r._mapping) for r in rows]

    @classmethod
    def stats(cls) -> dict:
        with cls.engine().connect() as c:
            return {
                "users":       c.execute(text("SELECT COUNT(*) FROM users")).scalar(),
                "suppliers":   c.execute(text("SELECT COUNT(*) FROM suppliers")).scalar(),
                "edges":       c.execute(text("SELECT COUNT(*) FROM supply_edges")).scalar(),
                "events":      c.execute(text("SELECT COUNT(*) FROM disruption_events")).scalar(),
                "predictions": c.execute(text("SELECT COUNT(*) FROM risk_predictions")).scalar(),
            }

    @classmethod
    def reset_all_predictions_and_events(cls) -> dict:
        """Delete all predictions + active events, reset supplier risk to low."""
        with cls.engine().connect() as conn:
            conn.execute(text("DELETE FROM risk_predictions"))
            conn.execute(text("DELETE FROM disruption_events"))
            conn.execute(text("UPDATE suppliers SET risk_score=0.05, risk_level='low'"))
            conn.commit()
        return {"deleted": True}