import os
import sys
import bcrypt
from sqlalchemy.orm import Session
from backend.db.database import SessionLocal
from backend.db.models import User

def seed_admin():
    # NOTE: Schema is managed by Alembic migrations. Do NOT call create_all_tables() here.
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("Admin user already exists.")
            return

        from backend.core.config import get_settings
        settings = get_settings()
        password = settings.auth_password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        new_admin = User(
            username="admin",
            email="admin@savra.local",
            hashed_password=hashed,
            is_admin=True,
            is_beta_authorized=True,
            has_seen_onboarding=True
        )
        db.add(new_admin)
        db.commit()
        print("Default admin created successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
