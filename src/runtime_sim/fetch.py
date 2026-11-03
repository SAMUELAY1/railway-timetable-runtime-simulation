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

print(month_chunks("2026-05-15", "2026-07-03"))