"""Graph data route — feeds the 3D visualisation."""
from fastapi import APIRouter
from app.services.database import Database
from app.models.schemas import SupplyChainGraph, GraphNode, GraphEdge

router = APIRouter()

@router.get("/", response_model=SupplyChainGraph)
def get_graph():
    suppliers = Database.list_suppliers()
    edges     = Database.list_edges()
    nodes = [GraphNode(
        id=s["id"], name=s["name"], tier=s["tier"], country=s["country"],
        risk_score=float(s.get("risk_score",0)),
        risk_level=str(s.get("risk_level","low")),
        latitude=float(s.get("latitude",0)), longitude=float(s.get("longitude",0)),
        annual_revenue_usd=float(s.get("annual_revenue_usd",0)),
        category=s.get("category",""),
    ) for s in suppliers]
    graph_edges = [GraphEdge(
        id=e["id"], source=e["source_supplier_id"], target=e["target_supplier_id"],
        lead_time_days=int(e.get("lead_time_days",30)),
        dependency_weight=float(e.get("dependency_weight",0.5)),
        is_sole_source=bool(e.get("is_sole_source",False)),
    ) for e in edges]
    return SupplyChainGraph(nodes=nodes, edges=graph_edges,
                            total_nodes=len(nodes), total_edges=len(graph_edges))
