"""
Full ML test suite — no internet, no GCP, runs 100% locally.
Usage: pytest ml/tests/test_ml.py -v
"""
import pytest, torch, numpy as np, tempfile, os
from torch_geometric.data import Data
from ml.config import MLConfig, GNNConfig, reset_config
from ml.model.gnn_model import RippleGNN, build_model, _level
from ml.evaluation.metrics import RiskMetrics
from ml.serving.stub_predictor import StubPredictor
from ml.data.graph_builder import NodeFeatureEncoder, EdgeFeatureEncoder


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_cfg():
    reset_config()
    yield
    reset_config()

@pytest.fixture
def small_cfg():
    cfg = GNNConfig()
    cfg.hidden_dim = 32; cfg.num_layers = 2
    cfg.num_epochs = 2;  cfg.batch_size = 4
    return cfg

@pytest.fixture
def tiny_graph():
    n, e = 12, 18
    x = torch.randn(n, 16)
    ei = torch.randint(0, n, (2, e))
    ea = torch.randn(e, 6)
    y  = torch.rand(n, 45)
    d = Data(x=x, edge_index=ei, edge_attr=ea, y=y, num_nodes=n)
    d.supplier_ids   = [f"s{i:03d}" for i in range(n)]
    d.supplier_names = [f"Supplier {i}" for i in range(n)]
    d.supplier_tiers = ["tier_3"]*4 + ["tier_2"]*4 + ["tier_1"]*3 + ["oem"]*1
    return d


# ── Model architecture ─────────────────────────────────────────────────────────

def test_graphsage_builds(small_cfg):
    small_cfg.model_type = "graphsage"
    m = RippleGNN(small_cfg)
    assert m.param_count() > 0

def test_gat_builds(small_cfg):
    small_cfg.model_type = "gat"
    small_cfg.heads = 2
    m = RippleGNN(small_cfg)
    assert m.param_count() > 0

def test_forward_shape(small_cfg, tiny_graph):
    m = RippleGNN(small_cfg); m.eval()
    with torch.no_grad():
        out = m(tiny_graph.x, tiny_graph.edge_index, tiny_graph.edge_attr)
    assert out.shape == (12, 45)

def test_output_in_01(small_cfg, tiny_graph):
    m = RippleGNN(small_cfg); m.eval()
    with torch.no_grad():
        out = m(tiny_graph.x, tiny_graph.edge_index, tiny_graph.edge_attr)
    assert out.min() >= 0.0 and out.max() <= 1.0

def test_predict_risk_dict(small_cfg, tiny_graph):
    m = RippleGNN(small_cfg)
    result = m.predict_risk(tiny_graph, torch.device("cpu"))
    assert len(result) == 12
    for sid, pred in result.items():
        assert len(pred["risk_scores"]) == 45
        assert 0 <= pred["peak_risk_score"] <= 1
        assert pred["risk_level"] in ("low","medium","high","critical")

def test_level_function():
    assert _level(0.80) == "critical"
    assert _level(0.55) == "high"
    assert _level(0.30) == "medium"
    assert _level(0.10) == "low"


# ── Feature encoders ───────────────────────────────────────────────────────────

def test_node_encoder_length():
    enc = NodeFeatureEncoder()
    feat = enc.encode({"tier":"tier_3","category":"raw_silicon","region":"Asia Pacific",
                       "annual_revenue_usd":5e8,"employee_count":2000,
                       "latitude":25.0,"longitude":121.5,
                       "historical_delay_rate":0.08,"risk_score":0.3})
    assert len(feat) == 16

def test_node_encoder_bounded():
    enc = NodeFeatureEncoder()
    for tier in ["tier_3","tier_2","tier_1","oem"]:
        feat = enc.encode({"tier":tier,"category":"semiconductors","region":"Asia Pacific",
                           "annual_revenue_usd":1e9,"employee_count":5000,
                           "latitude":35.0,"longitude":135.0,
                           "historical_delay_rate":0.05,"risk_score":0.2})
        for i,v in enumerate(feat):
            assert 0.0 <= v <= 1.0, f"Feature {i} = {v} out of [0,1]"

def test_edge_encoder_length():
    enc = EdgeFeatureEncoder()
    feat = enc.encode({"lead_time_days":45,"dependency_weight":0.8,
                       "annual_volume_usd":5e7,"is_sole_source":True,
                       "component_category":"semiconductors"})
    assert len(feat) == 6


# ── Metrics ────────────────────────────────────────────────────────────────────

def test_perfect_prediction_zero_error():
    p = np.random.rand(10, 45)
    m = RiskMetrics.compute(p, p)
    assert m["mae"] < 1e-6

def test_metrics_keys_present():
    p = np.random.rand(10, 45); t = np.random.rand(10, 45)
    m = RiskMetrics.compute(p, t)
    for k in ["mae","rmse","auc_roc","f1","peak_day_mae","peak_day_within7"]:
        assert k in m, f"Missing key: {k}"

def test_metrics_with_tiers():
    p = np.random.rand(12, 45); t = np.random.rand(12, 45)
    tiers = ["tier_3"]*4+["tier_2"]*4+["tier_1"]*3+["oem"]*1
    m = RiskMetrics.compute(p, t, tiers)
    assert "mae_tier_3" in m and "mae_oem" in m

def test_cascade_direction():
    preds = np.zeros((12, 45))
    preds[0]  = 0.9   # tier_3 trigger
    preds[4]  = 0.5   # tier_2
    preds[8]  = 0.2   # tier_1
    preds[11] = 0.05  # oem
    tiers = ["tier_3"]*4+["tier_2"]*4+["tier_1"]*3+["oem"]*1
    res = RiskMetrics.cascade_accuracy(preds, 0, tiers)
    assert res["cascade_direction_correct"] is True


# ── SQLite database ────────────────────────────────────────────────────────────

def test_database_creates_and_seeds():
    import tempfile, os
    td = tempfile.mkdtemp()
    try:
        db_path = os.path.join(td, "test.db")
        from ml.data.database import Database
        db = Database(db_path)
        db._create_tables()
        s = db.stats()
        assert "suppliers" in s
    finally:
        # Must dispose engine so SQLAlchemy releases the file lock on Windows
        if db.engine is not None:
            db.engine.dispose()
        import shutil
        shutil.rmtree(td, ignore_errors=True)


def test_database_seed_from_mock():
    import tempfile, os, json, uuid
    from datetime import datetime
    td = tempfile.mkdtemp()
    db = None
    try:
        mock = {
            "suppliers": [{"id":str(uuid.uuid4()),"name":"Test Corp","tier":"tier_3",
                           "country":"Taiwan","region":"Asia Pacific","category":"raw_silicon",
                           "annual_revenue_usd":1e9,"employee_count":1000,
                           "latitude":25.0,"longitude":121.5,"historical_delay_rate":0.05,
                           "risk_score":0.0,"risk_level":"low","created_at":datetime.utcnow().isoformat()}],
            "edges": [], "events": [],
        }
        mock_path = os.path.join(td, "mock.json")
        with open(mock_path,"w") as f: json.dump(mock, f)
        from ml.data.database import Database
        db = Database(os.path.join(td, "test.db"))
        db._create_tables()
        db.seed_from_json(mock_path)
        sups = db.get_suppliers()
        assert len(sups) == 1
        assert sups.iloc[0]["name"] == "Test Corp"
    finally:
        if db is not None and db.engine is not None:
            db.engine.dispose()
        import shutil
        shutil.rmtree(td, ignore_errors=True)


# ── Stub predictor ─────────────────────────────────────────────────────────────

class _N:
    def __init__(self, id_, tier, rs=0.0): self.id=id_; self.tier=tier; self.risk_score=rs; self.features=[0.0]*16

class _E:
    def __init__(self, s, t, w=0.7, sole=False): self.source=s; self.target=t; self.dependency_weight=w; self.is_sole_source=sole; self.features=[0.0]*6

class _R:
    graph_nodes=[_N("n0","tier_3",0.9),_N("n1","tier_2"),_N("n2","tier_1"),_N("n3","oem")]
    graph_edges=[_E("n0","n1",0.8,True),_E("n1","n2",0.6),_E("n2","n3",0.5)]
    trigger_event_id="t1"; horizon_days=45

def test_stub_all_nodes():
    result = StubPredictor().predict(_R())
    assert set(result.keys()) == {"n0","n1","n2","n3"}

def test_stub_propagates():
    result = StubPredictor().predict(_R())
    assert result["n0"].peak_risk_score >= result["n3"].peak_risk_score

def test_stub_shape():
    result = StubPredictor().predict(_R())
    for pred in result.values():
        assert len(pred.risk_scores) == 45
        assert 0 <= pred.peak_risk_score <= 1

def test_stub_sole_source_amplifies():
    class SoleR:
        graph_nodes=[_N("A","tier_3",0.7),_N("B","tier_2")]
        graph_edges=[_E("A","B",0.7,True)]; trigger_event_id="x"; horizon_days=45
    class NormR:
        graph_nodes=[_N("A","tier_3",0.7),_N("B","tier_2")]
        graph_edges=[_E("A","B",0.7,False)]; trigger_event_id="x"; horizon_days=45
    sole = StubPredictor().predict(SoleR()); norm = StubPredictor().predict(NormR())
    assert sole["B"].peak_risk_score >= norm["B"].peak_risk_score


# ── Config ─────────────────────────────────────────────────────────────────────

def test_default_config_values():
    cfg = MLConfig()
    assert cfg.gnn.node_feature_dim == 16
    assert cfg.gnn.output_dim == 45
    assert cfg.gnn.num_layers == 3
    assert cfg.serving.port == 8081

def test_config_from_yaml(tmp_path):
    yml = tmp_path / "test.yaml"
    yml.write_text("gnn:\n  hidden_dim: 64\n  num_epochs: 50\n")
    reset_config()
    cfg = MLConfig.from_yaml(str(yml))
    assert cfg.gnn.hidden_dim == 64
    assert cfg.gnn.num_epochs == 50