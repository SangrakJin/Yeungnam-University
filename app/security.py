import os
import secrets
from datetime import datetime, timedelta

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-now")
SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "720"))

def new_token() -> str:
    return secrets.token_urlsafe(48)

def expiry_utc(minutes: int = SESSION_EXPIRE_MINUTES) -> datetime:
    # ✅ naive UTC
    return datetime.utcnow() + timedelta(minutes=minutes)

def require_admin_key(key: str | None) -> bool:
    return bool(key) and key == ADMIN_API_KEY