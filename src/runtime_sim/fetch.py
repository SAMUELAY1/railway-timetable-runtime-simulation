"""Stage 2: download Historical Service Performance (HSP) data."""
import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

from runtime_sim import config

 # Historical Service Performance (HSP) data.
from datetime import date, timedelta

def month_chunks(date_from, date_to):

    # Split a date range into calendar-month pieces.
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)

    chunks = []
    while start <= end:
        next_month = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
        chunk_end = min(next_month - timedelta(days=1), end)
        chunks.append((start.isoformat(), chunk_end.isoformat()))
        start = next_month
    return chunks

# print(month_chunks("2026-05-15", "2026-07-03")) 

BASE_URL = "https://hsp-prod.rockshore.net/api/v1"

def make_session():
    # Create a logged-in connection to the HSP API using details from .env.
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

'''s = make_session()
print("Session ready for:", s.auth[0])'''

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

session = make_session()
result = fetch_service_metrics(session, "2026-10-01", "2026-10-01", "0700", "0900")
services = result.get("Services", [])
print("Trains found:", len(services))
if services:
    print(services[0])
