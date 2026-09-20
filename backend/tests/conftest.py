"""
Points the test suite at its own throwaway SQLite file (never the live demo
DB the dev server is using) and seeds it once per test session from the
real timetable + fresh synthetic data - the exact same pipeline the app
uses at startup, so these tests exercise the real code path, not a mock.
"""
import os

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_block_planning.db")
os.environ["BLOCK_PLANNING_DB_PATH"] = TEST_DB_PATH

import pytest  # noqa: E402  (must come after the env var is set)

from app.services import seed as seed_service  # noqa: E402
from app.db import SessionLocal  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    seed_service.seed(fresh=True)
    yield
    # leave the file for post-mortem inspection; harmless to keep around


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
