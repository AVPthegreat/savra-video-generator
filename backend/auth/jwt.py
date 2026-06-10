from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.security import get_token_from_cookie
from backend.core.config import get_settings
from backend.db.database import get_db
from backend.db.models import User

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_token_from_cookie),
) -> User:
    """Dependency to get the currently logged-in user from the database."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Enforce that the user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user

def require_beta_authorized(current_user: User = Depends(get_current_user)) -> User:
    """Enforce that the user is authorized for the beta (or is an admin)."""
    if not current_user.is_beta_authorized and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending beta authorization. Please wait for an admin to approve you.",
        )
    return current_user
