"""
Seeds the SQLite database from:
  - the real-anchored section list (ingest.py)
  - derived corridor free-windows, materialized as CorridorAvailability rows
    for a rolling 35-day horizon (covers both the 7-day and 30-day plans)
  - synthetic TMS/SMMS/TDMS defect requests (generate_synthetic_data.py),
    generated fresh if the CSVs don't exist yet

Run standalone:  python -m app.services.seed
"""
import csv
import os
from datetime import datetime, timedelta

from ..db import SessionLocal, init_db, reset_db
from ..models import Section, MaintenanceRequest, CorridorAvailability
from . import ingest, generate_synthetic_data

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HORIZON_DAYS = 35
PLANNING_START = datetime(2026, 9, 1)  # matches TODAY anchor in generate_synthetic_data.py


def _ensure_synthetic_csvs():
    needed = ["engineering_requests.csv", "signal_telecom_requests.csv", "traction_requests.csv"]
    if not all(os.path.exists(os.path.join(DATA_DIR, f)) for f in needed):
        generate_synthetic_data.main()


def seed(fresh: bool = True):
    if fresh:
        reset_db()
    else:
        init_db()

    db = SessionLocal()
    try:
        sections_map, passages = ingest.build_sections()

        # --- Sections ---
        for sid, meta in sections_map.items():
            db.add(Section(
                section_id=sid,
                section_name=meta["section_name"],
                zone=meta["zone"],
                division=meta["division"],
                from_station=meta["from_station"],
                to_station=meta["to_station"],
                daily_train_frequency=meta["daily_train_frequency"],
                is_electrified=True,
            ))
        db.commit()
        print(f"Seeded {len(sections_map)} sections")

        # --- CorridorAvailability: materialize free windows for HORIZON_DAYS ---
        avail_count = 0
        for sid in sections_map:
            free_windows = ingest.derive_free_windows(passages.get(sid, []))
            for day_offset in range(HORIZON_DAYS):
                day = PLANNING_START + timedelta(days=day_offset)
                for w_start, w_end in free_windows:
                    db.add(CorridorAvailability(
                        section_id=sid,
                        date=day,
                        window_start=day + timedelta(minutes=w_start),
                        window_end=day + timedelta(minutes=min(w_end, 24 * 60 - 1)),
                        is_used=False,
                    ))
                    avail_count += 1
        db.commit()
        print(f"Seeded {avail_count} corridor availability windows over {HORIZON_DAYS} days")

        # --- Synthetic maintenance requests ---
        _ensure_synthetic_csvs()
        req_count = 0
        for fname in ["engineering_requests.csv", "signal_telecom_requests.csv", "traction_requests.csv"]:
            path = os.path.join(DATA_DIR, fname)
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row["section_id"] not in sections_map:
                        continue
                    db.add(MaintenanceRequest(
                        department=row["department"],
                        section_id=row["section_id"],
                        defect_type=row["defect_type"],
                        severity=row["severity"],
                        reported_date=datetime.strptime(row["reported_date"], "%Y-%m-%d"),
                        overdue_days=int(row["overdue_days"]),
                        preferred_window_start=datetime.strptime(row["preferred_window_start"], "%Y-%m-%d %H:%M"),
                        preferred_window_end=datetime.strptime(row["preferred_window_end"], "%Y-%m-%d %H:%M"),
                        estimated_duration_min=int(row["estimated_duration_min"]),
                        status="PENDING",
                        source="synthetic",
                    ))
                    req_count += 1
        db.commit()
        print(f"Seeded {req_count} synthetic maintenance requests")
    finally:
        db.close()


if __name__ == "__main__":
    seed(fresh=True)
