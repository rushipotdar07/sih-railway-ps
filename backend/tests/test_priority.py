"""
Unit tests for the rule-based priority scoring model (Section 5.1).
Pure-function tests against lightweight fake objects - no DB needed, so
these run in milliseconds and pin down the scoring *formula* itself,
independent of the optimizer/solver.

Run:  cd backend && venv\\Scripts\\python -m pytest tests/test_priority.py -v
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services import priority


def make_request(request_id, department, section_id, severity, overdue_days,
                  preferred_start=None):
    return SimpleNamespace(
        request_id=request_id,
        department=department,
        section_id=section_id,
        severity=severity,
        overdue_days=overdue_days,
        preferred_window_start=preferred_start or datetime(2026, 9, 2, 2, 0),
    )


def make_section(section_id, daily_train_frequency):
    return SimpleNamespace(section_id=section_id, daily_train_frequency=daily_train_frequency)


def test_critical_overdue_busy_section_outranks_minor_fresh_quiet_section():
    """A textbook high-priority case must score above a textbook low-priority
    one - this is the single most important guarantee the scoring model
    makes, since it is what the whole "AI prioritizes correctly" claim rests
    on."""
    sections = {
        "BUSY": make_section("BUSY", 40),
        "QUIET": make_section("QUIET", 2),
    }
    critical = make_request(1, "ENGINEERING", "BUSY", "CRITICAL", overdue_days=10)
    minor = make_request(2, "ENGINEERING", "QUIET", "MINOR", overdue_days=0)

    scored = priority.score_requests([critical, minor], sections)
    by_id = {s.request_id: s for s in scored}

    assert by_id[1].composite_score > by_id[2].composite_score
    # scored list itself must already be sorted descending by composite score
    assert scored[0].request_id == 1


def test_urgency_score_scales_with_overdue_days_relative_to_sla():
    sections = {"S": make_section("S", 5)}
    fresh = make_request(1, "ENGINEERING", "S", "MAJOR", overdue_days=0)
    overdue = make_request(2, "ENGINEERING", "S", "MAJOR", overdue_days=20)  # MAJOR SLA = 10d

    scored = priority.score_requests([fresh, overdue], sections)
    by_id = {s.request_id: s for s in scored}

    assert by_id[2].urgency_score > by_id[1].urgency_score
    # 20 days overdue against a 10-day SLA => urgency = 2.0, clamped to the 1.5 cap
    assert by_id[2].urgency_score == 1.5


def test_network_score_normalized_against_busiest_section_in_batch():
    sections = {"BUSY": make_section("BUSY", 50), "MID": make_section("MID", 25)}
    a = make_request(1, "ENGINEERING", "BUSY", "MAJOR", overdue_days=0)
    b = make_request(2, "ENGINEERING", "MID", "MAJOR", overdue_days=0)

    scored = priority.score_requests([a, b], sections)
    by_id = {s.request_id: s for s in scored}

    assert by_id[1].network_score == 1.0   # busiest section in this batch
    assert by_id[2].network_score == 0.5   # exactly half as busy


def test_coordination_bonus_only_across_different_departments_same_section_close_window():
    sections = {"S": make_section("S", 10)}
    t = datetime(2026, 9, 5, 3, 0)
    eng = make_request(1, "ENGINEERING", "S", "MAJOR", overdue_days=0, preferred_start=t)
    sig = make_request(2, "SIGNAL_TELECOM", "S", "MAJOR", overdue_days=0,
                        preferred_start=t + timedelta(hours=2))  # within 24h tolerance
    other_dept_far = make_request(3, "TRACTION", "S", "MAJOR", overdue_days=0,
                                   preferred_start=t + timedelta(days=5))  # outside tolerance
    same_dept_close = make_request(4, "ENGINEERING", "S", "MAJOR", overdue_days=0,
                                    preferred_start=t + timedelta(hours=1))

    scored = priority.score_requests([eng, sig, other_dept_far, same_dept_close], sections)
    by_id = {s.request_id: s for s in scored}

    assert by_id[1].coordination_bonus == 1.0
    assert by_id[2].coordination_bonus == 1.0
    assert 2 in by_id[1].coordination_partner_ids
    assert by_id[3].coordination_bonus == 0.0   # too far apart in time
    # request 4 is same department as request 1 - coordination bonus is a
    # CROSS-department signal (Section 5.1), so same-department proximity
    # must not trigger it even though the window is close.
    assert 4 not in by_id[1].coordination_partner_ids


def test_severity_ordering_critical_gt_major_gt_minor_all_else_equal():
    sections = {"S": make_section("S", 10)}
    c = make_request(1, "ENGINEERING", "S", "CRITICAL", overdue_days=0)
    m = make_request(2, "ENGINEERING", "S", "MAJOR", overdue_days=0)
    n = make_request(3, "ENGINEERING", "S", "MINOR", overdue_days=0)

    scored = priority.score_requests([c, m, n], sections)
    by_id = {s.request_id: s for s in scored}

    assert by_id[1].composite_score > by_id[2].composite_score > by_id[3].composite_score
