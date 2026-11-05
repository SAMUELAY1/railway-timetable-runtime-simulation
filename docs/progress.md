# Project log: Timetable Run-Time Risk Simulation

A record of what I built, the decisions I made, the problems I hit and how I solved them.

---

## Project goal
Measure how often scheduled run times on a UK rail route (London Waterloo → Woking)
are actually achieved, find which sections create the most timetable risk, and test
run-time changes using a Monte Carlo simulation.

### How the project works (the big picture)
1. **Get data:** HSP API → which trains ran (RIDs) → station-by-station times for each train
2. **Prepare:** calculate planned vs actual run time for each section between stations
3. **Explore:** where and when does delay build up? Peak vs off-peak?
4. **Model:** store the real spread of delays for each section
5. **Simulate:** 10,000 random journeys built from real delays → % chance of arriving on time
6. **Insights:** riskiest sections, and "what if" tests (e.g. +1 minute on a section)
7. **Validate:** compare simulated on-time % with the real on-time %

---

## Key terms
| Term | Meaning |
|---|---|
| **HSP** | Historical Service Performance: an API with scheduled and actual times for UK trains |
| **API** | A way for my code to request data from another computer |
| **Endpoint** | A specific "counter" of the API (`serviceMetrics`, `serviceDetails`) |
| **Payload** | The "order form" I send with a request (stations, dates, times) |
| **JSON** | The text format the API replies in; becomes a Python dictionary |
| **CRS code** | 3-letter station code (WAT = Waterloo, WOK = Woking) |
| **Service** | A repeating timetable slot, e.g. "the 07:00 WAT → Portsmouth, weekdays" |
| **RID** | One specific train on one specific day. First 8 digits = date |
| **gbtt_ptd / gbtt_pta** | Public timetable departure / arrival time |
| **TOC** | Train operating company (SW = South Western Railway) |
| **Run time** | Time a train takes between two stations |
| **Dwell time** | Time a train waits at a station |
| **Monte Carlo** | Simulating something many times with random (but realistic) inputs to estimate probabilities |

---

## Stage 0: Project setup ✅

**What I did**
- Created the repo and folder structure (`src/`, `notebooks/`, `data/`, `docs/`, `tests/`, `outputs/`)
- Created a virtual environment (`.venv`) and `requirements.txt`
- Wrote `config.py` to hold all settings in one place
- Added `pyproject.toml` and installed my code as a package with `pip install -e .`

**Decisions and why**
- **Reusable code in `src/runtime_sim/`, notebooks only for exploring and charts.** Keeps logic testable and reusable.
- **`config.py`**: all settings (route, dates, paths) in one place, with paths built from the file's location so it runs on any computer.
- **Data folders ignored by Git.** The data is large and has licence terms.

**Problems and fixes**
| Problem | Cause | Fix |
|---|---|---|
| `git push` rejected | GitHub had a file my Mac didn't | `git pull --rebase origin main`, then push |
| `ModuleNotFoundError: runtime_sim` | Python didn't know my code lives in `src/` | `pyproject.toml` + `pip install -e .` |
| `.env` not found | Installed without `-e`, so Python ran a *copy* of my code from `site-packages` | Uninstalled, deleted `build/`, reinstalled with `-e` |
| Still `ModuleNotFoundError` | macOS marked the `.pth` link file as **hidden**; Python 3.12 skips hidden `.pth` files | Found it with `ls -lO`; fixed with `chflags -R nohidden .venv` |
| Problem kept coming back | Project was in Documents, synced by iCloud | Moved the project to `~/Projects` and rebuilt `.venv` |

**What I learned**
- Always activate the environment: `source .venv/bin/activate`
- "Successfully installed" doesn't mean it works: always test
- Debugging = test one assumption at a time; print what Python actually sees
  (`config.__file__`, `sys.path`)

---

## Stage 1: Data sources ✅

**Chosen**
- **HSP** (main dataset): the only free source with scheduled *and* actual times at every station
- **Network Rail Historic Delay Attribution** (later): explains *why* delays happen

**Rejected**
- Darwin / live train feeds: real-time only, no history
- Realtime Trains history: paid subscription

**Access**
- Registered on the National Rail Data Portal with HSP ticked (user type: Personal)
- Login stored in `.env`, never in code

---

## Stage 2: Data extraction (`fetch.py`) 🛠️ in progress

**Functions built**
| Function | What it does |
|---|---|
| `month_chunks()` | Splits a date range into calendar-month pieces |
| `make_session()` | Logs in once using `.env`; stops early with a clear message if details are missing |
| `post()` | Sends a request; retries up to 3 times with increasing waits (backoff) |
| `fetch_service_metrics()` | Asks HSP which trains ran between two stations in a period |
| `metrics_to_services()` | Flattens nested JSON into a table: one row per RID |
| `collect_services()` | Loops months × 2-hour windows, saves raw JSON, combines into `services.csv` |

**Decisions and why**
- **`.env` for credentials.** Keeps my password out of the code and off GitHub. `.env.example` shows others which settings are needed.
- **A session.** Log in once and reuse it for every request.
- **Retries with backoff.** The API is slow; waiting longer each time gives it a chance to recover.
- **Save raw JSON.** If I find a bug in my processing, I can reprocess without downloading again.
- **One row per RID.** Each RID is one real journey, which is what I analyse.
- **`if __name__ == "__main__":`.** Test code only runs when I run the file directly, not when it's imported.

**Timeout experiment (data-driven design)**
The API timed out on a full-week, full-day request, so I measured three request sizes:

| Request | Result |
|---|---|
| 1 day, 2 hours | ✅ 28 services in 34s |
| 1 day, 24 hours | ❌ failed after 375s |
| 5 days, 2 hours | ✅ 28 services in 25s |

**Conclusion:** wide **time windows** cause timeouts, not long date ranges.
**Change:** split each day into 12 two-hour windows (`TIME_WINDOWS` in `config.py`).

**Bugs I fixed**
| Bug | Lesson |
|---|---|
| `NameError: fetch_service_metrics not defined` | Python reads top to bottom: **define before use**. Test code goes at the bottom |
| Function wrapped in `'''` | `'''` makes a *string*, not a comment. Use **Cmd + /** to comment out code |
| `for rid` loop indented wrongly | **Indentation is logic.** One level wrong silently processed only the last service |

**Next**
- [ ] Run the one-week download with 2-hour windows and check the result
- [ ] `serviceDetails`: get station-by-station times for each RID
- [ ] Save every response to disk so downloads can resume

**One-week test of serviceMetrics (5–9 Oct 2026, 2-hour windows)**
- All 12 windows succeeded → **1,041 train runs** (~208 trains/day through WAT and WOK)
- Top destinations: Portsmouth Harbour (264), Woking (185), Alton (156), Basingstoke (139)
- Renamed `sched_dep`/`sched_arr` to `sched_dep_from`/`sched_arr_to`: these are times
  at *my* two stations, not at the train's origin/destination (a Southampton train's
  "arrival" was actually its Woking time)
- **Insight:** run times vary a lot between trains on the same route (00:09 stopping
  train = 49 min to Woking; 00:10 fast train = 30 min). Mixing them would make an
  "average journey time" meaningless, so I analyse **each section between stations**,
  comparing every train against **its own** timetable.

### serviceDetails: station-by-station times ✅
| Function | What it does |
|---|---|
| `fetch_service_details()` | Gets one train's times at every station; **caches** each reply as `details/<RID>.json` |
| `details_to_rows()` | Flattens one train into one row per station call (`seq` = calling order) |
| `collect_station_calls()` | Loops over many RIDs, prints progress every 50, saves `station_calls.csv` |

**Decisions and why**
- **Cache every reply to its own file.** Re-runs skip trains already downloaded, so a
  stopped download resumes where it left off, and fixing a parsing bug never needs a re-download.
- **0.5s pause between requests (rate limiting).** Avoids overloading the API.
- **`or None` for empty times.** HSP sends `""` when a time doesn't exist; `None` becomes
  proper missing data (`NaN`) in pandas instead of an empty string that breaks maths later.
- **`dtype=str` when reading CSVs.** Keeps RIDs and times like `"0009"` as text, so pandas
  doesn't turn them into numbers and drop leading zeros.
- **Build the DataFrame once, after the loop.** Inside the loop it would rebuild a
  growing table for every train, which gets slower and slower.

**Test (20 trains)**
- First run: **12s** (~0.6s per train). Second run: near-instant (served from cache).
- 20 trains → 360 station calls (~18 stations per train)
- Estimated full download: ~1.5 hours for 2 months, ~4.5 hours for 6 months

**What the data looks like (00:09 WAT → WOK, 6 Oct)**
- First station: **no arrival times** (the train starts there). Last station: **no departure times** (it ends there).
- Times are **whole minutes** only, so precision is about ±1 minute (a limitation to state later).
- This train arrived at Woking **2 minutes early** (00:56 vs 00:58).

**⚠️ Data quirk found: missing departures at middle stations**
- Esher → West Byfleet had **arrival times but no departure times**, even though the train kept going.
- Likely reason: on late-night trains these stops are **"set down only"** (passengers can
  get off but not on), so the public timetable shows no departure, and HSP only reports public times.
- **Impact:** my planned formula (departure from A → arrival at B) fails for these sections.
- Options for Stage 3: measure **arrival → arrival**, or use departure when present and
  arrival as a fallback.
- [ ] Check whether daytime trains have the same gap - 
 [x] Checked daytime trains: the 05:20 stopping train has departures at every middle
  station, so missing departures are specific to late-night **set-down-only** stops.

**More data findings (20 trains inspected)**
- **Pick-up-only stops:** the 00:10 to Southampton has *no arrival* at Clapham Junction and
  Wimbledon (passengers can only board). So a middle stop can have arrival only, departure only, or both.
- **Recording gaps:** the 05:05 on 8 Oct is missing several actual times (not cancelled,
  no reason code), so the equipment missed them. These sections must be dropped, not guessed.
- **Delay building:** 05:20 WAT→WOK on 6 Oct left on time but arrived **9 min late**,
  losing most time between Surbiton and Woking.
- **Delay recovering:** 05:18 to Weymouth on 6 Oct left **6 min late** and was **on time
  by Winchester**, thanks to recovery time in the timetable. So the simulation must allow
  lateness to *shrink*, not just add up.
- **Reason codes** (895, 574, 841) appear once a train is late and carry to the end of
  the journey. To look up in Stage 4.

**Decision for Stage 3: "best available time"**
- Leaving A = departure (fallback: arrival). Reaching B = arrival (fallback: departure).
- Same rule for scheduled and actual times; drop sections with missing actual times.

**Bug fixed**
| Bug | Lesson |
|---|---|
| `IndentationError: unexpected indent` | Lines at the same level need *exactly* the same spaces. Turned on "Render Whitespace" to see spaces and tabs |
| Docstring placed above `def` | A docstring only counts as the first line *inside* the function |


**Findings from services.csv (test week)**
- Trains crossing midnight (e.g. 23:20 → 00:10) → run-time maths must add 24h when arrival < departure
- Clockface timetable: same services repeat hourly → ~60 runs each over 3 months
- Fridays can have different IDs, times and destinations → compare each run to its own timetable
- Missing days (e.g. 16:30 PMH on Fri 9 Oct) → HSP excludes trains with no actual arrival,
  so cancellations are mostly invisible. Limitation: I measure lateness, not cancellations.

**Next**
- [ ] Decide the scope (how many months) and run the full download
- [ ] Stage 3: calculate planned vs actual run times for each section

## Stage 3: Data preparation (`prepare.py`) 🛠️ in progress

**Functions built**
| Function | What it does |
|---|---|
| `to_minutes()` | "HHMM" text → minutes since midnight (`"2320"` → 1400); missing stays missing |
| `minutes_between()` | End − start; adds 1440 only for big negatives (< −720) = midnight crossing |
| `load_calls()` | Loads station calls and adds a minutes column for every time |
| `add_best_times()` | Leave = departure (fallback arrival); reach = arrival (fallback departure) |
| `add_dwell_times()` | Dwell = departure − arrival at the same station (raw times only, no fallback) |
| `build_sections()` | Pairs each station with the next one on the same train (`groupby("rid").shift(-1)`) |
| `add_run_times()` | Planned run, actual run, and `run_delay` = actual − planned |

**Decisions and why**
- **Minutes since midnight:** text times can't be subtracted; numbers can.
- **Midnight rule uses −720, not < 0:** a big negative = crossed midnight (+1440);
  a small negative = data error, kept negative so it can be found and removed.
  Adding 1440 to every negative would create fake 1,438-minute run times.
- **Dwell uses raw times only:** a fallback would invent dwells that weren't measured.

**🔑 Key finding: reconciling one train by hand**
- 05:20 WAT → WOK on 6 Oct left 1 min early and arrived **9 min late**.
- My first model (running time only) said the train **gained 4 minutes**, which was wrong.
- Reconciling by hand: the delay was in **station dwell times (+14 min)**, which sections excluded.
  `−1 (departure) − 4 (running) + 14 (dwell) = +9` ✅
- **Change:** added dwell delays and attached each one to the section arriving at that station.
- **Lesson:** always reconcile a calculation against a hand-worked example before scaling it up.

**Limitation found**
- Public timetables round short stops to **0 minutes**, so any real stop (~30s) shows as
  at least +1 min dwell delay. True allowances are slightly bigger than the data shows.

**Full run: data quality report (Aug–Oct 2026)**
| Step | Sections | % |
|---|---|---|
| Before cleaning | 168,618 | 100% |
| Recording gaps (missing actual times) | −6,265 | 3.7% |
| Impossible negative run times | −2 | 0.001% |
| Bank holiday (31 Aug) | −2,703 | 1.6% |
| **Kept** | **159,648** | **94.7%** |

- Peak: 51,825 sections (32%); off-peak: 107,823 (68%). Peak covers 25% of the day
  but holds 32% of sections because more trains run then. ✅ Sanity check passed.
- Only 2 negatives: confirms HSP actuals are reliable and the −720 midnight rule was right.

**Outlier found and fixed**
- `describe()` showed a max actual run time of **1,392 min (23 hours)**: impossible.
- Cause: times either side of midnight in the *other* direction (leave just after
  midnight, reach just before) gave a big **positive** difference.
- Fix: `minutes_between` now also subtracts 1440 when the difference is > 720. The broken
  row became negative and was removed by the existing cleaning rule (negatives: 2 → 3).
- Lesson: always check min/max. Impossible values reveal bugs that averages hide.


---

## Interview stories
1. **Timeout problem:** "The API timed out on large requests. I ran a controlled experiment
   to find the cause (wide time windows) and redesigned the extraction around 2-hour slices."
2. **Hidden file bug:** "My package wasn't being found. I printed the module path and
   Python's search path, and traced it to macOS hiding the `.pth` file, which Python 3.12 skips."
3. **Silent indentation bug:** "A loop at the wrong level would have quietly kept only the
   last service, with no error. That taught me to check row counts, not just whether code runs."
 4. **Checking the data, not just the code:** "Before calculating run times, I inspected one
   train station by station and found middle stops with no departure times (set-down-only
   stops on late trains). My planned formula would have silently failed there, so I
   designed the calculation to handle it."
   5. **Reconciliation:** "My section model said a train gained 4 minutes, but it arrived 9 minutes
   late. Reconciling by hand showed the delay was in station dwell times, which my sections
   excluded, so I added dwell delays. The totals then matched exactly."

