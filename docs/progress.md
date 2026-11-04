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

---

## Interview stories
1. **Timeout problem:** "The API timed out on large requests. I ran a controlled experiment
   to find the cause (wide time windows) and redesigned the extraction around 2-hour slices."
2. **Hidden file bug:** "My package wasn't being found. I printed the module path and
   Python's search path, and traced it to macOS hiding the `.pth` file, which Python 3.12 skips."
3. **Silent indentation bug:** "A loop at the wrong level would have quietly kept only the
   last service, with no error. That taught me to check row counts, not just whether code runs."