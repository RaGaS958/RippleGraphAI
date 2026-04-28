"""
Seeds the backend SQLite database from mock JSON.
Run once before starting the server.

Usage:
    python scripts/seed_db.py
    python scripts/seed_db.py --path data/mock/supply_chain_mock.json
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.services.database import Database


def seed(path: str) -> None:
    p = Path(path)
    if not p.exists():
        print(f"Seed file not found: {path}")
        print("Generate it first:")
        print("  python -c \"from data.mock.generate_mock_data import generate_all; import json; json.dump(generate_all(), open('data/mock/supply_chain_mock.json','w'), default=str)\"")
        sys.exit(1)

    with open(p) as f:
        data = json.load(f)

    Database.init()

    n_sup  = Database.bulk_upsert_suppliers(data.get("suppliers", []))
    n_edge = Database.bulk_upsert_edges(data.get("edges", []))
    n_evt  = 0
    for ev in data.get("events", []):
        try:
            Database.create_event(ev)
            n_evt += 1
        except Exception:
            pass

    print(f"\nSeeded backend database at {get_settings().DB_PATH}")
    print(f"  Suppliers: {n_sup}")
    print(f"  Edges:     {n_edge}")
    print(f"  Events:    {n_evt}")
    print(f"\nDB stats: {Database.stats()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="data/mock/supply_chain_mock.json")
    args = parser.parse_args()
    seed(args.path)
