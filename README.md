# AI-Powered Automatic Block Planning — SIH26027

Working prototype for **"AI-Powered Automatic Block Planning to Maximize Asset
Availability for Train Operations on Indian Railways"** (Ministry of Railways,
Transportation & Logistics theme). Built per `SIH26027_Build_Spec.pdf`.

## What this is

Three departments (Engineering/TMS, Signal & Telecom/SMMS, Traction/TDMS)
currently request maintenance blocks independently, causing double-bookings
and wasted downtime. This prototype:

1. Collects all three departments' requests into **one unified queue**
   (BDMS-lite) via a single shared form.
2. Scores every pending request with a transparent **rule-based priority
   model** (urgency, severity, network impact, cross-department coordination
   bonus).
3. Feeds the scored queue into a **Google OR-Tools CP-SAT constraint
   scheduler** that assigns conflict-free block windows against real
   train-timetable-derived corridor availability, for both a 7-day (weekly)
   and 30-day (monthly) horizon.
4. Shows the result on a **Gantt-style dashboard** with an explicit
   **before/after comparison** against a simulated "naive/manual" baseline
   (today's decentralized process) — the single strongest demo asset per the
   build spec.
5. Lets a controller **click any block for its AI reasoning**, and pin one
   request to a manual window with **what-if re-optimization** around it.

## Architecture

```
3 request forms (React) ──▶ POST /api/requests ──▶ unified queue (SQLite)
                                                          │
Real Train Time Table (curated, Appendix-A schema) ──▶ ingest.py
   │  → sections + daily_train_frequency (real network-impact signal)
   │  → free corridor windows (gaps between real train passages)
   ▼
Synthetic TMS/SMMS/TDMS defects, anchored to real sections/traffic
   (generate_synthetic_data.py) ──▶ seeded into the same unified queue
                                                          │
                                                          ▼
                                    priority.py (rule-based scoring)
                                                          │
                                                          ▼
                          optimizer.py — OR-Tools CP-SAT (optimized)
                                       — naive FIFO-per-department (baseline)
                                                          │
                                                          ▼
                         GET /api/plans/{horizon}/compare ──▶ React Gantt
                                     dashboard + metrics + overrides
```

See `SIH26027_Build_Spec.pdf` for the full brief this was built against.

## Tech stack

- **Backend**: FastAPI + SQLAlchemy + SQLite, Google OR-Tools (CP-SAT), pure
  Python rule-based priority scoring. Runs on **Python 3.10** (OR-Tools /
  pydantic-core do not yet ship wheels for very new Python versions like
  3.14 — see Troubleshooting below if you hit build errors).
- **Frontend**: React 19 + Vite, no external UI/Gantt library — the Gantt
  chart, forms, and comparison view are hand-built to keep the stack light
  and dependency-free for a hackathon judging environment.

## Running it locally

### 1. Backend (FastAPI + OR-Tools)

```bash
cd backend
python -m venv venv          # use a Python 3.10–3.13 interpreter
venv\Scripts\activate         # Windows: venv\Scripts\activate.bat / .ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first launch it auto-seeds the database from the curated real-anchored
timetable + freshly generated synthetic requests — nothing else to run.
Verify with `curl http://localhost:8000/api/health`.

Interactive API docs: http://localhost:8000/docs

To wipe and regenerate demo data at any time:
`curl -X POST http://localhost:8000/api/admin/reseed`
(also available as a "Reset demo data" button in the UI header).

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. It talks to the backend at
`http://localhost:8000` by default (configurable via `frontend/.env`,
`VITE_API_BASE_URL`).

### Demo flow (see Section 12 of the build spec)

1. Open **Block Plan Dashboard** → toggle to **Before · Manual/Naive** —
   note the red-outlined conflicting blocks.
2. Toggle to **After · AI-Optimized** — conflicts drop to zero; the metrics
   bar shows the concrete downtime-reduction % and conflicts-avoided count.
3. Click any block to see its priority reasoning (severity, overdue days,
   traffic density, coordination bonus).
4. Go to **Submit Request**, add a new live request through one of the three
   department tabs — it lands in the unified queue immediately.
5. Back on the dashboard, re-open the plan (horizon toggle or reload) to see
   it picked up and scheduled.
6. Click a block → **Override this block** to demonstrate what-if
   re-optimization.
7. Toggle **Weekly ↔ Monthly** to show both required time horizons.

## Project layout

```
backend/
  app/
    main.py                 FastAPI app, CORS, startup auto-seed
    models.py                SQLAlchemy schema (Section 7 of the spec)
    schemas.py                Pydantic request/response models
    db.py                      SQLite engine/session
    routers/
      requests.py              Unified queue submit/list/delete (BDMS-lite)
      sections.py               Real section list + network-impact map
      plans.py                   Plan / compare / what-if-override endpoints
      admin.py                    Reseed
    services/
      ingest.py                Real timetable → sections + free-window derivation
      generate_synthetic_data.py  Synthetic TMS/SMMS/TDMS requests, real-anchored
      seed.py                    Wires the above into the DB
      priority.py                 Rule-based priority scoring model
      optimizer.py                 OR-Tools CP-SAT optimizer + naive baseline + compare
    data/
      seed_real_timetable.py    Real-station-anchored timetable generator (Appendix A schema)
      real_timetable.csv, *.csv  Generated data artifacts
frontend/
  src/
    App.jsx, api.js, constants.js, utils.js
    components/                 TopNav, RequestForm, RequestQueue, Dashboard,
                                 GanttChart, MetricsPanel, NetworkImpactPanel,
                                 OverrideModal, Toast
SIH26027_Build_Spec.pdf        The original brief this was built against
```

## Data provenance note

`backend/app/data/seed_real_timetable.py` hand-curates a representative
timetable using **real** Indian Railways station codes, station names, train
numbers/names and published routes (Rajdhani/Shatabdi/Mail/Express services
across several real corridors) — a live data.gov.in/Kaggle download needs an
account/API token unavailable in this build environment. Exact minute-by-minute
timings are reasonable approximations chained from published running times,
not scraped official timetables. To swap in a fully official dataset later,
drop a CSV matching the Appendix A schema into
`backend/app/data/real_timetable.csv` — no other code changes required
(`ingest.py` consumes it as-is).

All maintenance-defect data (TMS/SMMS/TDMS requests) is synthetic, generated
by `generate_synthetic_data.py`, weighted by each section's real derived
daily train frequency so busier/real corridors realistically accumulate more
defects — explainable to judges in one sentence: *"realistic synthetic data
anchored to real Indian Railways timetable structure."*

## Troubleshooting

- **`pip install` fails building `pydantic-core` / ortools** — you're
  likely on a Python version newer than what OR-Tools/pydantic-core ship
  prebuilt wheels for yet (e.g. 3.14). Use Python 3.10–3.13 instead
  (`py -0p` on Windows lists installed interpreters;
  `py -3.10 -m venv venv`).
- **Dashboard shows a spinner forever** — check the backend is running on
  port 8000 and `frontend/.env`'s `VITE_API_BASE_URL` points at it.
- **CORS errors in the browser console** — the backend allows all origins
  in `main.py` for this prototype; make sure you're hitting the FastAPI
  process, not a stale cached one.
