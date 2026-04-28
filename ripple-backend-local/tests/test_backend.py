"""
Backend test suite — zero cloud, runs entirely locally.
Uses FastAPI TestClient + in-memory SQLite.

Usage:  pytest tests/ -v
"""
import json, pytest, tempfile, os
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Each test gets its own fresh SQLite database."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    # Reset lru_cache so new settings are picked up
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.services.database import Database
    Database._engine = None
    Database.init()
    yield
    Database._engine = None


@pytest.fixture
def client():
    """FastAPI test client with mocked EventQueue worker."""
    with patch("app.services.event_queue.EventQueue.start_worker", new_callable=AsyncMock), \
         patch("app.services.event_queue.EventQueue.stop_worker",  new_callable=AsyncMock):
        from app.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture
def auth_header(client):
    """Register a test user and return Authorization header."""
    client.post("/api/v1/auth/register",
                json={"email": "test@ripple.ai", "password": "testpass123", "name": "Tester"})
    r = client.post("/api/v1/auth/login",
                    json={"email": "test@ripple.ai", "password": "testpass123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_db():
    """Seed a small graph into the test DB."""
    from app.services.database import Database
    import uuid
    sups = [
        {"id": f"t3-{i}", "name": f"Tier3-{i}", "tier": "tier_3", "country": "Taiwan",
         "region": "Asia Pacific", "category": "raw_silicon",
         "annual_revenue_usd": 5e8, "employee_count": 1000,
         "latitude": 25.0, "longitude": 121.5,
         "historical_delay_rate": 0.08, "risk_score": 0.0, "risk_level": "low"}
        for i in range(3)
    ] + [
        {"id": f"t2-{i}", "name": f"Tier2-{i}", "tier": "tier_2", "country": "China",
         "region": "Asia Pacific", "category": "wafers",
         "annual_revenue_usd": 3e8, "employee_count": 500,
         "latitude": 31.0, "longitude": 121.5,
         "historical_delay_rate": 0.05, "risk_score": 0.0, "risk_level": "low"}
        for i in range(3)
    ] + [
        {"id": "oem-1", "name": "TechForge OEM", "tier": "oem", "country": "USA",
         "region": "North America", "category": "consumer_electronics",
         "annual_revenue_usd": 5e9, "employee_count": 20000,
         "latitude": 37.7, "longitude": -122.4,
         "historical_delay_rate": 0.02, "risk_score": 0.0, "risk_level": "low"}
    ]
    Database.bulk_upsert_suppliers(sups)
    edges = [{"id": str(uuid.uuid4()), "source_supplier_id": f"t3-{i}",
              "target_supplier_id": f"t2-{i}", "component_category": "raw_silicon",
              "lead_time_days": 30, "dependency_weight": 0.8,
              "annual_volume_usd": 1e7, "is_sole_source": 0} for i in range(3)]
    Database.bulk_upsert_edges(edges)
    return {"suppliers": sups, "edges": edges}


# ── Health ─────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "db_connected" in body
    assert "ml_server_reachable" in body

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "RippleGraph AI Backend"

def test_readiness(client):
    assert client.get("/api/v1/health/ready").status_code == 200

def test_liveness(client):
    assert client.get("/api/v1/health/live").status_code == 200


# ── Auth ───────────────────────────────────────────────────────────────────────

def test_register(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": "new@test.com", "password": "secret123", "name": "Alice"})
    assert r.status_code == 201
    body = r.json()
    assert "access_token" in body
    assert body["email"] == "new@test.com"

def test_register_duplicate_email(client):
    client.post("/api/v1/auth/register",
               json={"email": "dup@test.com", "password": "password123", "name": "A"})
    r = client.post("/api/v1/auth/register",
               json={"email": "dup@test.com", "password": "password456", "name": "B"})
    assert r.status_code == 400

def test_login_success(client):
    client.post("/api/v1/auth/register",
                json={"email": "user@test.com", "password": "mypassword", "name": "User"})
    r = client.post("/api/v1/auth/login",
                    json={"email": "user@test.com", "password": "mypassword"})
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_login_wrong_password(client):
    client.post("/api/v1/auth/register",
                json={"email": "u2@test.com", "password": "correct", "name": "U2"})
    r = client.post("/api/v1/auth/login",
                    json={"email": "u2@test.com", "password": "wrong"})
    assert r.status_code == 401

def test_me_authenticated(client, auth_header):
    r = client.get("/api/v1/auth/me", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["email"] == "test@ripple.ai"

def test_me_unauthenticated(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


# ── Suppliers ──────────────────────────────────────────────────────────────────

def test_list_suppliers_empty(client):
    r = client.get("/api/v1/suppliers/")
    assert r.status_code == 200
    assert r.json() == []

def test_list_suppliers_seeded(client, seeded_db):
    r = client.get("/api/v1/suppliers/")
    assert r.status_code == 200
    assert len(r.json()) == 7   # 3 tier_3 + 3 tier_2 + 1 oem

def test_list_suppliers_filter_tier(client, seeded_db):
    r = client.get("/api/v1/suppliers/?tier=tier_3")
    assert r.status_code == 200
    assert len(r.json()) == 3

def test_get_supplier_found(client, seeded_db):
    r = client.get("/api/v1/suppliers/t3-0")
    assert r.status_code == 200
    assert r.json()["tier"] == "tier_3"

def test_get_supplier_not_found(client):
    r = client.get("/api/v1/suppliers/nonexistent")
    assert r.status_code == 404

def test_create_supplier_requires_auth(client):
    data = {"name":"X","tier":"tier_3","country":"TW","region":"Asia Pacific",
            "category":"raw_silicon","annual_revenue_usd":1e8,"employee_count":100,
            "latitude":25.0,"longitude":121.5}
    r = client.post("/api/v1/suppliers/", json=data)
    assert r.status_code == 401

def test_create_supplier_authenticated(client, auth_header):
    data = {"name":"New Supplier","tier":"tier_2","country":"China",
            "region":"Asia Pacific","category":"wafers",
            "annual_revenue_usd":2e8,"employee_count":500,
            "latitude":31.0,"longitude":121.5}
    r = client.post("/api/v1/suppliers/", json=data, headers=auth_header)
    assert r.status_code == 201
    assert r.json()["name"] == "New Supplier"


# ── Events ─────────────────────────────────────────────────────────────────────

def test_list_active_events_empty(client):
    r = client.get("/api/v1/events/active")
    assert r.status_code == 200
    assert r.json() == []

def test_create_event_requires_auth(client, seeded_db):
    data = {"supplier_id":"t3-0","disruption_type":"factory_shutdown",
            "severity":0.85,"description":"Test","affected_capacity_pct":40.0}
    r = client.post("/api/v1/events/", json=data)
    assert r.status_code == 401

def test_create_event_authenticated(client, seeded_db, auth_header):
    with patch("app.services.event_queue.EventQueue.publish", new_callable=AsyncMock):
        data = {"supplier_id":"t3-0","disruption_type":"factory_shutdown",
                "severity":0.85,"description":"Test disruption","affected_capacity_pct":40.0}
        r = client.post("/api/v1/events/", json=data, headers=auth_header)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    assert body["severity"] == 0.85

def test_create_event_invalid_severity(client, auth_header):
    data = {"supplier_id":"t3-0","disruption_type":"factory_shutdown",
            "severity":2.0,"description":"X","affected_capacity_pct":40.0}
    r = client.post("/api/v1/events/", json=data, headers=auth_header)
    assert r.status_code == 422

def test_get_event_not_found(client):
    r = client.get("/api/v1/events/nonexistent")
    assert r.status_code == 404


# ── Graph ──────────────────────────────────────────────────────────────────────

def test_graph_empty(client):
    r = client.get("/api/v1/graph/")
    assert r.status_code == 200
    body = r.json()
    assert body["total_nodes"] == 0
    assert body["total_edges"] == 0

def test_graph_seeded(client, seeded_db):
    r = client.get("/api/v1/graph/")
    assert r.status_code == 200
    body = r.json()
    assert body["total_nodes"] == 7
    assert body["total_edges"] == 3
    assert all("risk_score" in n for n in body["nodes"])


# ── Predictions ────────────────────────────────────────────────────────────────

def test_predictions_summary_empty(client):
    r = client.get("/api/v1/predictions/summary")
    assert r.status_code == 200

def test_predictions_tier_breakdown(client):
    r = client.get("/api/v1/predictions/tier-breakdown")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Database ───────────────────────────────────────────────────────────────────

def test_db_stats(seeded_db):
    from app.services.database import Database
    stats = Database.stats()
    assert stats["suppliers"] == 7
    assert stats["edges"] == 3

def test_db_risk_update(seeded_db):
    from app.services.database import Database
    Database.update_supplier_risk("t3-0", 0.85, "critical")
    sup = Database.get_supplier("t3-0")
    assert sup["risk_score"] == 0.85
    assert sup["risk_level"] == "critical"

def test_db_event_resolve(seeded_db, auth_header, client):
    from app.services.database import Database
    eid = Database.create_event({
        "supplier_id":"t3-0","disruption_type":"factory_shutdown",
        "severity":0.7,"description":"Test","affected_capacity_pct":30.0,
        "source":"test","country":"TW","category":"raw_silicon"
    })["id"]
    Database.resolve_event(eid)
    ev = Database.get_event(eid)
    assert ev["status"] == "resolved"


# ── JWT Auth ───────────────────────────────────────────────────────────────────

def test_jwt_create_and_decode():
    from app.core.auth import create_access_token, decode_token
    token = create_access_token("uid-123", "test@test.com", "Test User")
    payload = decode_token(token)
    assert payload["sub"] == "uid-123"
    assert payload["email"] == "test@test.com"

def test_jwt_invalid_token():
    from app.core.auth import decode_token
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        decode_token("this.is.not.valid")
    assert exc.value.status_code == 401
