
from fastapi import Header, HTTPException
import os

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def require_admin(authorization: str | None = Header(None)):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header (Bearer)")
    token = authorization.split(" ", 1)[1].strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True
