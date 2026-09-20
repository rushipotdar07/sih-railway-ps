"""
Integration tests against the real seeded DB (real timetable + fresh
synthetic requests) and the real OR-Tools CP-SAT optimizer - these are the
tests that actually prove the "AI produces a correct, conflict-free
schedule" claim, rather than just eyeballing a demo screenshot.

Run:  cd backend && venv\\Scripts\\python -m pytest tests/test_optimizer.py -v
"""
from datetime import datetime, timedelta

from app.models import MaintenanceRequest, CorridorAvailability
from app.services import optimizer as optimizer_service

HORIZONS = ["WEEKLY", "MONTHLY"]


def _independent_overlap_count(assignments):
    """Re-implements the overlap check from scratch (not by calling the
    module under test) so a bug in _count_conflicts itself couldn't hide a
    real scheduling conflict from this test."""
    by_section = {}
    for a in assignments:
        if a.assigned_start:
            by_section.setdefault(a.section_id, []).append((a.assigned_start, a.assigned_end))
    total = 0
    for section_id, ivs in by_section.items():
        ivs.sort()
        for i in range(len(ivs)):
            for j in range(i + 1, len(ivs)):
                s1, e1 = ivs[i]
                s2, e2 = ivs[j]
                if s1 < e2 and s2 < e1:
                    total += 1
    return total


def test_optimized_plan_has_zero_overlaps_on_every_horizon(db):
    for horizon in HORIZONS:
        result = optimizer_service.optimize_plan(db, horizon)
        assert _independent_overlap_count(result.assignments) == 0, (
            f"{horizon}: optimizer produced overlapping blocks on the same section"
        )
        assert result.conflicts_count == 0


def test_naive_baseline_has_strictly_more_conflicts_than_optimized(db):
    """This is the literal claim the whole project rests on - re-verify it
    numerically, not just by looking at a screenshot."""
    for horizon in HORIZONS:
        naive = optimizer_service.naive_plan(db, horizon)
        optimized = optimizer_service.optimize_plan(db, horizon)
        assert naive.conflicts_count > 0, (
            f"{horizon}: seeded synthetic data no longer reproduces any naive "
            f"conflicts - the before/after demo has nothing to show"
        )
        assert optimized.conflicts_count < naive.conflicts_count


def test_every_assignment_fits_inside_a_real_availability_window(db):
    """No block may be scheduled on top of real scheduled train traffic -
    checked directly against the CorridorAvailability rows derived from the
    real timetable, independent of the solver's own bookkeeping."""
    result = optimizer_service.optimize_plan(db, "WEEKLY")
    checked = 0
    for a in result.assignments:
        if not a.assigned_start:
            continue
        rows = (
            db.query(CorridorAvailability)
            .filter(CorridorAvailability.section_id == a.section_id)
            .filter(CorridorAvailability.window_start <= a.assigned_start)
            .filter(CorridorAvailability.window_end >= a.assigned_end)
            .all()
        )
        assert rows, (
            f"request #{a.request_id} on {a.section_id} was assigned "
            f"{a.assigned_start}-{a.assigned_end}, which is not fully inside "
            f"any real free corridor window"
        )
        checked += 1
    assert checked > 0, "no scheduled assignments were found to check"


def test_assignment_duration_matches_requested_duration(db):
    result = optimizer_service.optimize_plan(db, "WEEKLY")
    req_duration = {
        r.request_id: r.estimated_duration_min
        for r in db.query(MaintenanceRequest).all()
    }
    checked = 0
    for a in result.assignments:
        if not a.assigned_start:
            continue
        actual_min = (a.assigned_end - a.assigned_start).total_seconds() / 60
        assert actual_min == req_duration[a.request_id]
        checked += 1
    assert checked > 0


def test_solver_reports_optimal_or_feasible(db):
    for horizon in HORIZONS:
        result = optimizer_service.optimize_plan(db, horizon)
        assert result.engine["status"] in ("OPTIMAL", "FEASIBLE"), (
            f"{horizon}: solver did not find a valid solution "
            f"(status={result.engine['status']}) - something is over-constrained"
        )


def test_majority_of_scheduled_requests_land_near_their_preferred_window(db):
    """Regression guard for the preferred-window fix: the optimizer must
    actually use preferred_window_start as a soft preference, not ignore it
    and grab an arbitrary free slot.

    Checked against MONTHLY, not WEEKLY: the synthetic generator spreads
    preferred windows up to 28 days out (generate_synthetic_data.py), so most
    requests' genuine preference falls outside a 7-day horizon entirely -
    that's a horizon-length mismatch, not a sign the preference term isn't
    working. MONTHLY (30d) is the horizon where nearly every synthetic
    preference is actually reachable, making it the fair check.
    """
    result = optimizer_service.optimize_plan(db, "MONTHLY")
    req_pref = {
        r.request_id: r.preferred_window_start
        for r in db.query(MaintenanceRequest).all()
    }
    scheduled = [a for a in result.assignments if a.assigned_start]
    assert scheduled, "no requests were scheduled - cannot check preference adherence"

    within_a_day = 0
    for a in scheduled:
        pref = req_pref.get(a.request_id)
        if not pref:
            continue
        dev_hours = abs((a.assigned_start - pref).total_seconds()) / 3600
        if dev_hours <= 24:
            within_a_day += 1

    ratio = within_a_day / len(scheduled)
    assert ratio >= 0.5, (
        f"only {ratio:.0%} of scheduled requests landed within 24h of their "
        f"preferred window - preference term may not be wired into the objective"
    )


def test_override_pins_the_request_to_exactly_the_requested_window(db):
    pending = db.query(MaintenanceRequest).filter(MaintenanceRequest.status == "PENDING").first()
    assert pending is not None

    start = datetime(2026, 9, 3, 2, 0)
    end = start + timedelta(minutes=pending.estimated_duration_min)
    result = optimizer_service.optimize_plan(
        db, "WEEKLY", locked_overrides={pending.request_id: (start, end)}
    )
    match = next(a for a in result.assignments if a.request_id == pending.request_id)
    assert match.assigned_start == start
    assert match.assigned_end == end
    # everything else must still be conflict-free around the pinned block
    assert _independent_overlap_count(result.assignments) == 0


def test_compare_metrics_are_internally_consistent(db):
    naive = optimizer_service.naive_plan(db, "WEEKLY")
    optimized = optimizer_service.optimize_plan(db, "WEEKLY")
    metrics = optimizer_service.compare(naive, optimized)

    assert metrics["naive_downtime_min"] == naive.total_downtime_min
    assert metrics["optimized_downtime_min"] == optimized.total_downtime_min
    assert metrics["conflicts_avoided"] == max(0, naive.conflicts_count - optimized.conflicts_count)
    if naive.total_downtime_min > 0:
        expected_pct = round(
            100 * (naive.total_downtime_min - optimized.total_downtime_min) / naive.total_downtime_min, 1
        )
        assert metrics["downtime_reduction_pct"] == expected_pct
