from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from backend.auth.jwt import require_admin
from backend.auth.security import get_password_hash
from backend.db.database import get_db
from backend.db import crud
from backend.db.models import User

router = APIRouter(prefix="/admin", tags=["admin"])

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_beta_authorized: bool
    created_at: str

    class Config:
        from_attributes = True

class UserCreateAdmin(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=8)
    is_admin: bool = False
    is_beta_authorized: bool = True

class ApproveUserRequest(BaseModel):
    authorized: bool

@router.get("/users", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """List all registered users for moderation."""
    users = crud.list_users(db)
    # Safely convert datetimes to string
    def safe_iso(dt):
        return dt.isoformat() if dt else "Unknown"

    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            is_admin=u.is_admin,
            is_beta_authorized=u.is_beta_authorized,
            created_at=safe_iso(u.created_at)
        ) for u in users
    ]

@router.put("/users/{user_id}/approve")
def approve_user(
    user_id: int,
    body: ApproveUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Grant or revoke beta access to a user."""
    user = crud.update_user_beta_access(db, user_id, body.authorized)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok", "is_beta_authorized": user.is_beta_authorized}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Permanently delete a user. Cannot delete self or other admins."""
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete administrative accounts")
    
    if target_user.id == admin.id:
        raise HTTPException(status_code=403, detail="Self-deletion is prohibited")
    
    crud.delete_user(db, user_id)
    return {"status": "ok", "message": "User deleted successfully"}

@router.post("/users/create", response_model=UserResponse)
def create_user_direct(
    request: UserCreateAdmin,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Manually create a user (pre-approved)."""
    if crud.get_user_by_username(db, request.username):
        raise HTTPException(status_code=400, detail="Username exists")
    
    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        is_admin=request.is_admin,
        is_beta_authorized=request.is_beta_authorized,
        has_seen_onboarding=True # Admin-created users don't need onboarding pop-up
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)

@router.get("/jobs")
def get_all_jobs(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Global job monitoring for the admin."""
    jobs = crud.list_jobs(db, limit=100)
    return jobs

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Global system metrics."""
    try:
        jobs = crud.list_jobs(db, limit=500)
        
        stats = {
            "total_users": db.query(User).count(),
            "beta_users": db.query(User).filter(User.is_beta_authorized == True).count(),
            "total_jobs": len(jobs),
            "failed_jobs": sum(1 for j in jobs if j.status == "failed"),
            "completed_jobs": sum(1 for j in jobs if j.status == "completed"),
        }
        return stats
    except Exception as e:
        # Catch and log the error instead of returning 500
        import logging
        logging.error(f"Stats Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database Stats Error: {str(e)}")
