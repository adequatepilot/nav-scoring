# NAV Scoring Phase 1 - Foundation Summary

## What I've Built (Foundation Layer)

### 1. Database Schema (`migrations/001_initial_schema.sql`)

**Tables Created:**
- `airports` — Airport codes (KMDH, KOSH, KCPS)
- `start_gates` — Departure points per airport
- `navs` — Navigation routes
- `checkpoints` — Landmarks in each NAV
- `secrets` — Secrets per NAV (lat/lon, type: checkpoint|enroute) — for Phase 2
- `teams` — Team user accounts (username, password_hash, email, team_name)
- `coach` — Separate coach admin account
- `prenav_submissions` — Pre-flight planning data (leg times, fuel estimate, token)
- `flight_results` — Scored flight data (GPX, actual fuel, secrets, score, PDF filename)

**All tables properly indexed and foreign-keyed for performance.**

---

### 2. Pydantic Models (`app/models.py`)

**Authentication:**
- `TeamCreate` — Register a team
- `TeamLogin` — Team login form
- `CoachLogin` — Coach login form
- `TeamResponse` — Team data response

**NAV/Navigation:**
- `AirportResponse`, `StartGateResponse`, `CheckpointResponse`
- `NavResponse` — Full NAV with all checkpoints
- `SecretResponse` — Secret object (with type: checkpoint|enroute)

**Flight Data:**
- `PreNavCreate` — Pre-flight form submission
- `PreNavResponse` — Submitted pre-nav with token + expiry
- `FlightCreate` — Post-flight form submission
- `FlightResultResponse` — Scored result with all metrics

**Response Wrappers:**
- `SuccessResponse`, `ErrorResponse` — Standard API responses

---

### 3. Scoring Engine (`app/scoring_engine.py`)

**Pure functions extracted from nav.py:**
- `haversine_distance()` — Distance calculation
- `calculate_bearing()` — True bearing between points
- `side_of_plane()` — Perpendicular plane crossing detection
- `interpolate_point()` — Linear interpolation for CTP
- `detect_start_gate_crossing()` — Identify takeoff point
- `find_checkpoint_crossing()` — Three methods (CTP, Radius Entry, PCA)
- `calculate_leg_score()` — Timing + off-course penalties per config
- `calculate_fuel_penalty()` — Fuel burn error penalty per config
- `calculate_secrets_penalty()` — Checkpoint & enroute secret penalties
- `calculate_overall_score()` — Sum all penalties

**Key change from nav.py:**
- All configuration-based scoring (no hardcoded thresholds)
- All functions are pure (no database, no logging in the math)
- Config passed in, allowing runtime rule changes

---

### 4. Database Layer (`app/database.py`)

**SQLite wrapper with context managers:**

**Team Management:**
- `create_team()`, `get_team_by_username()`, `get_team_by_id()`
- `list_teams()`, `update_team()`, `delete_team()`
- `bulk_create_teams()` — For CSV imports
- `update_team_last_login()`

**Coach Management:**
- `init_coach()`, `get_coach()`, `update_coach_password()`
- `update_coach_last_login()`

**NAV Management:**
- `get_nav()`, `list_navs()`, `list_navs_by_airport()`
- `get_checkpoints()`, `get_start_gates()`, `get_start_gate()`

**Secrets Management:**
- `get_secrets()`, `create_secret()`, `delete_secret()`

**Pre-NAV Submissions:**
- `create_prenav()`, `get_prenav_by_token()`, `get_prenav()`
- `delete_expired_prenavs()` — Auto-cleanup of 48-hour-old tokens

**Flight Results:**
- `create_flight_result()`, `get_flight_result()`
- `list_flight_results()` — With filtering by team, NAV, date range
- `delete_flight_result()`

**Auto-JSON serialization** for complex fields (leg_times, checkpoint_results)

---

### 5. Authentication Layer (`app/auth.py`)

**Team Auth:**
- `team_register()` — Create team account
- `team_login()` — Verify credentials
- `team_set_password()` — Coach-initiated password setup
- `team_change_password()` — Team-initiated password change

**Coach Auth:**
- `coach_init()` — One-time setup
- `coach_login()` — Verify coach credentials
- `coach_change_password()` — Coach password change
- `coach_reset_team_password()` — Coach resets a team's password

**Utilities:**
- `hash_password()`, `verify_password()` — bcrypt hashing (passlib)
- `generate_token()` — Secure random tokens for pre-nav submissions
- `create_session_token()` — Session management

---

## Architecture Decisions Made

1. **Separate coach account** — Not in teams table, isolated password
2. **Token-based pre-nav** — 48-hour expiry, auto-cleanup
3. **Config-driven scoring** — No hardcoded thresholds, all from config.yaml
4. **Pure scoring engine** — No database/IO in math, testable independently
5. **JSON storage** — Complex data (leg_times, results) stored as JSON in SQLite
6. **Auto-migrations** — Schema applied on first DB init
7. **Context managers** — All database access via `with get_connection()` for safety

---

## What's Next (FastAPI Layer)

Once you approve this foundation, I'll build:

1. **`app.py`** — FastAPI application
   - Session middleware (cookie-based)
   - Route groups: `/` (auth), `/team/` (team forms), `/coach/` (admin dashboard)

2. **Templates** — HTML forms
   - `team/login.html`, `team/prenav.html`, `team/flight.html`, `team/results.html`
   - `coach/login.html`, `coach/dashboard.html`, `coach/teams.html`, `coach/config.html`, `coach/results.html`

3. **Email Integration** — Zoho SMTP
   - Results notification email (team + coach)
   - Pre-nav confirmation email

4. **GPX Processing** — Full pipeline
   - Validate GPX
   - Extract track points with speeds
   - Run scoring engine
   - Generate PDF with plots
   - Store results

5. **Docker Setup**
   - `Dockerfile` + `requirements.txt`
   - `docker-compose.yml` for Unraid
   - Volume mounts for persistence

---

## Questions Before I Continue

1. **Database location:** Should I hardcode to `data/navs.db` (relative to project), or make it configurable?

2. **Config file:** Should config.yaml be:
   - In project root?
   - In data/ folder?
   - Somewhere else?

3. **GPX uploads:** Should uploaded GPX files be:
   - Stored permanently (for archiving)?
   - Deleted after scoring?

4. **PDF storage:** Should PDFs be:
   - Stored on disk + filename referenced in DB?
   - Generated on-demand?

5. **Session timeout:** How long should team/coach sessions last before re-login? (default: 24 hours?)

6. **Team creation:** Should coach dashboard have a form to create teams one-by-one, or primarily bulk CSV?

Any changes to the foundation before I build the API layer?

---

## Files Created

- `migrations/001_initial_schema.sql` — Database schema
- `app/models.py` — 400 lines, Pydantic models
- `app/scoring_engine.py` — 350 lines, pure scoring logic
- `app/database.py` — 500 lines, SQLite wrapper
- `app/auth.py` — 250 lines, authentication

**Total: ~1500 lines of clean, testable foundation code.**

Ready to proceed? 🚀
