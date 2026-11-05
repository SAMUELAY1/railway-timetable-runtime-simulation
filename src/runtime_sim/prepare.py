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



if __name__ == "__main__":
    calls = add_dwell_times(add_best_times(load_calls()))
    sections = add_run_times(build_sections(calls))
    one_train = sections[sections["rid"] == "202610067681365"]
    print(one_train[["from_loc", "to_loc", "run_delay", "dwell_delay_at_to"]])
    print("Running delay:", one_train["run_delay"].sum())
    print("Dwell delay:  ", one_train["dwell_delay_at_to"].sum())