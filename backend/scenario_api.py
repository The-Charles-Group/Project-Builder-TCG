from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import time

router = APIRouter()

class Scenario(BaseModel):
    id: str
    name: str
    createdAt: str | None = None
    updatedAt: str | None = None
    currency: str | None = "USD"
    blendedRate: float | None = None
    hoursPerDay: float | None = None
    deliverables: list[dict]
    totals: dict | None = None

# Simple in-memory persistence; swap with your DB if needed.
_INMEM: Dict[str, Dict[str, Any]] = {}

@router.post("/save")
async def save_scenario(s: Scenario):
    data = s.dict()
    data["_serverSavedAt"] = time.time()
    _INMEM[data["id"]] = data
    return {"ok": True, "id": data["id"], "serverSavedAt": data["_serverSavedAt"]}

@router.get("/active")
async def get_active():
    if "working" in _INMEM:
        return {"ok": True, "scenario": _INMEM["working"]}
    raise HTTPException(status_code=404, detail="No active scenario found")
