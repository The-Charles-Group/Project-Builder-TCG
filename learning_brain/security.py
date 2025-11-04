from fastapi import Header, HTTPException
import os
import secrets

# Generate a secure default token if ADMIN_TOKEN is not set in environment
# This token will be consistent for the session but secure by default
DEFAULT_SECURE_TOKEN = "dev_token_" + secrets.token_urlsafe(24)  # Prefix for easy identification
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", DEFAULT_SECURE_TOKEN)

# Always print token on startup for development (remove in production)
print("=" * 60)
print("[LEARNING BRAIN] Admin Authentication Configured")
if os.getenv("ADMIN_TOKEN") is None:
    print(f"[LEARNING BRAIN] Using DEFAULT admin token: {ADMIN_TOKEN}")
    print("[LEARNING BRAIN] Set ADMIN_TOKEN environment variable for production")
else:
    print("[LEARNING BRAIN] Using custom ADMIN_TOKEN from environment")
print("=" * 60)

def require_admin(authorization: str | None = Header(None)):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header (Bearer)")
    token = authorization.split(" ", 1)[1].strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True