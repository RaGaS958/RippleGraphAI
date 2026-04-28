"""
Mock supply chain data generator.
Creates realistic data and saves to data/mock/supply_chain_mock.json
then seeds the local SQLite database.

Usage:
    python -m data.mock.generate_mock_data
"""
import json, random, uuid
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

COMPANIES = {
    "tier_3": [
        ("SiliconBase Corp","raw_silicon","Taiwan","Asia Pacific",25.0,121.5),
        ("RareMetal Solutions","rare_earth_metals","China","Asia Pacific",30.0,114.0),
        ("ChemPure Industries","specialty_chemicals","Germany","Europe",51.5,10.0),
        ("GlassTech Advanced","advanced_glass","Japan","Asia Pacific",35.7,139.7),
        ("PhotoResist Labs","photoresists","South Korea","Asia Pacific",37.5,127.0),
        ("PureQuartz Mining","raw_silicon","Malaysia","Asia Pacific",3.1,101.7),
        ("ElementX Refinery","rare_earth_metals","China","Asia Pacific",28.0,116.0),
        ("NanoMaterial Sciences","specialty_chemicals","Netherlands","Europe",52.4,4.9),
    ],
    "tier_2": [
        ("Wafer Dynamics","wafers","Taiwan","Asia Pacific",24.8,121.0),
        ("PCB Solutions Asia","pcb_substrate","China","Asia Pacific",22.5,113.0),
        ("Passive Tech Korea","passive_components","South Korea","Asia Pacific",36.5,127.9),
        ("DisplayCraft China","display_panels","China","Asia Pacific",31.2,121.5),
        ("CellTech Energy","battery_cells","Japan","Asia Pacific",34.7,135.5),
        ("Board Systems Vietnam","pcb_substrate","Vietnam","Asia Pacific",10.8,106.7),
        ("Component Hub Thailand","passive_components","Thailand","Asia Pacific",13.7,100.5),
        ("Circuit Materials India","wafers","India","South Asia",12.9,77.6),
    ],
    "tier_1": [
        ("SemiCore Systems","semiconductors","Taiwan","Asia Pacific",25.0,121.5),
        ("MemoryTech International","memory_chips","South Korea","Asia Pacific",37.5,127.0),
        ("PowerIC Solutions","power_management_ics","USA","North America",37.8,-122.4),
        ("ScreenTech Global","displays","Japan","Asia Pacific",35.7,139.7),
        ("BatteryPack Industries","battery_packs","China","Asia Pacific",22.5,114.1),
        ("ChipLink Advanced","semiconductors","Taiwan","Asia Pacific",24.5,121.0),
        ("Processor Dynamics","semiconductors","USA","North America",37.3,-121.9),
        ("FlashCore Memory","memory_chips","South Korea","Asia Pacific",37.4,127.1),
    ],
    "oem": [
        ("TechForge OEM","consumer_electronics","USA","North America",37.7,-122.4),
        ("AutoDrive Systems","automotive","Germany","Europe",48.1,11.6),
        ("IndustrialCore Mfg","industrial_equipment","USA","North America",42.4,-83.1),
        ("AeroTech Dynamics","aerospace","France","Europe",48.9,2.4),
        ("MedDevice Global","medical_devices","UK","Europe",51.5,-0.1),
    ],
}

def _sup(tier, name, category, country, region, lat, lon):
    return {
        "id": str(uuid.uuid4()),
        "name": name, "tier": tier,
        "country": country, "region": region, "category": category,
        "annual_revenue_usd": random.uniform(50e6, 5e9),
        "employee_count": random.randint(200, 50_000),
        "latitude": lat + random.uniform(-0.5, 0.5),
        "longitude": lon + random.uniform(-0.5, 0.5),
        "historical_delay_rate": round(random.uniform(0.02, 0.15), 3),
        "risk_score": 0.0, "risk_level": "low",
        "created_at": datetime.utcnow().isoformat(),
    }

def _edge(src_id, tgt_id, category):
    return {
        "id": str(uuid.uuid4()),
        "source_supplier_id": src_id,
        "target_supplier_id": tgt_id,
        "component_category": category,
        "lead_time_days": random.randint(14, 90),
        "dependency_weight": round(random.uniform(0.3, 1.0), 2),
        "annual_volume_usd": random.uniform(1e6, 3e8),
        "is_sole_source": 1 if random.random() < 0.2 else 0,
    }

def _event(supplier, scenario="random"):
    scenarios = {
        "tsmc_shutdown": {
            "disruption_type": "factory_shutdown", "severity": 0.93,
            "description": "Major semiconductor fab shutdown — 45% of global chip supply affected",
            "affected_capacity_pct": 45.0,
        },
        "rare_earth_ban": {
            "disruption_type": "geopolitical", "severity": 0.78,
            "description": "Export controls on rare earth metals — 6-month supply disruption",
            "affected_capacity_pct": 30.0,
        },
        "random": {
            "disruption_type": random.choice([
                "factory_shutdown","natural_disaster","logistics_delay",
                "quality_issue","capacity_constraint"]),
            "severity": round(random.uniform(0.4, 0.9), 2),
            "description": f"Disruption at {supplier['name']}",
            "affected_capacity_pct": round(random.uniform(15, 60), 1),
        },
    }
    base = scenarios.get(scenario, scenarios["random"])
    return {
        "id": str(uuid.uuid4()),
        "supplier_id": supplier["id"],
        "source": "mock_generator",
        "country": supplier["country"],
        "category": supplier["category"],
        "status": "active",
        "estimated_revenue_at_risk_usd": round(random.uniform(1e6, 5e8), 2),
        "created_at": (datetime.utcnow() - timedelta(days=random.randint(0,7))).isoformat(),
        "resolved_at": None,
        **base,
    }

def generate_all() -> dict:
    suppliers = []
    tier_map = {}
    for tier, entries in COMPANIES.items():
        tier_map[tier] = []
        for entry in entries:
            s = _sup(tier, *entry)
            suppliers.append(s)
            tier_map[tier].append(s)

    edges = []
    for t3 in tier_map["tier_3"]:
        for t2 in random.sample(tier_map["tier_2"], k=random.randint(1,3)):
            edges.append(_edge(t3["id"], t2["id"], t3["category"]))
    for t2 in tier_map["tier_2"]:
        for t1 in random.sample(tier_map["tier_1"], k=random.randint(1,4)):
            edges.append(_edge(t2["id"], t1["id"], t2["category"]))
    for t1 in tier_map["tier_1"]:
        for oem in random.sample(tier_map["oem"], k=random.randint(1,3)):
            edges.append(_edge(t1["id"], oem["id"], t1["category"]))

    # Dramatic events — Tier-3 nodes carry hidden risk
    events = []
    events.append(_event(tier_map["tier_3"][0], "tsmc_shutdown"))  # TSMC-like
    events.append(_event(tier_map["tier_3"][1], "rare_earth_ban")) # Rare earth
    for s in tier_map["tier_3"][2:5]:
        events.append(_event(s, "random"))

    return {
        "suppliers": suppliers, "edges": edges, "events": events,
        "stats": {
            "total_suppliers": len(suppliers), "total_edges": len(edges),
            "total_events": len(events),
            "tier_breakdown": {t: len(v) for t, v in tier_map.items()},
        },
    }

if __name__ == "__main__":
    data = generate_all()
    out = Path("data/mock/supply_chain_mock.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Generated → {out}")
    print(f"  Suppliers: {data['stats']['total_suppliers']}")
    print(f"  Edges:     {data['stats']['total_edges']}")
    print(f"  Events:    {data['stats']['total_events']}")
    print(f"  Tiers:     {data['stats']['tier_breakdown']}")
