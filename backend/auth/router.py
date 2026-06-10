from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.auth.security import create_access_token, get_password_hash, verify_password
from backend.auth.jwt import get_current_user
from backend.core.config import get_settings
from backend.db.database import get_db
from backend.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Username must be 3-64 characters")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

class UserRead(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_beta_authorized: bool
    has_seen_onboarding: bool

    class Config:
        from_attributes = True

class AuthLoginRequest(BaseModel):
    username: str
    password: str

@router.post("/signup", response_model=UserRead)
def signup(request: UserCreate, db: Session = Depends(get_db)):
    """Public signup for the beta waitlist."""
    # Check if user already exists
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        is_beta_authorized=False # Pending admin approval
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login")
def login(
    response: Response,
    request: AuthLoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user and set a secure HttpOnly cookie."""
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    token = create_access_token(subject=user.username)
    
    # Standard secure cookie (SameSite=Lax works now because of the Vercel Proxy)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True, 
        samesite="lax",
        max_age=3600 * 24 * 7 # 1 week
    )
    return {"status": "ok", "message": "Logged in successfully"}

@router.post("/logout")
def logout(response: Response):
    """Clear the authentication cookie."""
    response.delete_cookie("access_token")
    return {"status": "ok", "message": "Logged out successfully"}

@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the current user's profile."""
    return current_user
