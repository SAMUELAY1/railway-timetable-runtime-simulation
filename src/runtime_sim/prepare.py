"""Stage 3: turn station calls into section run times (planned vs actual)."""
import pandas as pd

from runtime_sim import config
from runtime_sim.fetch import HSP_DIR

def to_minutes(hhmm):
    """Convert 'HHMM' text (e.g. '2320') to minutes since midnight (1400). Missing stays missing."""
    if pd.isna(hhmm):
        return float("nan")
    hhmm = str(hhmm).zfill(4)
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def minutes_between(start, end):
    """Minutes from start to end, adding a day when a train crosses midnight."""
    diff = end - start
    return diff.where(diff > -720, diff + 1440)

TIME_COLS = ["sched_arr", "sched_dep", "actual_arr", "actual_dep"]

def load_calls():
    """Load station calls and add a minutes-since-midnight column for each time."""
    calls = pd.read_csv(HSP_DIR / "station_calls.csv", dtype=str)
    calls["seq"] = calls["seq"].astype(int)
    for col in TIME_COLS:
        calls[col + "_min"] = calls[col].map(to_minutes)
    return calls

def add_best_times(calls):
    """Pick the time each train left / reached each station, using a fallback where one is missing."""
    calls["sched_leave"] = calls["sched_dep_min"].fillna(calls["sched_arr_min"])
    calls["sched_reach"] = calls["sched_arr_min"].fillna(calls["sched_dep_min"])
    calls["actual_leave"] = calls["actual_dep_min"].fillna(calls["actual_arr_min"])
    calls["actual_reach"] = calls["actual_arr_min"].fillna(calls["actual_dep_min"])
    return calls

def add_dwell_times(calls):
    """Add planned and actual time standing at each station, and the dwell delay."""
    calls["planned_dwell"] = minutes_between(calls["sched_arr_min"], calls["sched_dep_min"])
    calls["actual_dwell"] = minutes_between(calls["actual_arr_min"], calls["actual_dep_min"])
    calls["dwell_delay"] = calls["actual_dwell"] - calls["planned_dwell"]
    return calls

def build_sections(calls):
    """Pair each station with the next station on the same train to make sections."""
    calls = calls.sort_values(["rid", "seq"])
    nxt = calls.groupby("rid").shift(-1)
    sections = pd.DataFrame({
        "rid": calls["rid"],
        "date": calls["date"],
        "from_loc": calls["location"],
        "to_loc": nxt["location"],
        "sched_leave": calls["sched_leave"],
        "sched_reach": nxt["sched_reach"],
        "actual_leave": calls["actual_leave"],
        "actual_reach": nxt["actual_reach"],
        "dwell_delay_at_to": nxt["dwell_delay"]
    })
    return sections.dropna(subset=["to_loc"])


def add_run_times(sections):
    """Add planned and actual run time for each section, and the delay."""
    sections["planned_run"] = minutes_between(sections["sched_leave"], sections["sched_reach"])
    sections["actual_run"] = minutes_between(sections["actual_leave"], sections["actual_reach"])
    sections["run_delay"] = sections["actual_run"] - sections["planned_run"]
    return sections

def clean_sections(sections):
    """Remove sections we can't trust, printing how many each rule removes."""
    print(f"Sections before cleaning: {len(sections):,}")

    before = len(sections)
    sections = sections.dropna(subset=["planned_run", "actual_run"])
    print(f"  Removed {before - len(sections):,} with a missing time (recording gaps)")

    before = len(sections)
    sections = sections[(sections["planned_run"] >= 0) & (sections["actual_run"] >= 0)]
    print(f"  Removed {before - len(sections):,} with an impossible negative run time")

    before = len(sections)
    sections = sections[~sections["date"].isin(config.EXCLUDE_DATES)]
    print(f"  Removed {before - len(sections):,} on excluded dates (bank holiday)")

    print(f"Sections after cleaning: {len(sections):,}")
    return sections

def is_peak(minutes):
    """True if a departure time (minutes since midnight) falls in a peak window."""
    for start, end in config.PEAK_WINDOWS:
        start_min = to_minutes(start.replace(":", ""))
        end_min = to_minutes(end.replace(":", ""))
        if start_min <= minutes <= end_min:
            return True
    return False

def add_peak_flag(sections):
    """Attach each train's departure time from London and whether it's a peak train."""
    services = pd.read_csv(HSP_DIR / "services.csv", dtype=str)
    services["dep_min"] = services["sched_dep_from"].map(to_minutes)
    services["peak"] = services["dep_min"].map(is_peak)
    return sections.merge(services[["rid", "sched_dep_from", "peak"]], on="rid", how="left")



if __name__ == "__main__":
    calls = add_dwell_times(add_best_times(load_calls()))
    sections = add_run_times(build_sections(calls))
    sections = clean_sections(sections)
    sections = add_peak_flag(sections)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = config.PROCESSED_DIR / "sections.csv"
    sections.to_csv(out, index=False)
    print(f"Saved {len(sections):,} sections to {out.name}")
    print(sections["peak"].value_counts())

