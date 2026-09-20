from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


def _drop_tzinfo(v: datetime) -> datetime:
    """
    The whole system (real timetable, synthetic data, planning horizon) runs
    on naive wall-clock datetimes anchored to a fictional Sept 2026 demo
    timeline - not real UTC. If a client sends a timezone-aware timestamp
    (e.g. JS `Date.toISOString()`), normalize it by dropping the offset
    rather than letting naive/aware arithmetic crash the optimizer later.
    """
    if isinstance(v, datetime) and v.tzinfo is not None:
        return v.replace(tzinfo=None)
    return v


class RequestCreate(BaseModel):
    department: str = Field(..., pattern="^(ENGINEERING|SIGNAL_TELECOM|TRACTION)$")
    section_id: str
    defect_type: str
    severity: str = Field(..., pattern="^(CRITICAL|MAJOR|MINOR)$")
    overdue_days: int = 0
    preferred_window_start: datetime
    preferred_window_end: datetime
    estimated_duration_min: int = 120
    notes: Optional[str] = None

    _strip_tz = field_validator("preferred_window_start", "preferred_window_end")(_drop_tzinfo)


class RequestOut(BaseModel):
    request_id: int
    department: str
    section_id: str
    section_name: Optional[str] = None
    defect_type: str
    severity: str
    reported_date: datetime
    overdue_days: int
    preferred_window_start: Optional[datetime] = None
    preferred_window_end: Optional[datetime] = None
    estimated_duration_min: int
    status: str
    source: str

    class Config:
        from_attributes = True


class SectionOut(BaseModel):
    section_id: str
    section_name: str
    zone: Optional[str] = None
    division: Optional[str] = None
    from_station: Optional[str] = None
    to_station: Optional[str] = None
    daily_train_frequency: int
    is_electrified: bool

    class Config:
        from_attributes = True


class AssignmentOut(BaseModel):
    request_id: int
    department: str
    section_id: str
    section_name: str
    severity: str
    defect_type: str
    assigned_start: Optional[datetime]
    assigned_end: Optional[datetime]
    priority_score: float
    reasoning: str
    is_conflict: bool = False
    coordinated_with: List[int] = []
    # 4-factor breakdown behind priority_score (Section 5.1) - powers the
    # score-breakdown bar in the reasoning popover instead of a bare number.
    urgency_score: float = 0.0
    severity_score: float = 0.0
    network_score: float = 0.0
    coordination_bonus: float = 0.0


class PlanOut(BaseModel):
    horizon: str
    mode: str
    generated_at: datetime
    assignments: List[AssignmentOut]
    unscheduled_request_ids: List[int]
    total_requests: int
    scheduled_count: int
    total_priority_score: float
    conflicts_count: int
    total_downtime_min: int
    engine: Optional[dict] = None


class ComparisonOut(BaseModel):
    naive: PlanOut
    optimized: PlanOut
    metrics: dict


class OverrideRequest(BaseModel):
    request_id: int
    assigned_start: datetime
    assigned_end: datetime

    _strip_tz = field_validator("assigned_start", "assigned_end")(_drop_tzinfo)
