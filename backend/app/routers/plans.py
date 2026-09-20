from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import PlanOut, AssignmentOut, ComparisonOut, OverrideRequest
from ..services import optimizer as optimizer_service

router = APIRouter(prefix="/api/plans", tags=["plans"])

VALID_HORIZONS = {"WEEKLY", "MONTHLY"}
PLANNING_START = datetime(2026, 9, 1)  # matches the anchor used when seeding synthetic data


def _validate_horizon(horizon: str) -> str:
    h = horizon.upper()
    if h not in VALID_HORIZONS:
        raise HTTPException(400, "horizon must be WEEKLY or MONTHLY")
    return h


def _to_plan_out(result) -> PlanOut:
    return PlanOut(
        horizon=result.horizon,
        mode=result.mode,
        generated_at=result.generated_at,
        assignments=[AssignmentOut(**a.__dict__) for a in result.assignments],
        unscheduled_request_ids=result.unscheduled_request_ids,
        total_requests=result.total_requests,
        scheduled_count=result.scheduled_count,
        total_priority_score=result.total_priority_score,
        conflicts_count=result.conflicts_count,
        total_downtime_min=result.total_downtime_min,
        engine=result.engine,
    )


@router.get("/{horizon}", response_model=PlanOut)
def get_plan(horizon: str, mode: str = "optimized", db: Session = Depends(get_db)):
    """
    Runs the AI engine fresh against the current unified request queue.
    mode=optimized -> OR-Tools CP-SAT plan (Section 5.2)
    mode=naive     -> today's decentralized/manual baseline (Section 10 before/after)
    """
    h = _validate_horizon(horizon)
    if mode.lower() == "naive":
        result = optimizer_service.naive_plan(db, h, PLANNING_START)
    else:
        result = optimizer_service.optimize_plan(db, h, PLANNING_START)
    return _to_plan_out(result)


@router.get("/{horizon}/compare", response_model=ComparisonOut)
def compare_plan(horizon: str, db: Session = Depends(get_db)):
    """The before/after comparison (Section 10) - the strongest demo asset."""
    h = _validate_horizon(horizon)
    naive = optimizer_service.naive_plan(db, h, PLANNING_START)
    optimized = optimizer_service.optimize_plan(db, h, PLANNING_START)
    metrics = optimizer_service.compare(naive, optimized)
    return ComparisonOut(
        naive=_to_plan_out(naive),
        optimized=_to_plan_out(optimized),
        metrics=metrics,
    )


@router.post("/{horizon}/override", response_model=PlanOut)
def override_plan(horizon: str, payload: OverrideRequest, db: Session = Depends(get_db)):
    """
    What-if re-optimization (Section 10): controller pins one request to a
    manually chosen window; the engine re-solves everything else around it.
    """
    h = _validate_horizon(horizon)
    locked = {payload.request_id: (payload.assigned_start, payload.assigned_end)}
    result = optimizer_service.optimize_plan(db, h, PLANNING_START, locked_overrides=locked)
    return _to_plan_out(result)
