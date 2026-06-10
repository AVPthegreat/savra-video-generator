import os
from sqlalchemy import create_url, create_engine, text
from backend.core.config import get_settings

def migrate_production_db():
    settings = get_settings()
    db_url = settings.database_url
    
    print(f"Connecting to database to apply emergency schema fix...")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("Checking for missing columns in 'jobs' table...")
        try:
            # Add user_id column if it doesn't exist
            # Note: This uses raw SQL because it's the most reliable way to modify an existing table without Alembic
            conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;"))
            conn.commit()
            print("SUCCESS: 'user_id' column added to 'jobs' table.")
        except Exception as e:
            print(f"ERROR: Could not add column. It might already exist or the table is missing. Error: {e}")

if __name__ == "__main__":
    migrate_production_db()
