from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Request, HTTPException, status
from backend.core.config import get_settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if the provided password matches the stored hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    """Generate a secure hash for a password."""
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')

def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode = {"sub": subject, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def get_token_from_cookie(request: Request) -> str:
    """Extract the JWT token from the Authorization header (primary) or cookie (fallback)."""
    # 1. Check Header (Modern/Reliable for Cross-Domain)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    
    # 2. Check Cookie (Legacy/Local Dev)
    token = request.cookies.get("access_token")
    if token:
        return token
        
    # 3. Fail if neither exists
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
