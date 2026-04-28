"""
Local JWT auth — uses sha256_crypt instead of bcrypt.
Avoids passlib/bcrypt version incompatibility on Windows.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

logger  = logging.getLogger(__name__)
bearer  = HTTPBearer(auto_error=False)

# sha256_crypt: pure Python, no C extensions, no bcrypt compat issues
pwd_ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_access_token(user_id: str, email: str, name: str = "") -> str:
    cfg    = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=cfg.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "email": email, "name": name,
         "exp": expire, "iat": datetime.now(timezone.utc)},
        cfg.JWT_SECRET, algorithm=cfg.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    cfg = get_settings()
    try:
        return jwt.decode(token, cfg.JWT_SECRET, algorithms=[cfg.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}")


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> dict:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header")
    return decode_token(creds.credentials)


async def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Optional[dict]:
    if not creds:
        return None
    try:
        return decode_token(creds.credentials)
    except HTTPException:
        return None