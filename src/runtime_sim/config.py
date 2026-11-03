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
DATE_FROM = "2026-05-01"
DATE_TO = "2026-10-31"
DAYS = "WEEKDAY"  #HSP

# Simulation settings
PEAK_WINDOWS = [("07:00", "09:59"), ("16:00", "18:59")]
N_SIMULATIONS = 10_000
ON_TIME_THRESHOLD_MIN = 1
