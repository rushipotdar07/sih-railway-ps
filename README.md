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

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. It talks to the backend at
`http://localhost:8000` by default (configurable via `frontend/.env`,
`VITE_API_BASE_URL`).

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

