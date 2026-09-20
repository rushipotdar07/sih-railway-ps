import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DB_PATH = os.environ.get("BLOCK_PLANNING_DB_PATH")
if not DB_PATH:
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "block_planning.db")
DB_PATH = os.path.abspath(DB_PATH)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Drop and recreate all tables (used by /api/admin/reseed)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
