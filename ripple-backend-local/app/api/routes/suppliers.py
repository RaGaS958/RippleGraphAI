"""Supplier CRUD routes."""
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.auth import get_current_user
from app.models.schemas import Supplier, SupplierCreate
from app.services.database import Database

router = APIRouter()

@router.get("/", response_model=list[Supplier])
def list_suppliers(tier: Optional[str] = Query(None), limit: int = Query(200, le=500)):
    rows = Database.list_suppliers(tier=tier, limit=limit)
    return [Supplier(**r) for r in rows]

@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier(supplier_id: str):
    s = Database.get_supplier(supplier_id)
    if not s: raise HTTPException(404, "Supplier not found")
    return Supplier(**s)

@router.post("/", response_model=Supplier, status_code=201)
def create_supplier(data: SupplierCreate, _=Depends(get_current_user)):
    doc = Database.create_supplier({"id": str(uuid.uuid4()), **data.model_dump()})
    return Supplier(**doc)

@router.get("/{supplier_id}/downstream")
def downstream(supplier_id: str):
    ids = Database.get_downstream_ids(supplier_id)
    return {"supplier_id": supplier_id, "downstream_ids": ids, "count": len(ids)}
