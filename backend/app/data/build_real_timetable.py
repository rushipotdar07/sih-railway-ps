"""
Builds real_timetable.csv from the REAL, public, CC0-licensed Indian
Railways dataset published by the DataMeet open-data community
(https://github.com/datameet/railways), which mirrors official
data.gov.in-sourced station/train/schedule records with no login or API
key required - unlike data.gov.in's own catalog UI (Cloudflare-gated) or
Kaggle (requires an account), this is directly fetchable.

This REPLACES the earlier hand-curated `seed_real_timetable.py` approach:
every train_number, train_name, station_code/name, and arrival/departure
time in the output is genuine, not approximated. Only a small zone/state
label per major station is supplied here (the source JSON leaves it null
for a chunk of stations, including several major ones) - that field is
purely descriptive (shown in the UI), never used in scoring or scheduling.

Output matches Appendix A of SIH26027_Build_Spec.pdf exactly, so no other
code changes anywhere else are required (ingest.py consumes it as-is).

Why filter to major stations at all, instead of using the full ~417k-row/
~5,200-train dataset?  Two reasons: (1) the resulting section graph would
be far too large to browse in a demo dashboard, and (2) most of the extra
trains are branch-line locals passing through minor halts that never
overlap with any other route, which are not interesting inputs for a
"maintenance block corridors between major junctions" system.  Restricting
to major real junctions keeps every remaining number genuine while
producing a demo-sized (~500 section) real network.

Run standalone (re-)downloads ~85MB from GitHub, takes ~1-2 minutes:
    python -m app.data.build_real_timetable
"""
import csv
import json
import os
import urllib.request
from collections import defaultdict

BASE = os.path.dirname(__file__)
OUT_PATH = os.path.join(BASE, "real_timetable.csv")

SOURCE_REPO = "https://raw.githubusercontent.com/datameet/railways/master"
STATIONS_URL = f"{SOURCE_REPO}/stations.json"
SCHEDULES_URL = f"{SOURCE_REPO}/schedules.json"

# A broad, real set of major junctions/terminals spanning every zone, so the
# resulting network has genuine variety in traffic density (some pairs are
# busy trunk routes, some lightly used) rather than one hand-picked corridor.
MAJOR_STATIONS = {
    "NDLS", "NZM", "GZB", "CNB", "ALD", "MGS", "GAYA", "DHN", "ASN", "HWH", "SDAH", "BWN",
    "PNBE", "MFP", "LKO", "JHS", "GWL", "AGC", "BPL", "ET", "NGP", "BSP", "R", "JBP",
    "CSTM", "CST", "CSMT", "DR", "KYN", "PUNE", "SUR", "GTL", "SC", "HYB", "BZA", "MAS",
    "MS", "SBC", "MYS", "CBE", "ERS", "TVC", "BCT", "BRC", "RTM", "KOTA", "ADI", "ST",
    "UDZ", "JP", "JU", "BKN", "ASR", "LDH", "UMB", "CDG", "JAT", "GHY", "NJP", "DBRG",
    "BBS", "PURI", "VSKP", "TATA", "ROU", "CTC", "UBL", "MAQ", "MAO", "PNVL", "KOP",
    "NZB", "AWB", "AMI", "DDU", "MB", "BE", "ALJN", "TDL", "FZR", "PTK",
}

# The source JSON leaves zone/state null for a chunk of stations - including
# several majors. This fills exactly those gaps with real, well-known zone /
# state assignments; anywhere the source JSON *does* have a value, that value
# is used instead (see load_station_meta below).
ZONE_STATE_OVERRIDE = {
    "NDLS": ("NR", "Delhi"), "NZM": ("NR", "Delhi"), "GZB": ("NR", "Uttar Pradesh"),
    "CNB": ("NCR", "Uttar Pradesh"), "ALD": ("NCR", "Uttar Pradesh"), "MGS": ("ECR", "Uttar Pradesh"),
    "DDU": ("ECR", "Uttar Pradesh"), "GAYA": ("ECR", "Bihar"), "DHN": ("ECR", "Jharkhand"),
    "ASN": ("ER", "West Bengal"), "HWH": ("ER", "West Bengal"), "SDAH": ("ER", "West Bengal"),
    "BWN": ("ER", "West Bengal"), "PNBE": ("ECR", "Bihar"), "MFP": ("ECR", "Bihar"),
    "LKO": ("NER", "Uttar Pradesh"), "JHS": ("NCR", "Uttar Pradesh"), "GWL": ("NCR", "Madhya Pradesh"),
    "AGC": ("NCR", "Uttar Pradesh"), "BPL": ("WCR", "Madhya Pradesh"), "ET": ("WCR", "Madhya Pradesh"),
    "NGP": ("SECR", "Maharashtra"), "BSP": ("SECR", "Chhattisgarh"), "R": ("SECR", "Chhattisgarh"),
    "JBP": ("WCR", "Madhya Pradesh"), "CSTM": ("CR", "Maharashtra"), "CST": ("CR", "Maharashtra"),
    "CSMT": ("CR", "Maharashtra"), "DR": ("CR", "Maharashtra"), "KYN": ("CR", "Maharashtra"),
    "PUNE": ("CR", "Maharashtra"), "SUR": ("CR", "Maharashtra"), "GTL": ("SCR", "Andhra Pradesh"),
    "SC": ("SCR", "Telangana"), "HYB": ("SCR", "Telangana"), "BZA": ("SCR", "Andhra Pradesh"),
    "MAS": ("SR", "Tamil Nadu"), "MS": ("SR", "Tamil Nadu"), "SBC": ("SWR", "Karnataka"),
    "MYS": ("SWR", "Karnataka"), "CBE": ("SR", "Tamil Nadu"), "ERS": ("SR", "Kerala"),
    "TVC": ("SR", "Kerala"), "BCT": ("WR", "Maharashtra"), "BRC": ("WR", "Gujarat"),
    "RTM": ("WR", "Madhya Pradesh"), "KOTA": ("WCR", "Rajasthan"), "ADI": ("WR", "Gujarat"),
    "ST": ("WR", "Gujarat"), "UDZ": ("NWR", "Rajasthan"), "JP": ("NWR", "Rajasthan"),
    "JU": ("NWR", "Rajasthan"), "BKN": ("NWR", "Rajasthan"), "ASR": ("NR", "Punjab"),
    "LDH": ("NR", "Punjab"), "UMB": ("NR", "Haryana"), "CDG": ("NR", "Chandigarh"),
    "JAT": ("NR", "Jammu and Kashmir"), "GHY": ("NFR", "Assam"), "NJP": ("NFR", "West Bengal"),
    "DBRG": ("NFR", "Assam"), "BBS": ("ECoR", "Odisha"), "PURI": ("ECoR", "Odisha"),
    "VSKP": ("ECoR", "Andhra Pradesh"), "TATA": ("SER", "Jharkhand"), "ROU": ("SER", "Odisha"),
    "CTC": ("ECoR", "Odisha"), "UBL": ("SWR", "Karnataka"), "MAQ": ("SWR", "Karnataka"),
    "MAO": ("KR", "Goa"), "PNVL": ("CR", "Maharashtra"), "KOP": ("CR", "Maharashtra"),
    "NZB": ("SCR", "Telangana"), "AWB": ("SCR", "Maharashtra"), "AMI": ("CR", "Madhya Pradesh"),
    "MB": ("NR", "Uttar Pradesh"), "BE": ("NER", "Uttar Pradesh"), "ALJN": ("NCR", "Uttar Pradesh"),
    "TDL": ("NCR", "Uttar Pradesh"), "FZR": ("NR", "Punjab"), "PTK": ("NR", "Punjab"),
}


def _fetch_json(url, cache_name):
    cache_path = os.path.join(BASE, ".cache_" + cache_name)
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url) as resp:
        raw = resp.read()
    with open(cache_path, "wb") as f:
        f.write(raw)
    return json.loads(raw)


def load_station_meta():
    data = _fetch_json(STATIONS_URL, "stations.json")
    meta = {}
    for feat in data["features"]:
        p = feat["properties"]
        zone, state = ZONE_STATE_OVERRIDE.get(p["code"], (None, None))
        meta[p["code"]] = {
            "zone": p.get("zone") or zone or "NR",
            "state": p.get("state") or state or "—",
        }
    return meta


def _effective_minutes(day, hhmmss):
    if not hhmmss or hhmmss == "None":
        return None
    h, m, _s = hhmmss.split(":")
    return day * 24 * 60 + int(h) * 60 + int(m)


def main():
    station_meta = load_station_meta()
    print(f"{len(station_meta)} real stations loaded")

    schedules = _fetch_json(SCHEDULES_URL, "schedules.json")
    print(f"{len(schedules)} real stop records loaded")

    by_train = defaultdict(list)
    for r in schedules:
        if r["station_code"] in MAJOR_STATIONS:
            by_train[r["train_number"]].append(r)
    print(f"{len(by_train)} distinct real trains touch >=1 major station")

    rows = []
    kept_trains = 0
    for train_no, stops in by_train.items():
        def sort_key(r):
            t = _effective_minutes(r["day"], r["arrival"])
            if t is None:
                t = _effective_minutes(r["day"], r["departure"])
            return t if t is not None else 0

        stops_sorted = sorted(stops, key=sort_key)
        cleaned = []
        for s in stops_sorted:
            if not cleaned or cleaned[-1]["station_code"] != s["station_code"]:
                cleaned.append(s)
        if len(cleaned) < 2:
            continue
        kept_trains += 1
        for s in cleaned:
            meta = station_meta.get(s["station_code"], {"zone": "NR", "state": "—"})
            rows.append({
                "train_number": s["train_number"],
                "train_name": s["train_name"],
                "station_code": s["station_code"],
                "station_name": s["station_name"],
                "arrival": s["arrival"],
                "departure": s["departure"],
                "day": s["day"],
                "distance": "",
                "zone": meta["zone"],
                "division": meta["state"],
            })

    print(f"{kept_trains} real trains kept (>=2 stops at major stations)")
    print(f"{len(rows)} output rows")

    fieldnames = ["train_number", "train_name", "station_code", "station_name",
                  "arrival", "departure", "day", "distance", "zone", "division"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
