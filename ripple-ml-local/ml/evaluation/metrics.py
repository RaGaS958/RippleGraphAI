"""Evaluation metrics — MAE, AUC-ROC, cascade accuracy. No cloud deps."""
import numpy as np
from typing import Dict, List, Optional
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support, mean_absolute_error, mean_squared_error


class RiskMetrics:
    HIGH_RISK_THRESHOLD = 0.50

    @classmethod
    def compute(cls, preds: np.ndarray, targets: np.ndarray, tiers: Optional[List] = None) -> Dict:
        r = {}
        r["mae"]  = float(mean_absolute_error(targets.flatten(), preds.flatten()))
        r["rmse"] = float(np.sqrt(mean_squared_error(targets.flatten(), preds.flatten())))

        per_day = np.mean(np.abs(preds - targets), axis=0)
        for d in [1, 7, 30, 45]:
            r[f"mae_day{d}"] = float(per_day[min(d-1, 44)])
        r["worst_day_mae"] = float(per_day.max())
        r["worst_day"]     = int(per_day.argmax())

        pred_bin = (preds.max(axis=1) >= cls.HIGH_RISK_THRESHOLD).astype(int)
        tgt_bin  = (targets.max(axis=1) >= cls.HIGH_RISK_THRESHOLD).astype(int)
        try:
            r["auc_roc"] = float(roc_auc_score(tgt_bin, preds.max(axis=1)))
        except ValueError:
            r["auc_roc"] = 0.0

        if tgt_bin.sum() > 0:
            p, rc, f1, _ = precision_recall_fscore_support(tgt_bin, pred_bin, average="binary", zero_division=0)
            r["precision"] = float(p); r["recall"] = float(rc); r["f1"] = float(f1)
        else:
            r["precision"] = r["recall"] = r["f1"] = 0.0

        peak_err = np.abs(preds.argmax(axis=1) - targets.argmax(axis=1)).astype(float)
        r["peak_day_mae"]      = float(peak_err.mean())
        r["peak_day_within3"]  = float((peak_err <= 3).mean())
        r["peak_day_within7"]  = float((peak_err <= 7).mean())

        if tiers:
            for tier in ["tier_3","tier_2","tier_1","oem"]:
                mask = np.array([t == tier for t in tiers])
                if mask.sum() > 0:
                    r[f"mae_{tier}"] = float(mean_absolute_error(targets[mask].flatten(), preds[mask].flatten()))
        return r

    @classmethod
    def cascade_accuracy(cls, preds, trigger_idx, supplier_tiers) -> Dict:
        tier_risks = {}
        for i, tier in enumerate(supplier_tiers):
            tier_risks.setdefault(tier, []).append(float(preds[i].max()))
        tier_avg = {t: np.mean(v) for t, v in tier_risks.items()}
        order = ["tier_3","tier_2","tier_1","oem"]
        vals  = [tier_avg.get(t, 0.0) for t in order if t in tier_avg]
        correct = all(vals[i] >= vals[i+1] for i in range(len(vals)-1))
        corr = float(np.corrcoef(range(len(vals)), vals)[0,1]) if len(vals) > 1 else 0.0
        return {"trigger_risk": float(preds[trigger_idx].max()),
                "tier_avg_risk": tier_avg, "cascade_direction_correct": correct, "cascade_score": corr}

    @classmethod
    def print_report(cls, m: Dict):
        print("\n" + "─"*52)
        print("  RippleGNN Evaluation")
        print("─"*52)
        for k, fmt in [("mae",".4f"),("rmse",".4f"),("auc_roc",".4f"),("f1",".4f"),
                       ("peak_day_mae",".1f"),("peak_day_within7",".1%")]:
            if k in m: print(f"  {k:<24} {m[k]:{fmt}}")
        print("─"*52)