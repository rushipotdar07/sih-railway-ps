"""
FastAPI entrypoint - AI-Powered Automatic Block Planning (SIH26027).

Run from backend/:
    uvicorn app.main:app --reload --port 8000

On first run (empty DB), automatically seeds:
  - real-anchored section list + derived corridor availability (ingest.py)
  - synthetic TMS/SMMS/TDMS requests (generate_synthetic_data.py)
so the dashboard has data to show immediately.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from .db import init_db, engine
from .services import seed as seed_service
from .routers import requests as requests_router
from .routers import sections as sections_router
from .routers import plans as plans_router
from .routers import admin as admin_router

app = FastAPI(
    title="AI-Powered Automatic Block Planning (SIH26027)",
    description="Unified maintenance-request queue + OR-Tools CP-SAT block scheduling engine.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon prototype - tighten before any real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(requests_router.router)
app.include_router(sections_router.router)
app.include_router(plans_router.router)
app.include_router(admin_router.router)


@app.on_event("startup")
def on_startup():
    init_db()
    inspector = inspect(engine)
    if "sections" not in inspector.get_table_names():
        seed_service.seed(fresh=True)
        return
    from .db import SessionLocal
    from .models import Section
    db = SessionLocal()
    try:
        if db.query(Section).count() == 0:
            seed_service.seed(fresh=True)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
