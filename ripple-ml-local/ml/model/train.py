"""
Local training pipeline — no pyg-lib or torch-sparse required.
Works with the simple full-graph DataLoader from dataset.py.

Usage:
    python -m ml.model.train
    python -m ml.model.train --epochs 5
"""
from __future__ import annotations
import argparse, logging, random, time, sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from ml.config import get_config, reset_config, MLConfig
from ml.data.database import Database
from ml.data.graph_builder import GraphBuilder
from ml.data.dataset import SupplyChainDataset
from ml.model.gnn_model import RippleGNN, build_model
from ml.evaluation.metrics import RiskMetrics

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

class EarlyStopping:
    def __init__(self, patience=15, min_delta=1e-4):
        self.patience  = patience
        self.min_delta = min_delta
        self.counter   = 0
        self.best      = float("inf")
        self.stop      = False

    def step(self, val_loss: float) -> bool:
        if val_loss < self.best - self.min_delta:
            self.best    = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.stop = True
        return self.stop


def _device(spec: str) -> torch.device:
    if spec == "auto":
        if torch.cuda.is_available():               return torch.device("cuda")
        if torch.backends.mps.is_available():       return torch.device("mps")
        return torch.device("cpu")
    return torch.device(spec)


def _loss_fn(cfg: MLConfig) -> nn.Module:
    name = cfg.gnn.loss_fn
    if name == "huber": return nn.HuberLoss(delta=cfg.gnn.huber_delta)
    if name == "mse":   return nn.MSELoss()
    return nn.L1Loss()


def _set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ── Train / eval epoch ────────────────────────────────────────────────────────
# The DataLoader yields batches of node *indices* (plain LongTensor).
# We run the GNN on the FULL graph each forward pass, then compute loss
# only on the batch indices. This is efficient for small graphs (≤10k nodes).

def train_epoch(
    model: RippleGNN,
    loader,
    data,           # full PyG Data object
    opt: torch.optim.Optimizer,
    loss_fn: nn.Module,
    device: torch.device,
) -> float:
    model.train()
    x   = data.x.to(device)
    ei  = data.edge_index.to(device)
    ea  = data.edge_attr.to(device) if data.edge_attr is not None else None
    y   = data.y.to(device)

    total, n_batches = 0.0, 0
    for idx_batch in loader:
        idx = idx_batch.to(device)          # node indices for this mini-batch
        opt.zero_grad()
        pred = model(x, ei, ea)             # [N, 45] — full graph forward
        loss = loss_fn(pred[idx], y[idx])   # loss only on batch nodes
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        total    += loss.item()
        n_batches += 1

    return total / max(n_batches, 1)


@torch.no_grad()
def eval_epoch(
    model: RippleGNN,
    loader,
    data,
    loss_fn: nn.Module,
    device: torch.device,
) -> Tuple[float, Dict]:
    model.eval()
    x  = data.x.to(device)
    ei = data.edge_index.to(device)
    ea = data.edge_attr.to(device) if data.edge_attr is not None else None
    y  = data.y.to(device)

    pred = model(x, ei, ea)    # single full-graph forward for eval

    # Collect all val/test indices from loader
    all_idx = torch.cat([b.to(device) for b in loader])
    loss    = loss_fn(pred[all_idx], y[all_idx]).item()

    p_np = pred[all_idx].cpu().numpy()
    t_np = y[all_idx].cpu().numpy()
    metrics = RiskMetrics.compute(p_np, t_np)
    return loss, metrics


# ── Main ──────────────────────────────────────────────────────────────────────

def train(cfg: MLConfig) -> RippleGNN:
    _set_seed(cfg.training.seed)
    device = _device(cfg.training.device)
    logger.info(f"Device: {device}")

    # Data
    db      = Database(cfg.db.db_path)
    db.init()
    logger.info(f"DB stats: {db.stats()}")

    builder  = GraphBuilder(db)
    graph    = builder.build(include_labels=True, save_path="artifacts/graph_data.pt")
    dataset  = SupplyChainDataset(graph)
    logger.info(f"Dataset: {dataset.stats()}")

    train_loader = dataset.get_train_loader()
    val_loader   = dataset.get_val_loader()

    # Model
    model   = build_model(cfg.gnn).to(device)
    loss_fn = _loss_fn(cfg)
    opt     = AdamW(model.parameters(),
                    lr=cfg.gnn.learning_rate, weight_decay=cfg.gnn.weight_decay)
    sched   = CosineAnnealingLR(
        opt,
        T_max=max(cfg.gnn.num_epochs - cfg.gnn.warmup_epochs, 1),
        eta_min=1e-6,
    )
    es      = EarlyStopping(patience=cfg.gnn.early_stopping_patience)

    ckpt_dir  = Path(cfg.training.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    best_ckpt = ckpt_dir / "best_model.pt"
    best_val  = float("inf")
    history   = {"train_loss": [], "val_loss": [], "val_mae": [], "val_auc": []}

    logger.info(f"Training for up to {cfg.gnn.num_epochs} epochs…")

    for epoch in range(1, cfg.gnn.num_epochs + 1):
        t0 = time.time()

        # LR warmup
        if epoch <= cfg.gnn.warmup_epochs:
            for pg in opt.param_groups:
                pg["lr"] = cfg.gnn.learning_rate * epoch / cfg.gnn.warmup_epochs

        tr_loss         = train_epoch(model, train_loader, graph, opt, loss_fn, device)
        val_loss, vmets = eval_epoch(model, val_loader, graph, loss_fn, device)

        if epoch > cfg.gnn.warmup_epochs:
            sched.step()

        history["train_loss"].append(tr_loss)
        history["val_loss"].append(val_loss)
        history["val_mae"].append(vmets.get("mae", 0))
        history["val_auc"].append(vmets.get("auc_roc", 0))

        if val_loss < best_val:
            best_val = val_loss
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_loss": val_loss,
                "gnn_config": cfg.gnn,
            }, str(best_ckpt))

        if epoch % cfg.training.log_every_n_steps == 0 or epoch == 1:
            lr = opt.param_groups[0]["lr"]
            logger.info(
                f"Ep {epoch:4d}/{cfg.gnn.num_epochs} | "
                f"train={tr_loss:.4f} val={val_loss:.4f} "
                f"mae={vmets.get('mae', 0):.4f} "
                f"auc={vmets.get('auc_roc', 0):.4f} "
                f"lr={lr:.2e} | {time.time()-t0:.1f}s"
            )

        if epoch % cfg.training.save_every_n_epochs == 0:
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "gnn_config": cfg.gnn,
            }, str(ckpt_dir / f"model_ep{epoch:04d}.pt"))

        if es.step(val_loss):
            logger.info(f"Early stopping at epoch {epoch}")
            break

    # Load best weights
    ckpt = torch.load(str(best_ckpt), map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])

    # Save final artifact
    art = Path("artifacts/model.pt")
    art.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state_dict": model.state_dict(),
        "gnn_config":       cfg.gnn,
        "train_history":    history,
        "best_val_loss":    best_val,
        "model_version":    "gnn-v1",
    }, str(art))

    logger.info(f"Done. best_val_loss={best_val:.4f} → artifacts/model.pt")
    return model


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, stream=sys.stdout,
        format="%(asctime)s %(levelname)s — %(message)s",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/ml_config.yaml")
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()

    reset_config()
    cfg = get_config(args.config)
    if args.epochs:
        cfg.gnn.num_epochs = args.epochs

    train(cfg)