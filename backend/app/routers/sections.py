from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Section
from ..schemas import SectionOut

router = APIRouter(prefix="/api/sections", tags=["sections"])


@router.get("", response_model=list[SectionOut])
def list_sections(db: Session = Depends(get_db)):
    return db.query(Section).order_by(Section.section_name).all()


@router.get("/map")
def sections_map_view(db: Session = Depends(get_db)):
    """
    Lightweight network-impact view (Section 10): one row per section with
    its real daily train frequency and current pending-request load, enough
    to color a birds-eye map/list by block-plan density.
    """
    from ..models import MaintenanceRequest
    sections = db.query(Section).all()
    result = []
    for s in sections:
        pending_count = (db.query(MaintenanceRequest)
                          .filter(MaintenanceRequest.section_id == s.section_id)
                          .filter(MaintenanceRequest.status == "PENDING")
                          .count())
        result.append({
            "section_id": s.section_id,
            "section_name": s.section_name,
            "zone": s.zone,
            "division": s.division,
            "daily_train_frequency": s.daily_train_frequency,
            "pending_request_count": pending_count,
        })
    return result
