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

s = make_session()
print("Session ready for:", s.auth[0])