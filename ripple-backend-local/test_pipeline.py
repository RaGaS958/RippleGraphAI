"""
RippleGraph AI — Full Pipeline Test
Tests the complete flow: Auth → Suppliers → Event → ADK Pipeline → Predictions

Run from ripple-backend-local folder:
    python test_pipeline.py
"""

import requests
import time
import json

BASE = "http://localhost:8080/api/v1"
ML   = "http://localhost:8081"


def section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)


def check(label: str, condition: bool, detail: str = ""):
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"  {status}  {label}")
    if detail:
        print(f"          {detail}")
    return condition


# ── 1. ML Server ──────────────────────────────────────────────────────────────
section("1. ML Server (port 8081)")
try:
    r = requests.get(f"{ML}/health", timeout=3)
    data = r.json()
    check("ML server reachable", r.status_code == 200)
    check("Mode is GNN (not stub)", data.get("mode") == "gnn",
          f"mode={data.get('mode')} — set stub_mode: false in ml_config.yaml if stub")
except Exception as e:
    check("ML server reachable", False, f"Start it: python -m ml.serving.prediction_server")


# ── 2. Backend Health ─────────────────────────────────────────────────────────
section("2. Backend Health (port 8080)")
try:
    r = requests.get(f"{BASE}/health", timeout=3)
    data = r.json()
    check("Backend reachable",      r.status_code == 200)
    check("DB connected",           data.get("db_connected") is True)
    check("ML server reachable",    data.get("ml_server_reachable") is True)
    check("Suppliers seeded",       data["db_stats"].get("suppliers", 0) > 0,
          f"suppliers={data['db_stats'].get('suppliers')}")
except Exception as e:
    check("Backend reachable", False, f"Start it: uvicorn app.main:app --port 8080 --reload")
    raise SystemExit(1)


# ── 3. Auth ───────────────────────────────────────────────────────────────────
section("3. Auth — Register + Login")
email    = "pipeline_test@ripple.ai"
password = "testpass9999"

# Register (may already exist — that's fine)
r = requests.post(f"{BASE}/auth/register",
                  json={"email": email, "password": password, "name": "Pipeline Tester"})
if r.status_code == 201:
    token = r.json()["access_token"]
    check("Register new user", True)
elif r.status_code == 400:
    # Already registered — login instead
    r2 = requests.post(f"{BASE}/auth/login",
                       json={"email": email, "password": password})
    check("Login existing user", r2.status_code == 200)
    token = r2.json()["access_token"]
else:
    check("Register/Login", False, r.text)
    raise SystemExit(1)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Verify token works
r = requests.get(f"{BASE}/auth/me", headers=headers)
check("JWT token valid", r.status_code == 200, f"email={r.json().get('email')}")


# ── 4. Suppliers ──────────────────────────────────────────────────────────────
section("4. Suppliers")
r = requests.get(f"{BASE}/suppliers/")
suppliers = r.json()
check("List all suppliers", r.status_code == 200, f"count={len(suppliers)}")

r3 = requests.get(f"{BASE}/suppliers/?tier=tier_3")
tier3 = r3.json()
check("Filter tier_3", len(tier3) > 0, f"tier_3 count={len(tier3)}")

supplier_id = tier3[0]["id"]
supplier_name = tier3[0]["name"]
print(f"\n  → Using supplier: {supplier_name} ({supplier_id[:8]}...)")


# ── 5. Graph ──────────────────────────────────────────────────────────────────
section("5. Supply Chain Graph")
r = requests.get(f"{BASE}/graph/")
graph = r.json()
check("Graph endpoint", r.status_code == 200)
check("Nodes present",  graph["total_nodes"] > 0, f"nodes={graph['total_nodes']}")
check("Edges present",  graph["total_edges"] > 0, f"edges={graph['total_edges']}")


# ── 6. Fire disruption event ──────────────────────────────────────────────────
section("6. Fire Disruption Event → ADK Pipeline")
print(f"\n  Triggering TSMC-style shutdown on {supplier_name}...")
print("  Watch backend terminal for agent logs.\n")

r = requests.post(f"{BASE}/events/", headers=headers, json={
    "supplier_id":          supplier_id,
    "disruption_type":      "factory_shutdown",
    "severity":             0.92,
    "description":          "Major semiconductor fab shutdown — 45% of global chip supply affected",
    "affected_capacity_pct": 45.0,
    "country":              "Taiwan",
    "category":             "raw_silicon",
})
check("Event created (201)", r.status_code == 201, r.text[:100] if r.status_code != 201 else "")

if r.status_code == 201:
    event = r.json()
    event_id = event["id"]
    print(f"  Event ID: {event_id}")
    print(f"  Status:   {event['status']}")

    # ── 7. Wait for ADK pipeline ──────────────────────────────────────────────
    section("7. Waiting for ADK Pipeline (3 seconds)")
    for i in range(3, 0, -1):
        print(f"  {i}...", end="\r")
        time.sleep(1)
    print("  Pipeline should be complete.       ")

    # ── 8. Predictions ────────────────────────────────────────────────────────
    section("8. Risk Predictions")
    r = requests.get(f"{BASE}/predictions/summary")
    summary = r.json()
    check("Predictions summary", r.status_code == 200)
    check("Revenue at risk > 0",
          float(summary.get("total_revenue_at_risk_usd", 0)) > 0,
          f"${summary.get('total_revenue_at_risk_usd', 0)/1e9:.2f}B")
    check("Suppliers affected",
          int(summary.get("affected_suppliers", 0)) > 0,
          f"count={summary.get('affected_suppliers')}")

    print(f"\n  Revenue at risk:    ${float(summary.get('total_revenue_at_risk_usd',0))/1e9:.2f}B")
    print(f"  Critical nodes:     {summary.get('critical_count', 0)}")
    print(f"  High nodes:         {summary.get('high_count', 0)}")
    print(f"  Avg risk score:     {float(summary.get('avg_risk_score',0)):.3f}")

    # Tier breakdown
    r2 = requests.get(f"{BASE}/predictions/tier-breakdown")
    if r2.status_code == 200 and r2.json():
        print("\n  Risk by tier:")
        for row in r2.json():
            print(f"    {row['tier']:<10} avg={float(row['avg_risk']):.3f}  "
                  f"${float(row['total_revenue_at_risk_usd'])/1e6:.0f}M at risk")


# ── 9. WebSocket check ────────────────────────────────────────────────────────
section("9. WebSocket Live Updates")
try:
    import websockets, asyncio

    async def ws_test():
        uri = "ws://localhost:8080/ws/live"
        async with websockets.connect(uri) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(msg)
            return data.get("type")

    ws_type = asyncio.run(ws_test())
    check("WebSocket connects", True, f"first message type={ws_type}")
    check("Receives snapshot", ws_type in ("snapshot", "ping"), f"type={ws_type}")
except ImportError:
    print("  (websockets not installed — skip: pip install websockets)")
except Exception as e:
    check("WebSocket", False, str(e))


# ── Summary ───────────────────────────────────────────────────────────────────
section("SYSTEM STATUS")
print("""
  ML server   → http://localhost:8081  (GNN predictions)
  Backend     → http://localhost:8080  (REST API + ADK pipeline)
  WebSocket   → ws://localhost:8080/ws/live  (live risk scores)

  Both servers must stay running for the frontend to work.
  Next step: start frontend (React + Three.js 3D graph)
""")
