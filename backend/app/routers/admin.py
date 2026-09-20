from fastapi import APIRouter
from ..services import seed as seed_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reseed")
def reseed():
    """Wipes and rebuilds the DB from the real timetable + fresh synthetic requests."""
    seed_service.seed(fresh=True)
    return {"ok": True, "message": "Database reseeded."}
