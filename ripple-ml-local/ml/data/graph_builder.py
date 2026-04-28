"""
Graph builder — reads from local SQLite and builds a PyG Data object.
No cloud dependencies. Works entirely offline.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch
from torch_geometric.data import Data

from ml.config import get_config
from ml.data.database import Database

logger = logging.getLogger(__name__)

TIER_MAP     = {"tier_3": 0, "tier_2": 1, "tier_1": 2, "oem": 3}
CATEGORY_MAP = {
    "raw_silicon":0,"rare_earth_metals":1,"specialty_chemicals":2,
    "advanced_glass":3,"photoresists":4,"wafers":5,"pcb_substrate":6,
    "passive_components":7,"display_panels":8,"battery_cells":9,
    "semiconductors":10,"memory_chips":11,"power_management_ics":12,
    "displays":13,"battery_packs":14,"consumer_electronics":15,
    "automotive":16,"industrial_equipment":17,"aerospace":18,"medical_devices":19,
}
REGION_MAP = {"Asia Pacific":0,"Europe":1,"North America":2,"South Asia":3,"Other":4}


class NodeFeatureEncoder:
    """Encodes a supplier row → 16-dim float vector (all values in [0,1])."""

    def encode(self, s: dict, in_deg=0, out_deg=0, max_deg=10,
               sole_src_target=False, recent_disruption=None) -> List[float]:
        tier_n    = TIER_MAP.get(s.get("tier","tier_3"),0) / 3.0
        cat_n     = CATEGORY_MAP.get(s.get("category","semiconductors"),0) / max(len(CATEGORY_MAP)-1,1)
        reg_n     = REGION_MAP.get(s.get("region","Other"),4) / 4.0
        rev_n     = np.log1p(max(float(s.get("annual_revenue_usd",1e8)),1)) / np.log1p(5e9)
        emp_n     = np.log1p(max(float(s.get("employee_count",1000)),1)) / np.log1p(100_000)
        lat_n     = (float(s.get("latitude",0)) + 90) / 180.0
        lon_n     = (float(s.get("longitude",0)) + 180) / 360.0
        delay     = float(s.get("historical_delay_rate",0.05))
        risk      = float(s.get("risk_score",0.0))
        sole      = float(sole_src_target)
        in_n      = min(in_deg / max(max_deg,1), 1.0)
        out_n     = min(out_deg / max(max_deg,1), 1.0)
        dt = recent_disruption or ""
        d_factory = float("factory_shutdown" in dt)
        d_natural = float("natural_disaster" in dt)
        d_geo     = float("geopolitical" in dt)
        d_other   = float(bool(dt) and dt not in ("factory_shutdown","natural_disaster","geopolitical"))
        return [tier_n,cat_n,reg_n,rev_n,emp_n,lat_n,lon_n,
                delay,risk,sole,in_n,out_n,d_factory,d_natural,d_geo,d_other]


class EdgeFeatureEncoder:
    """Encodes a supply edge → 6-dim float vector (all values in [0,1])."""

    def encode(self, e: dict, src_tier="tier_3", tgt_tier="tier_2") -> List[float]:
        lead  = min(int(e.get("lead_time_days",30)), 120) / 120.0
        wt    = float(e.get("dependency_weight",0.5))
        vol   = np.log1p(max(float(e.get("annual_volume_usd",1e6)),1)) / np.log1p(5e8)
        sole  = float(bool(e.get("is_sole_source",False)))
        delta = (TIER_MAP.get(tgt_tier,1) - TIER_MAP.get(src_tier,0) + 3) / 6.0
        cat   = CATEGORY_MAP.get(e.get("component_category","semiconductors"),0) / max(len(CATEGORY_MAP)-1,1)
        return [lead, wt, vol, sole, delta, cat]


class GraphBuilder:
    """
    Reads from SQLite → builds PyG Data object.
    Data object fields:
      x           [N, 16]  node features
      edge_index  [2, E]   directed adjacency
      edge_attr   [E, 6]   edge features
      y           [N, 45]  risk labels
      supplier_ids, supplier_names, supplier_tiers
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.node_enc = NodeFeatureEncoder()
        self.edge_enc = EdgeFeatureEncoder()

    def build(self, include_labels=True, save_path: Optional[str] = None) -> Data:
        suppliers  = self.db.get_suppliers()
        edges_df   = self.db.get_edges()
        events_df  = self.db.get_latest_event_per_supplier()

        if suppliers.empty:
            raise RuntimeError("No suppliers found. Run db.init() or seed the database first.")

        id_to_idx: Dict[str,int] = {sid:i for i,sid in enumerate(suppliers["id"])}
        n = len(suppliers)

        in_deg  = edges_df["target_supplier_id"].value_counts().to_dict()
        out_deg = edges_df["source_supplier_id"].value_counts().to_dict()
        max_deg = max(max(in_deg.values(), default=1), max(out_deg.values(), default=1))
        sole_targets = set(edges_df[edges_df["is_sole_source"]==1]["target_supplier_id"].tolist())
        event_map = {}
        if not events_df.empty:
            for _, row in events_df.iterrows():
                event_map[row["supplier_id"]] = row["disruption_type"]

        # ── Node features ──────────────────────────────────────────────────────
        x_list = []
        for _, sup in suppliers.iterrows():
            sid = sup["id"]
            x_list.append(self.node_enc.encode(
                sup.to_dict(),
                in_deg=in_deg.get(sid,0), out_deg=out_deg.get(sid,0), max_deg=max_deg,
                sole_src_target=sid in sole_targets,
                recent_disruption=event_map.get(sid),
            ))
        x = torch.tensor(x_list, dtype=torch.float)

        # ── Edges ──────────────────────────────────────────────────────────────
        tier_lookup = suppliers.set_index("id")["tier"].to_dict()
        srcs, tgts, ea = [], [], []
        for _, e in edges_df.iterrows():
            s, t = e["source_supplier_id"], e["target_supplier_id"]
            if s not in id_to_idx or t not in id_to_idx:
                continue
            srcs.append(id_to_idx[s]); tgts.append(id_to_idx[t])
            ea.append(self.edge_enc.encode(e.to_dict(), tier_lookup.get(s,"tier_3"), tier_lookup.get(t,"tier_2")))

        edge_index = torch.tensor([srcs, tgts], dtype=torch.long) if srcs else torch.zeros((2,0),dtype=torch.long)
        edge_attr  = torch.tensor(ea, dtype=torch.float) if ea else torch.zeros((0,6),dtype=torch.float)

        # ── Labels ─────────────────────────────────────────────────────────────
        y = self._synthetic_labels(suppliers, events_df, id_to_idx, n)

        data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr, y=y, num_nodes=n)
        data.supplier_ids   = suppliers["id"].tolist()
        data.supplier_names = suppliers["name"].tolist()
        data.supplier_tiers = suppliers["tier"].tolist()

        logger.info(f"Graph: {n} nodes, {len(srcs)} edges | x={list(x.shape)} y={list(y.shape)}")

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            torch.save(data, save_path)
            logger.info(f"Graph saved → {save_path}")

        return data

    def _synthetic_labels(self, suppliers, events_df, id_to_idx, n):
        """Synthetic 45-day risk labels — peak at day 7, exponential decay."""
        y = torch.zeros(n, 45, dtype=torch.float)
        sev_map = {}
        if not events_df.empty:
            for _, row in events_df.iterrows():
                sev_map[row["supplier_id"]] = float(row.get("severity", 0.5))

        for _, sup in suppliers.iterrows():
            sid = sup["id"]
            if sid not in id_to_idx:
                continue
            idx = id_to_idx[sid]
            base = sev_map.get(sid, 0.0)
            noise_floor = float(sup.get("historical_delay_rate", 0.05))
            for d in range(45):
                if base > 0:
                    r = min(1.0, base * np.exp(-0.06 * abs(d-7))
                            + noise_floor * 0.3 + np.random.uniform(-0.01, 0.01))
                else:
                    r = noise_floor * np.random.uniform(0.1, 0.5)
                y[idx, d] = float(max(0.0, r))
        return y

    @staticmethod
    def load(path: str) -> Data:
        return torch.load(path, weights_only=False)