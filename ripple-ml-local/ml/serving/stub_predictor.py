"""Rule-based stub predictor — deployed immediately, replaced by GNN after training."""
import numpy as np
from typing import Dict, List
from pydantic import BaseModel


class NodePrediction(BaseModel):
    risk_scores: List[float]
    peak_risk_score: float
    peak_risk_day: int
    risk_level: str
    confidence: float


class StubPredictor:
    TIER_DECAY = {"tier_3":1.00,"tier_2":0.65,"tier_1":0.40,"oem":0.20}

    def predict(self, req) -> Dict:
        edge_map: Dict[str, list] = {}
        for e in req.graph_edges:
            edge_map.setdefault(e.source, []).append((e.target, e.dependency_weight, e.is_sole_source))

        trigger = max(req.graph_nodes, key=lambda n: n.risk_score, default=req.graph_nodes[0])
        sev = max(trigger.risk_score, 0.5)

        risks: Dict[str, float] = {}
        visited = set()
        queue = [(trigger.id, sev)]
        while queue:
            cur, cur_risk = queue.pop(0)
            if cur in visited: continue
            visited.add(cur); risks[cur] = cur_risk
            node = next((n for n in req.graph_nodes if n.id == cur), None)
            if node is None: continue
            for tgt, wt, sole in edge_map.get(cur, []):
                tier = next((n.tier for n in req.graph_nodes if n.id == tgt), "tier_2")
                prop = min(1.0, cur_risk * self.TIER_DECAY.get(tier, 0.5) * wt * (1.4 if sole else 1.0))
                if tgt not in visited: queue.append((tgt, prop))

        result = {}
        for node in req.graph_nodes:
            base  = risks.get(node.id, 0.0)
            noise = getattr(node, "risk_score", 0.0) * 0.1
            scores = []
            for d in range(req.horizon_days):
                r = min(1.0, max(0.0, base * np.exp(-0.06 * abs(d-7)) + noise + np.random.uniform(-0.01, 0.01)))
                scores.append(round(r, 4))
            peak = max(scores)
            result[node.id] = NodePrediction(
                risk_scores=scores, peak_risk_score=round(peak, 4),
                peak_risk_day=int(scores.index(peak)),
                risk_level=_level(peak), confidence=0.60,
            )
        return result


def _level(s: float) -> str:
    if s >= 0.70: return "critical"
    if s >= 0.40: return "high"
    if s >= 0.20: return "medium"
    return "low"