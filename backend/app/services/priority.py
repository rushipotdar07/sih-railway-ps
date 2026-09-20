"""
Rule-based, transparent Priority Scoring Model (Section 5.1 of the build spec).

score = 0.35 * urgency + 0.30 * severity + 0.20 * network_impact + 0.15 * coordination_bonus

All sub-scores are normalized to [0, 1] so the composite is also roughly [0, 1]
(coordination bonus can push slightly above 1, which is fine - it's a reward).
Every score ships with a plain-English `reasoning` string for the UI
(Section 9: "Priority score and reasoning should be visible on click/hover").
"""
from dataclasses import dataclass, field
from typing import Optional

SEVERITY_WEIGHT = {"CRITICAL": 1.0, "MAJOR": 0.6, "MINOR": 0.3}
SEVERITY_SLA_DAYS = {"CRITICAL": 3, "MAJOR": 10, "MINOR": 30}

W_URGENCY = 0.35
W_SEVERITY = 0.30
W_NETWORK = 0.20
W_COORD = 0.15

COORD_WINDOW_TOLERANCE_HOURS = 24  # requests within this window on the same section may be coordinated


@dataclass
class ScoredRequest:
    request_id: int
    department: str
    section_id: str
    severity: str
    overdue_days: int
    daily_train_frequency: int
    urgency_score: float
    severity_score: float
    network_score: float
    coordination_bonus: float
    composite_score: float
    reasoning: str
    coordination_partner_ids: list = field(default_factory=list)


def _urgency_score(severity: str, overdue_days: int) -> float:
    sla = SEVERITY_SLA_DAYS.get(severity, 10)
    return max(0.0, min(1.5, overdue_days / sla))  # allow >1 for badly overdue items


def _network_score(daily_train_frequency: int, max_frequency: int) -> float:
    if max_frequency <= 0:
        return 0.0
    return min(1.0, daily_train_frequency / max_frequency)


def find_coordination_pairs(requests):
    """
    Detect requests from DIFFERENT departments on the SAME section whose
    preferred windows are within COORD_WINDOW_TOLERANCE_HOURS of each other.
    Returns dict request_id -> set(partner_request_ids).
    """
    from collections import defaultdict
    by_section = defaultdict(list)
    for r in requests:
        by_section[r.section_id].append(r)

    partners = defaultdict(set)
    tol = COORD_WINDOW_TOLERANCE_HOURS * 3600
    for section_id, reqs in by_section.items():
        for i in range(len(reqs)):
            for j in range(i + 1, len(reqs)):
                a, b = reqs[i], reqs[j]
                if a.department == b.department:
                    continue
                if not a.preferred_window_start or not b.preferred_window_start:
                    continue
                diff = abs((a.preferred_window_start - b.preferred_window_start).total_seconds())
                if diff <= tol:
                    partners[a.request_id].add(b.request_id)
                    partners[b.request_id].add(a.request_id)
    return partners


def score_requests(requests, sections_by_id):
    """
    requests: list of MaintenanceRequest ORM objects (PENDING)
    sections_by_id: dict section_id -> Section ORM object
    Returns list[ScoredRequest], sorted by composite_score descending.
    """
    max_freq = max((s.daily_train_frequency or 0 for s in sections_by_id.values()), default=1)
    coord_partners = find_coordination_pairs(requests)

    scored = []
    for r in requests:
        section = sections_by_id.get(r.section_id)
        freq = section.daily_train_frequency if section else 0

        urgency = _urgency_score(r.severity, r.overdue_days or 0)
        severity = SEVERITY_WEIGHT.get(r.severity, 0.3)
        network = _network_score(freq, max_freq)
        partners = coord_partners.get(r.request_id, set())
        coord_bonus = 1.0 if partners else 0.0

        composite = (W_URGENCY * urgency + W_SEVERITY * severity +
                     W_NETWORK * network + W_COORD * coord_bonus)

        reasons = []
        if r.severity == "CRITICAL":
            reasons.append("Critical severity")
        elif r.severity == "MAJOR":
            reasons.append("Major severity")
        else:
            reasons.append("Minor severity")
        reasons.append(f"{r.overdue_days or 0}d overdue (SLA {SEVERITY_SLA_DAYS.get(r.severity, 10)}d)")
        reasons.append(f"section carries {freq} trains/day")
        if partners:
            reasons.append(f"can be coordinated with {len(partners)} other department request(s)")
        reasoning = ", ".join(reasons) + "."

        scored.append(ScoredRequest(
            request_id=r.request_id,
            department=r.department,
            section_id=r.section_id,
            severity=r.severity,
            overdue_days=r.overdue_days or 0,
            daily_train_frequency=freq,
            urgency_score=round(urgency, 3),
            severity_score=round(severity, 3),
            network_score=round(network, 3),
            coordination_bonus=coord_bonus,
            composite_score=round(composite, 4),
            reasoning=reasoning,
            coordination_partner_ids=sorted(partners),
        ))

    scored.sort(key=lambda s: s.composite_score, reverse=True)
    return scored
