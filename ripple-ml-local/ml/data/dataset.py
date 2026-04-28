"""
SupplyChainDataset — train/val/test node masks + simple DataLoader.
Uses full-graph batching instead of NeighborLoader — no pyg-lib or
torch-sparse needed. Works perfectly for graphs under ~10k nodes.
"""
from __future__ import annotations
import logging
import numpy as np
import torch
from torch_geometric.data import Data
from torch.utils.data import DataLoader
from ml.config import get_config

logger = logging.getLogger(__name__)


class _NodeSubset:
    """Wraps node indices so standard DataLoader can iterate them."""
    def __init__(self, data: Data, mask: torch.Tensor):
        self.data    = data
        self.indices = mask.nonzero(as_tuple=True)[0].tolist()

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        return self.indices[idx]


def _make_loader(data: Data, mask: torch.Tensor, batch_size: int, shuffle: bool):
    return DataLoader(
        _NodeSubset(data, mask),
        batch_size=batch_size,
        shuffle=shuffle,
    )


class SupplyChainDataset:
    def __init__(self, graph_data: Data):
        self.cfg  = get_config()
        self.data = graph_data
        self._split_nodes()

    def _split_nodes(self):
        cfg   = self.cfg.gnn
        n     = self.data.num_nodes
        tiers = getattr(self.data, "supplier_tiers", ["tier_2"] * n)

        tier_indices: dict = {}
        for i, t in enumerate(tiers):
            tier_indices.setdefault(t, []).append(i)

        train_idx, val_idx, test_idx = [], [], []
        for _, indices in tier_indices.items():
            perm    = np.random.permutation(indices)
            nt      = len(perm)
            n_train = max(1, int(nt * cfg.train_ratio))
            n_val   = max(1, int(nt * cfg.val_ratio))
            train_idx.extend(perm[:n_train].tolist())
            val_idx.extend(perm[n_train:n_train + n_val].tolist())
            test_idx.extend(perm[n_train + n_val:].tolist())

        def _mask(idxs):
            m = torch.zeros(n, dtype=torch.bool)
            if idxs:
                m[idxs] = True
            return m

        self.data.train_mask = _mask(train_idx)
        self.data.val_mask   = _mask(val_idx)
        self.data.test_mask  = _mask(test_idx)
        logger.info(
            f"Split: train={self.data.train_mask.sum()} "
            f"val={self.data.val_mask.sum()} "
            f"test={self.data.test_mask.sum()}"
        )

    def get_train_loader(self):
        return _make_loader(
            self.data, self.data.train_mask,
            batch_size=self.cfg.gnn.batch_size, shuffle=True,
        )

    def get_val_loader(self):
        return _make_loader(
            self.data, self.data.val_mask,
            batch_size=self.cfg.gnn.batch_size * 2, shuffle=False,
        )

    def get_test_loader(self):
        return _make_loader(
            self.data, self.data.test_mask,
            batch_size=self.cfg.gnn.batch_size * 2, shuffle=False,
        )

    def stats(self) -> dict:
        d = self.data
        return {
            "num_nodes":        d.num_nodes,
            "num_edges":        d.num_edges,
            "node_feature_dim": d.x.shape[1],
            "edge_feature_dim": d.edge_attr.shape[1] if d.edge_attr is not None else 0,
            "label_horizon":    d.y.shape[1] if d.y is not None else 0,
            "train_nodes":      int(d.train_mask.sum()),
            "val_nodes":        int(d.val_mask.sum()),
            "test_nodes":       int(d.test_mask.sum()),
        }