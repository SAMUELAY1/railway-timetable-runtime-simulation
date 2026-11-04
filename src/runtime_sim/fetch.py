""" download Historical Service Performance (HSP) data."""
import json
import os
import time
from datetime import date, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

from runtime_sim import config

def month_chunks(date_from, date_to):

    ''' Split a date range into calendar-month pieces.'''
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)

    chunks = []
    while start <= end:
        next_month = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
        chunk_end = min(next_month - timedelta(days=1), end)
        chunks.append((start.isoformat(), chunk_end.isoformat()))
        start = next_month
    return chunks

BASE_URL = "https://hsp-prod.rockshore.net/api/v1"


def make_session():
    """Create a logged-in connection to the HSP API using details from .env."""
    load_dotenv(config.ROOT / ".env")
    email = os.getenv("HSP_EMAIL")
    password = os.getenv("HSP_PASSWORD")

    if not email or not password:
        raise SystemExit("Missing HSP_EMAIL or HSP_PASSWORD. Fill in your .env file.")
    
    # creating the reusable connection
    session = requests.Session()
    session.auth = (email, password)
    session.headers["Content-Type"] = "application/json"
    return session

def post(session, endpoint, payload, retries=3):
    """Send a POST request to HSP and return the JSON reply, retrying if it fails."""
    url = f"{BASE_URL}/{endpoint}"

    for attempt in range(1, retries + 1):
        try:
            response = session.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as err:
            if attempt == retries:
                raise
            wait = 5 * attempt
            print(f"  Attempt {attempt} failed ({err}). Retrying in {wait}s...")
            time.sleep(wait)

def fetch_service_metrics(session, from_date, to_date, from_time="0000", to_time="2359"):
    """Ask HSP which trains ran on our route between two dates."""
    payload = {
        "from_loc": config.FROM_CRS,
        "to_loc": config.TO_CRS,
        "from_time": from_time,
        "to_time": to_time,
        "from_date": from_date,
        "to_date": to_date,
        "days": config.DAYS,
    }
    return post(session, "serviceMetrics", payload)

def metrics_to_services(metrics):
    """Flatten a serviceMetrics reply into a table with one row per train run (RID)."""
    rows = []
    for service in metrics.get("Services", []):
        attrs = service["serviceAttributesMetrics"]

        for rid in attrs.get("rids", []):
            rows.append({
                "rid": rid,
                "origin": attrs.get("origin_location"),
                "destination": attrs.get("destination_location"),
                "sched_dep_from": attrs.get("gbtt_ptd"),
                "sched_arr_to": attrs.get("gbtt_pta"),
                "toc": attrs.get("toc_code"),
            })
    return pd.DataFrame(rows)


HSP_DIR = config.RAW_DIR / "hsp"
DETAILS_DIR = HSP_DIR / "details"


def collect_services(session, date_from, date_to):
    """Fetch serviceMetrics in month x 2-hour chunks and combine into one table of train runs."""
    HSP_DIR.mkdir(parents=True, exist_ok=True)
    tables = []

    for start, end in month_chunks(date_from, date_to):
        for t1, t2 in config.TIME_WINDOWS:
            print(f"Fetching trains {start} to {end}, {t1}-{t2}...")
            metrics = fetch_service_metrics(session, start, end, t1, t2)
            (HSP_DIR / f"metrics_{start}_{t1}.json").write_text(json.dumps(metrics))
            tables.append(metrics_to_services(metrics))

    services = pd.concat(tables, ignore_index=True).drop_duplicates("rid")
    services.to_csv(HSP_DIR / "services.csv", index=False)
    print(f"Saved {len(services):,} train runs")
    return services

def fetch_service_details(session, rid):
    """Get station-by-station times for one train, using a saved copy if we have one."""
    cache_file = DETAILS_DIR / f"{rid}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    
    details = post(session, "serviceDetails", {"rid": rid})
    cache_file.write_text(json.dumps(details))
    time.sleep(0.5)
    return details


def details_to_rows(details):
    """Flatten a serviceDetails reply into one row per station call."""
    info = details.get("serviceAttributesDetails", {})
    rows = []
    for seq, loc in enumerate(info.get("locations", [])):
        rows.append({
            "rid": info.get("rid"),
            "date": info.get("date_of_service"),
            "seq": seq,
            "location": loc.get("location"),
            "sched_arr": loc.get("gbtt_pta") or None,
            "sched_dep": loc.get("gbtt_ptd") or None,
            "actual_arr": loc.get("actual_ta") or None,
            "actual_dep": loc.get("actual_td") or None,
            "late_canc_reason": loc.get("late_canc_reason") or None,
        })
    return rows

def collect_station_calls(session, rids):
    """Fetch details for many trains and save one combined table of station calls."""
    DETAILS_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for n, rid in enumerate(rids, start=1):
        details = fetch_service_details(session, rid)
        all_rows.extend(details_to_rows(details))
        if n % 50 == 0 or n == len(rids):
            print(f"  {n:,}/{len(rids):,} trains done")

    calls = pd.DataFrame(all_rows)
    calls.to_csv(HSP_DIR / "station_calls.csv", index=False)
    print(f"Saved {len(calls):,} station calls")
    return calls

if __name__ == "__main__":
    session = make_session()
    services = pd.read_csv(HSP_DIR / "services.csv", dtype=str)
    rids = services["rid"].head(20).tolist()

    start = time.time()
    calls = collect_station_calls(session, rids)
    print(f"Took {time.time() - start:.0f}s for {len(rids)} trains")
    print(calls.head(15))

    