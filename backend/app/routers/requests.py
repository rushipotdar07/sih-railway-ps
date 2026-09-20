from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MaintenanceRequest, Section
from ..schemas import RequestCreate, RequestOut

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.post("", response_model=RequestOut)
def submit_request(payload: RequestCreate, db: Session = Depends(get_db)):
    """
    The single shared submission endpoint behind the three department forms
    (Engineering / Signal & Telecom / Traction) - this IS the BDMS-lite
    unified queue described in Section 1 & 4: one endpoint, one table,
    tagged by department.
    """
    section = db.query(Section).filter(Section.section_id == payload.section_id).first()
    if not section:
        raise HTTPException(404, f"Unknown section_id '{payload.section_id}'")
    if payload.department == "TRACTION" and not section.is_electrified:
        raise HTTPException(400, "Traction requests require an electrified section")

    overdue_days = payload.overdue_days
    req = MaintenanceRequest(
        department=payload.department,
        section_id=payload.section_id,
        defect_type=payload.defect_type,
        severity=payload.severity,
        reported_date=datetime.utcnow(),
        overdue_days=overdue_days,
        preferred_window_start=payload.preferred_window_start,
        preferred_window_end=payload.preferred_window_end,
        estimated_duration_min=payload.estimated_duration_min,
        status="PENDING",
        source="live",
        notes=payload.notes,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    out = RequestOut.model_validate(req)
    out.section_name = section.section_name
    return out


@router.get("", response_model=list[RequestOut])
def list_requests(department: Optional[str] = None, status: Optional[str] = None,
                   db: Session = Depends(get_db)):
    """The unified BDMS-lite queue/inbox - optionally filtered by department or status."""
    q = db.query(MaintenanceRequest)
    if department:
        q = q.filter(MaintenanceRequest.department == department)
    if status:
        q = q.filter(MaintenanceRequest.status == status)
    reqs = q.order_by(MaintenanceRequest.reported_date.desc()).all()
    sections = {s.section_id: s for s in db.query(Section).all()}
    out = []
    for r in reqs:
        o = RequestOut.model_validate(r)
        sec = sections.get(r.section_id)
        o.section_name = sec.section_name if sec else r.section_id
        out.append(o)
    return out


@router.delete("/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db)):
    req = db.query(MaintenanceRequest).filter(MaintenanceRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(404, "Request not found")
    db.delete(req)
    db.commit()
    return {"ok": True}
