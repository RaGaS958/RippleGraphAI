"""
Local SQLite database — replaces BigQuery entirely.
Uses SQLAlchemy Core (no ORM) for speed with pandas integration.

Tables:
  suppliers        — all supplier nodes
  supply_edges     — dependency relationships
  disruption_events — disruption alerts
  risk_predictions — GNN prediction outputs

Usage:
  from ml.data.database import Database
  db = Database()
  db.init()              # creates tables + seeds from JSON if empty
  suppliers = db.get_suppliers()
"""
from __future__ import annotations
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd
from sqlalchemy import (
    create_engine, text, MetaData, Table, Column,
    String, Float, Integer, Boolean, DateTime, JSON,
)
from sqlalchemy.engine import Engine
from datetime import datetime

from ml.config import get_config

logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around SQLite. Zero cloud dependencies."""

    def __init__(self, db_path: Optional[str] = None):
        cfg = get_config()
        path = db_path or cfg.db.db_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(
            f"sqlite:///{path}",
            echo=cfg.db.echo_sql,
            connect_args={"check_same_thread": False},
        )
        self._path = path

    # ── Schema ─────────────────────────────────────────────────────────────────

    def init(self, seed_path: Optional[str] = None) -> None:
        """Create tables and optionally seed from JSON mock data."""
        self._create_tables()
        if seed_path or self._is_empty():
            fallback = "data/mock/supply_chain_mock.json"
            self.seed_from_json(seed_path or fallback)

    def _create_tables(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id TEXT PRIMARY KEY,
                name TEXT,
                tier TEXT,
                country TEXT,
                region TEXT,
                category TEXT,
                annual_revenue_usd REAL,
                employee_count INTEGER,
                latitude REAL,
                longitude REAL,
                historical_delay_rate REAL DEFAULT 0.0,
                risk_score REAL DEFAULT 0.0,
                risk_level TEXT DEFAULT 'low',
                created_at TEXT
            )"""))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS supply_edges (
                id TEXT PRIMARY KEY,
                source_supplier_id TEXT,
                target_supplier_id TEXT,
                component_category TEXT,
                lead_time_days INTEGER,
                dependency_weight REAL,
                annual_volume_usd REAL,
                is_sole_source INTEGER DEFAULT 0
            )"""))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS disruption_events (
                id TEXT PRIMARY KEY,
                supplier_id TEXT,
                disruption_type TEXT,
                severity REAL,
                description TEXT,
                affected_capacity_pct REAL,
                source TEXT DEFAULT 'manual',
                country TEXT DEFAULT '',
                category TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                estimated_revenue_at_risk_usd REAL DEFAULT 0.0,
                created_at TEXT,
                resolved_at TEXT
            )"""))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_predictions (
                id TEXT PRIMARY KEY,
                trigger_event_id TEXT,
                supplier_id TEXT,
                peak_risk_score REAL,
                peak_risk_day INTEGER,
                risk_level TEXT,
                confidence REAL,
                total_revenue_at_risk_usd REAL,
                affected_supplier_count INTEGER,
                model_version TEXT,
                recommendations TEXT,
                created_at TEXT
            )"""))

            # Indexes for common queries
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sup_tier ON suppliers(tier)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_edge_src ON supply_edges(source_supplier_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_evt_status ON disruption_events(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pred_supplier ON risk_predictions(supplier_id)"))
            conn.commit()
        logger.info(f"SQLite schema ready at {self._path}")

    def _is_empty(self) -> bool:
        with self.engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM suppliers")).scalar()
            return (count or 0) == 0

    # ── Seeding ────────────────────────────────────────────────────────────────

    def seed_from_json(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            logger.warning(f"Seed file not found: {path} — generating mock data")
            self._generate_and_seed()
            return

        with open(p) as f:
            data = json.load(f)

        with self.engine.begin() as conn:
            for s in data.get("suppliers", []):
                s.setdefault("created_at", datetime.utcnow().isoformat())
                conn.execute(text("""
                    INSERT OR REPLACE INTO suppliers
                    (id,name,tier,country,region,category,annual_revenue_usd,
                     employee_count,latitude,longitude,historical_delay_rate,
                     risk_score,risk_level,created_at)
                    VALUES (:id,:name,:tier,:country,:region,:category,
                            :annual_revenue_usd,:employee_count,:latitude,
                            :longitude,:historical_delay_rate,:risk_score,
                            :risk_level,:created_at)
                """), s)

            for e in data.get("edges", []):
                conn.execute(text("""
                    INSERT OR REPLACE INTO supply_edges
                    (id,source_supplier_id,target_supplier_id,component_category,
                     lead_time_days,dependency_weight,annual_volume_usd,is_sole_source)
                    VALUES (:id,:source_supplier_id,:target_supplier_id,
                            :component_category,:lead_time_days,:dependency_weight,
                            :annual_volume_usd,:is_sole_source)
                """), e)

            for ev in data.get("events", []):
                ev.setdefault("created_at", datetime.utcnow().isoformat())
                ev.setdefault("resolved_at", None)
                conn.execute(text("""
                    INSERT OR REPLACE INTO disruption_events
                    (id,supplier_id,disruption_type,severity,description,
                     affected_capacity_pct,source,country,category,status,
                     estimated_revenue_at_risk_usd,created_at,resolved_at)
                    VALUES (:id,:supplier_id,:disruption_type,:severity,:description,
                            :affected_capacity_pct,:source,:country,:category,:status,
                            :estimated_revenue_at_risk_usd,:created_at,:resolved_at)
                """), ev)

        logger.info(
            f"Seeded: {len(data.get('suppliers',[]))} suppliers, "
            f"{len(data.get('edges',[]))} edges, "
            f"{len(data.get('events',[]))} events"
        )

    def _generate_and_seed(self) -> None:
        """Auto-generate mock data if no JSON file exists."""
        import sys
        sys.path.insert(0, ".")
        try:
            from data.mock.generate_mock_data import generate_all
            data = generate_all()
            mock_path = Path("data/mock/supply_chain_mock.json")
            mock_path.parent.mkdir(parents=True, exist_ok=True)
            with open(mock_path, "w") as f:
                json.dump(data, f, default=str)
            self.seed_from_json(str(mock_path))
        except Exception as e:
            logger.error(f"Auto-seed failed: {e}")

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_suppliers(self, tier: Optional[str] = None) -> pd.DataFrame:
        q = "SELECT * FROM suppliers"
        if tier:
            q += f" WHERE tier = '{tier}'"
        return pd.read_sql(q, self.engine)

    def get_edges(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM supply_edges", self.engine)

    def get_active_events(self) -> pd.DataFrame:
        return pd.read_sql(
            "SELECT * FROM disruption_events WHERE status='active' ORDER BY created_at DESC",
            self.engine,
        )

    def get_latest_event_per_supplier(self) -> pd.DataFrame:
        q = """
        SELECT * FROM disruption_events
        WHERE id IN (
            SELECT id FROM disruption_events
            WHERE status = 'active'
            GROUP BY supplier_id
            HAVING MAX(created_at)
        )
        """
        return pd.read_sql(q, self.engine)

    def save_prediction(self, pred: dict) -> None:
        pred.setdefault("created_at", datetime.utcnow().isoformat())
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO risk_predictions
                (id,trigger_event_id,supplier_id,peak_risk_score,peak_risk_day,
                 risk_level,confidence,total_revenue_at_risk_usd,
                 affected_supplier_count,model_version,recommendations,created_at)
                VALUES (:id,:trigger_event_id,:supplier_id,:peak_risk_score,
                        :peak_risk_day,:risk_level,:confidence,
                        :total_revenue_at_risk_usd,:affected_supplier_count,
                        :model_version,:recommendations,:created_at)
            """), pred)

    def update_supplier_risk(self, supplier_id: str, risk_score: float, risk_level: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(
                "UPDATE suppliers SET risk_score=:s, risk_level=:l WHERE id=:id"
            ), {"s": risk_score, "l": risk_level, "id": supplier_id})

    def get_risk_summary(self) -> dict:
        q = """
        SELECT
            ROUND(SUM(total_revenue_at_risk_usd),2) AS total_revenue_at_risk,
            COUNT(DISTINCT supplier_id) AS affected_suppliers,
            ROUND(AVG(peak_risk_score),4) AS avg_risk_score,
            ROUND(MAX(peak_risk_score),4) AS max_risk_score,
            SUM(CASE WHEN risk_level='critical' THEN 1 ELSE 0 END) AS critical_count,
            SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) AS high_count
        FROM risk_predictions
        WHERE created_at >= datetime('now', '-30 days')
        """
        with self.engine.connect() as conn:
            row = conn.execute(text(q)).fetchone()
            return dict(row._mapping) if row else {}

    def get_tier_risk_breakdown(self) -> List[dict]:
        q = """
        SELECT
            s.tier,
            COUNT(DISTINCT p.supplier_id) AS supplier_count,
            ROUND(AVG(p.peak_risk_score),4) AS avg_risk,
            ROUND(SUM(p.total_revenue_at_risk_usd),2) AS total_revenue_at_risk
        FROM risk_predictions p
        JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.created_at >= datetime('now', '-7 days')
        GROUP BY s.tier
        ORDER BY avg_risk DESC
        """
        with self.engine.connect() as conn:
            rows = conn.execute(text(q)).fetchall()
            return [dict(r._mapping) for r in rows]

    def stats(self) -> dict:
        with self.engine.connect() as conn:
            return {
                "suppliers":    conn.execute(text("SELECT COUNT(*) FROM suppliers")).scalar(),
                "edges":        conn.execute(text("SELECT COUNT(*) FROM supply_edges")).scalar(),
                "events":       conn.execute(text("SELECT COUNT(*) FROM disruption_events")).scalar(),
                "predictions":  conn.execute(text("SELECT COUNT(*) FROM risk_predictions")).scalar(),
            }
