from pathlib import Path

# creating folder paths 
ROOT = Path(__file__) .resolve().parents[2]
RAW_DIR = ROOT /"data"/"raw"
PROCESSED_DIR = ROOT/"data"/"processed"
FIG_DIR = ROOT/ "outputs" / "figures"

# creating routes with 3 letter codes
FROM_CRS = "WAT" #LONDON WATERLOO
TO_CRS = "WOK"   #WOKING

# PERIOD OF STUDY
DATE_FROM = "2026-08-01"   # 3 months: enough runs per service for delay distributions, and stays within one timetable period as they change overtime
DATE_TO = "2026-10-31"
DAYS = "WEEKDAY"  #HSP

# HSP times out on wide time windows, so we request the day in 2-hour slices
TIME_WINDOWS = [
    ("0000", "0159"), ("0200", "0359"), ("0400", "0559"), ("0600", "0759"),
    ("0800", "0959"), ("1000", "1159"), ("1200", "1359"), ("1400", "1559"),
    ("1600", "1759"), ("1800", "1959"), ("2000", "2159"), ("2200", "2359"),
]

# Simulation settings
PEAK_WINDOWS = [("07:00", "09:59"), ("16:00", "18:59")]
N_SIMULATIONS = 10_000
ON_TIME_THRESHOLD_MIN = 1
