"""
ML config — fully local, zero cloud dependencies.
Edit configs/ml_config.yaml to override any value.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import yaml


@dataclass
class DBConfig:
    # SQLite replaces BigQuery — just a file on disk
    db_path: str = "data/ripple_graph.db"
    echo_sql: bool = False


@dataclass
class GNNConfig:
    model_type: str = "graphsage"       # "graphsage" | "gat"
    hidden_dim: int = 128
    num_layers: int = 3
    dropout: float = 0.3
    heads: int = 4                       # GAT only
    aggregation: str = "mean"

    node_feature_dim: int = 16
    edge_feature_dim: int = 6
    output_dim: int = 45                 # 45-day forecast

    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 32
    num_epochs: int = 100
    early_stopping_patience: int = 15
    scheduler: str = "cosine"
    warmup_epochs: int = 5
    loss_fn: str = "huber"
    huber_delta: float = 0.5
    neighbor_sample_sizes: List[int] = field(default_factory=lambda: [15, 10, 5])
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15


@dataclass
class TrainingConfig:
    seed: int = 42
    device: str = "auto"                 # auto | cpu | cuda | mps
    num_workers: int = 0                 # 0 = main process (safer on Windows/Mac)
    log_every_n_steps: int = 10
    save_every_n_epochs: int = 20
    checkpoint_dir: str = "artifacts/checkpoints"
    experiment_name: str = "ripple-gnn"


@dataclass
class ServingConfig:
    host: str = "0.0.0.0"
    port: int = 8081                     # 8081 so it doesn't clash with backend
    model_artifact_path: str = "artifacts/model.pt"
    stub_mode: bool = True               # True until training completes


@dataclass
class LLMConfig:
    # Ollama (local) replaces Gemini
    provider: str = "ollama"             # "ollama" | "template"
    model: str = "llama3.2"             # any model pulled via: ollama pull llama3.2
    base_url: str = "http://localhost:11434"
    temperature: float = 0.2
    max_tokens: int = 1024


@dataclass
class MLConfig:
    db: DBConfig = field(default_factory=DBConfig)
    gnn: GNNConfig = field(default_factory=GNNConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    serving: ServingConfig = field(default_factory=ServingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "MLConfig":
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        cfg = cls()
        for section, sub in [
            ("db", cfg.db), ("gnn", cfg.gnn),
            ("training", cfg.training), ("serving", cfg.serving),
            ("llm", cfg.llm),
        ]:
            for k, v in (raw.get(section) or {}).items():
                if hasattr(sub, k):
                    setattr(sub, k, v)
        return cfg

    def to_yaml(self, path: str) -> None:
        import dataclasses
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(dataclasses.asdict(self), f, default_flow_style=False)


_cfg: Optional[MLConfig] = None

def get_config(path: str = "configs/ml_config.yaml") -> MLConfig:
    global _cfg
    if _cfg is None:
        p = Path(path)
        _cfg = MLConfig.from_yaml(str(p)) if p.exists() else MLConfig()
    return _cfg

def reset_config() -> None:
    global _cfg
    _cfg = None
