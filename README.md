# Seats.aero Flight Availability Notifier — Design Doc + Repo README (Single File)

---

## 1) Project goal

Build a polling-based notifier that checks award flight availability using **Seats.aero’s API**, then sends a notification when results match user-defined criteria—so the user doesn’t have to manually check.

### Current goal (Shrink MVP / v0)
- Dedicated route: **departure + arrival**
- Date: **single date or date range**
- Use **Cached Search** endpoint (summary-level results) — enough for current criteria
- Pipeline:
  - **poll → get data → paginate+dedupe → basic filter → anti-spam → notify**
- No database yet; only minimal persistent state (JSON) to avoid spam alerts

### Future goal (v1+)
- Multiple watches
- Richer criteria
- Optional trip-level detail verification via **Get Trips**
- DB-backed history/analytics
- Multi-channel notifications (SMS/Slack/etc.)
- Better scheduling and scale-up options

---

## 2) Constraints and assumptions

- Language: **Python**
- Auth: API key in header `Partner-Authorization`
- Pagination: `skip` + `cursor`
- Rare duplicates across pages possible → **dedupe by ID**
- Fields vary by program/source (seat count/taxes may be missing)

---

## 3) Design overview

### 3.1 Shrink MVP architecture (v0)

**Cached Search polling → Get Data → Pagination + Dedupe → Basic criteria filter → Cooldown/Dedupe across runs → Notify**

Why this MVP is “solid” even without a DB:
- Pagination + dedupe ensures you don’t miss results
- Minimal `state.json` prevents repeated alerts every polling run
- Modular folder structure supports future expansion

### 3.2 Future desired architecture (v1+ target)

Think in 6 pluggable modules:

1) **Watch Manager (Inputs)**
   - Stores “what I care about” rules (route/date/program + filters)
   - Data-driven watches (not code)

2) **Fetcher (Seats.aero client)**
   - Cached Search + optional Get Trips
   - Pagination (`skip` + `cursor`), retries, rate limiting
   - Optional `/routes?source=` caching for route coverage validation

3) **Normalizer**
   - Converts API responses into internal “Candidate” objects
   - Makes future enhancements easy (new endpoints/providers won’t break criteria logic)

4) **Evaluator (Rules Engine)**
   - Applies criteria (direct-only, max miles, min seats, preferred airlines, etc.)
   - Outputs “Qualified Alerts”

5) **State Store (DB)**
   - Saves raw responses (optional), normalized candidates, alert history
   - Handles dedupe and cooldown

6) **Notifier**
   - Sends Email/SMS/Slack/etc.
   - Pluggable interface for future channels

---

## 4) Shrink MVP scope (v0) — what we build first

### v0 features
- 1 watch (dedicated route + date range or single date)
- Seats.aero Cached Search polling
- Basic filters:
  - cabin available
  - direct-only (if present)
  - max miles (if present)
- Email notification (MVP)
- Pagination + dedupe
- Cooldown/dedupe across runs using a small local `state/state.json`
- Simple logging + basic retries

### v0 intentionally skipped
- Database (SQLite/Postgres)
- Routes catalog caching (`/routes`)
- Get Trips verification
- Parallelization/job queue
- UI

---

## 5) Repository folder design (v0)
Wool Radar/
  README.md
  .gitignore
  .env.example
  requirements.txt

  config/
    watch.example.yaml
    watch.yaml              # real config (gitignored)

  state/
    state.json              # runtime anti-spam state (gitignored)

  src/
    main.py                 # entrypoint / orchestration

    settings.py             # loads env + config paths

    seats_aero/
      client.py             # HTTP client: auth header, retries, request wrapper
      cached_search.py      # fetcher: calls Cached Search + pagination + dedupe

    logic/
      filter.py             # applies basic criteria to cached results
      signature.py          # builds a stable signature for anti-spam

    storage/
      state_store.py        # reads/writes state.json, cooldown logic

    notify/
      email.py              # MVP notifier (email)
      sms.py                # placeholder for future (Twilio/SNS)

  scripts/
    run_once.sh             # optional local helper