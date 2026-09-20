"""
Ingestion of the real Train Time Table into:
  - Section list (section_id, section_name, zone, division, daily_train_frequency)
  - Free-window derivation per section/day (gaps between scheduled train passages)

This implements Appendix A of the build spec: section_id is an ordered pair of
consecutive station_codes for a given train; daily_train_frequency counts
distinct trains crossing that section per day; free_window is the gap between
consecutive scheduled passages.

real_timetable.csv is derived from the real, public, CC0-licensed Indian
Railways dataset published by the DataMeet open-data community (see
build_real_timetable.py for provenance and regeneration instructions) -
every train number/name/station/timing in it is genuine.
"""
import csv
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TIMETABLE_CSV = os.path.join(DATA_DIR, "real_timetable.csv")

DAY_START = 0          # minutes from midnight
DAY_END = 24 * 60       # 1440
MIN_FREE_WINDOW_MIN = 60  # ignore slivers shorter than this


def _ensure_timetable():
    if not os.path.exists(TIMETABLE_CSV):
        # Fallback only - normally real_timetable.csv ships committed in the
        # repo. This regenerates it from the live DataMeet source (needs
        # network access; downloads ~85MB, takes a minute or two).
        build_script = os.path.join(DATA_DIR, "build_real_timetable.py")
        subprocess.run([sys.executable, build_script], check=True)


def _parse_time(s):
    if not s or s == "None":
        return None
    # Accepts both "HH:MM" (Appendix A's minimal schema) and "HH:MM:SS"
    # (the real DataMeet-sourced data includes seconds) - seconds are
    # dropped, they don't matter at the granularity this system schedules at.
    parts = s.split(":")
    h, m = parts[0], parts[1]
    return int(h) * 60 + int(m)


def load_timetable():
    _ensure_timetable()
    with open(TIMETABLE_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_sections():
    """
    Returns:
      sections: dict section_id -> {section_name, zone, division, daily_train_frequency}
      passages: dict section_id -> sorted list of (dep_minute_from_prev_station, arr_minute_at_next_station)
                 representing when a train occupies that section (using departure at first
                 station and arrival at next station, both clipped to a single day for
                 free-window derivation).
    """
    rows = load_timetable()
    # group rows by train_number in file order (already chronological per train)
    by_train = defaultdict(list)
    for r in rows:
        by_train[r["train_number"]].append(r)

    section_trains = defaultdict(set)   # section_id -> set(train_number) for frequency
    section_meta = {}
    passages = defaultdict(list)        # section_id -> list of (dep_min, arr_min) within a normalized day

    for train_no, stops in by_train.items():
        for i in range(len(stops) - 1):
            a, b = stops[i], stops[i + 1]
            dep = _parse_time(a["departure"])
            arr = _parse_time(b["arrival"])
            if dep is None or arr is None:
                continue
            section_id = f"{a['station_code']}-{b['station_code']}"
            section_name = f"{a['station_name']} - {b['station_name']}"
            section_trains[section_id].add(train_no)
            section_meta[section_id] = {
                "section_name": section_name,
                "zone": a.get("zone") or "NR",
                "division": a.get("division") or "Delhi",
                "from_station": a["station_code"],
                "to_station": b["station_code"],
            }
            # normalize into a single 0-1440 day for free-window derivation
            dep_n = dep % DAY_END
            arr_n = arr % DAY_END
            if arr_n <= dep_n:
                arr_n = min(DAY_END, dep_n + max(30, arr_n))
            passages[section_id].append((dep_n, arr_n))

    sections = {}
    for sid, meta in section_meta.items():
        sections[sid] = {
            **meta,
            "section_id": sid,
            "daily_train_frequency": len(section_trains[sid]),
        }
    return sections, passages


def derive_free_windows(passages_for_section):
    """Given a list of (occupied_start_min, occupied_end_min) for one section/day,
    return the free gaps as (start_min, end_min) covering DAY_START..DAY_END."""
    if not passages_for_section:
        return [(DAY_START, DAY_END)]
    intervals = sorted(passages_for_section)
    merged = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    free = []
    cursor = DAY_START
    for s, e in merged:
        if s - cursor >= MIN_FREE_WINDOW_MIN:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if DAY_END - cursor >= MIN_FREE_WINDOW_MIN:
        free.append((cursor, DAY_END))
    return free


def minutes_to_hhmm(m):
    m = int(m) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


if __name__ == "__main__":
    sections, passages = build_sections()
    print(f"{len(sections)} sections derived from real timetable")
    for sid, meta in list(sections.items())[:5]:
        print(sid, meta)
    sample_sid = next(iter(passages))
    print("Sample free windows for", sample_sid, ":",
          [(minutes_to_hhmm(a), minutes_to_hhmm(b)) for a, b in derive_free_windows(passages[sample_sid])])
