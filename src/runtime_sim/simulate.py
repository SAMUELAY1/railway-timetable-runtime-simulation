"""Stage 6: Monte Carlo simulation of all-stations journeys from Waterloo to Woking."""
import numpy as np
import pandas as pd

from runtime_sim import config


def load_stopping_sections():
    """Load sections for trains that call at every station on the route."""
    sections = pd.read_csv(config.PROCESSED_DIR / "sections.csv",
                           dtype={"rid": str, "sched_dep_from": str})
    pos = {station: i for i, station in enumerate(config.ROUTE_STATIONS)}
    sections["from_i"] = sections["from_loc"].map(pos)
    sections["to_i"] = sections["to_loc"].map(pos)

    adjacent = sections[sections["to_i"] - sections["from_i"] == 1]
    stops = adjacent.groupby("rid").size()
    all_stations = stops[stops == len(config.ROUTE_STATIONS) - 1].index
    return adjacent[adjacent["rid"].isin(all_stations)]


def build_inputs(stopping, peak):
    """Collect the real delays the simulation samples from, for peak or off-peak trains."""
    data = stopping[stopping["peak"] == peak]
    first, last = config.ROUTE_STATIONS[0], config.ROUTE_STATIONS[-1]

    start = data.loc[data["from_loc"] == first, "late_leave"].dropna().to_numpy()

    run, overrun = {}, {}
    for i in range(len(config.ROUTE_STATIONS) - 1):
        section = data[data["from_i"] == i]
        run[i] = section["run_delay"].dropna().to_numpy()
        arrived_not_early = section[section["late_reach"] >= 0]
        overrun[i] = arrived_not_early["dwell_delay_at_to"].dropna().to_numpy()

    arrive = data.pivot_table(index="rid", columns="to_i", values="late_reach")
    leave = data.pivot_table(index="rid", columns="from_i", values="late_leave")
    early_leave = {}
    for i in range(len(config.ROUTE_STATIONS) - 2):
        station = i + 1
        arrived_early = arrive[station] < 0
        early_leave[i] = leave.loc[arrived_early, station].dropna().to_numpy()

    real_finish = data.loc[data["to_loc"] == last, "late_reach"].dropna().to_numpy()
    return start, run, overrun, early_leave, real_finish


def simulate(start, run, overrun, early_leave, n, seed=42):
    """Simulate n journeys; return lateness on arrival at every station (one column per station)."""
    rng = np.random.default_rng(seed)
    lateness = rng.choice(start, size=n)
    history = []
    n_sections = len(run)
    for i in range(n_sections):
        lateness = lateness + rng.choice(run[i], size=n)
        history.append(lateness.copy())
        if i < n_sections - 1:
            leaving = lateness + rng.choice(overrun[i], size=n)
            would_leave_early = leaving < 0
            leaving[would_leave_early] = rng.choice(early_leave[i], size=would_leave_early.sum())
            lateness = leaving
    return np.column_stack(history)


if __name__ == "__main__":
    stopping = load_stopping_sections()

    for peak in [False, True]:
        start, run, overrun, early_leave, real_finish = build_inputs(stopping, peak)
        sim_all = simulate(start, run, overrun, early_leave, config.N_SIMULATIONS)
        sim = sim_all[:, -1]

        label = "Peak" if peak else "Off-peak"
        print(f"\n{label}")
        print(f"  On time at Woking:   simulated {np.mean(sim < config.ON_TIME_THRESHOLD_MIN):.1%}"
              f"   real {np.mean(real_finish < config.ON_TIME_THRESHOLD_MIN):.1%}")
        print(f"  Average lateness:    simulated {sim.mean():.2f}   real {real_finish.mean():.2f} min")
        print(f"  90th percentile:     simulated {np.percentile(sim, 90):.1f}"
              f"   real {np.percentile(real_finish, 90):.1f} min")

        data = stopping[stopping["peak"] == peak]
        real_by_station = data.groupby("to_i")["late_reach"].mean()
        print("  Station   simulated   real")
        for i in range(len(run)):
            station = config.ROUTE_STATIONS[i + 1]
            print(f"  {station:8} {sim_all[:, i].mean():9.2f} {real_by_station[i + 1]:7.2f}")