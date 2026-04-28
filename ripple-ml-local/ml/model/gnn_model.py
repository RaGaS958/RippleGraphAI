"""
RippleGNN — GraphSAGE / GAT model for 45-day supply chain risk forecasting.
Fully local. No cloud dependencies.
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from torch_geometric.nn import SAGEConv, GATv2Conv, BatchNorm
from torch_geometric.data import Data
from ml.config import get_config, GNNConfig


class NodeEncoder(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.LeakyReLU(0.1),
            nn.Linear(hidden_dim, hidden_dim), nn.LayerNorm(hidden_dim),
        )
    def forward(self, x: Tensor) -> Tensor:
        return self.net(x)


class GraphSAGEBackbone(nn.Module):
    def __init__(self, cfg: GNNConfig):
        super().__init__()
        h = cfg.hidden_dim
        self.convs  = nn.ModuleList([SAGEConv(h, h, aggr=cfg.aggregation, normalize=True) for _ in range(cfg.num_layers)])
        self.norms  = nn.ModuleList([BatchNorm(h) for _ in range(cfg.num_layers)])
        self.skip   = nn.Linear(h, h)
        self.drop   = nn.Dropout(cfg.dropout)

    def forward(self, x: Tensor, edge_index: Tensor, **_) -> Tensor:
        for conv, norm in zip(self.convs, self.norms):
            res = self.skip(x)
            x   = self.drop(F.leaky_relu(norm(conv(x, edge_index)), 0.1)) + res
        return x


class GATBackbone(nn.Module):
    def __init__(self, cfg: GNNConfig):
        super().__init__()
        h, heads = cfg.hidden_dim, cfg.heads
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for i in range(cfg.num_layers):
            is_last = (i == cfg.num_layers - 1)
            self.convs.append(GATv2Conv(h, h // heads if not is_last else h,
                                        heads=heads, concat=not is_last, dropout=cfg.dropout))
            self.norms.append(BatchNorm(h))
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x: Tensor, edge_index: Tensor, **_) -> Tensor:
        for conv, norm in zip(self.convs, self.norms):
            x = self.drop(F.elu(norm(conv(x, edge_index))))
        return x


class RiskHead(nn.Module):
    def __init__(self, hidden_dim: int, output_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim*2), nn.LayerNorm(hidden_dim*2), nn.GELU(), nn.Dropout(0.2),
            nn.Linear(hidden_dim*2, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, output_dim), nn.Sigmoid(),
        )
    def forward(self, x: Tensor) -> Tensor:
        return self.mlp(x)


class RippleGNN(nn.Module):
    """Input: x[N,16], edge_index[2,E], edge_attr[E,6]  →  Output: [N,45]"""

    def __init__(self, cfg: GNNConfig):
        super().__init__()
        self.node_enc = NodeEncoder(cfg.node_feature_dim, cfg.hidden_dim)
        self.backbone = GraphSAGEBackbone(cfg) if cfg.model_type == "graphsage" else GATBackbone(cfg)
        self.head     = RiskHead(cfg.hidden_dim, cfg.output_dim)
        self._init()

    def _init(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="leaky_relu")
                if m.bias is not None: nn.init.zeros_(m.bias)

    def forward(self, x, edge_index, edge_attr=None):
        return self.head(self.backbone(self.node_enc(x), edge_index))

    def predict_risk(self, data: Data, device: torch.device) -> dict:
        self.eval()
        with torch.no_grad():
            preds = self.forward(data.x.to(device), data.edge_index.to(device),
                                 data.edge_attr.to(device) if data.edge_attr is not None else None)
        ids = getattr(data, "supplier_ids", [str(i) for i in range(data.num_nodes)])
        result = {}
        for i, sid in enumerate(ids):
            scores = preds[i].cpu().tolist()
            peak   = max(scores)
            result[sid] = {
                "risk_scores": scores,
                "peak_risk_score": round(peak, 4),
                "peak_risk_day": int(scores.index(peak)),
                "current_risk": round(scores[0], 4),
                "risk_level": _level(peak),
            }
        return result

    def param_count(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def _level(s: float) -> str:
    if s >= 0.70: return "critical"
    if s >= 0.40: return "high"
    if s >= 0.20: return "medium"
    return "low"


def build_model(cfg: GNNConfig = None) -> RippleGNN:
    cfg = cfg or get_config().gnn
    m = RippleGNN(cfg)
    print(f"RippleGNN | {m.param_count():,} params | {cfg.model_type} × {cfg.num_layers} layers")
    return m
