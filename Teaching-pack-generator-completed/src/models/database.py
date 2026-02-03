"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from pathlib import Path
from typing import Generator

from models.database_models import Base

# Determine absolute path to the database to avoid CWD issues
# Assumes database.py is in src/models/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "teaching_pack.db"

# Database URL from environment or default to SQLite for development
# If using default sqlite, use the absolute path we calculated
env_db_url = os.getenv("DATABASE_URL")
if env_db_url:
    DATABASE_URL = env_db_url
else:
    # Handle Windows path separators correctly for SQLAlchemy URL
    # SQLite URL format: sqlite:///C:/path/to/file.db
    clean_path = str(DB_PATH).replace('\\', '/')
    DATABASE_URL = f"sqlite:///{clean_path}"

print(f"DEBUG: Using Database URL: {DATABASE_URL}")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """
    Create all database tables
    """
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """
    Drop all database tables (for testing/reset)
    """
    Base.metadata.drop_all(bind=engine)
