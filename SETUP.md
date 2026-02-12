# NAV Scoring System Setup

## Important: Database Initialization

Due to CIFS mount limitations with SQLite file locking, the database initialization must be done on a local filesystem or in Docker.

### Option 1: Docker (Recommended)

The application is meant to run in Docker, which avoids filesystem locking issues:

```bash
docker build -t nav-scoring:latest .
docker run -d --name nav-scoring -p 8000:8000 -v $(pwd)/data:/app/data nav-scoring:latest
docker exec nav-scoring python3 seed.py
```

### Option 2: Local Development (Linux/Mac)

If developing locally with a proper filesystem:

```bash
# Create database with migrations
python3 bootstrap_db.py

# Seed test data
python3 seed.py

# Run app
python3 -m uvicorn app.app:app --reload
```

### Option 3: Remote Database

Configure the app to use a PostgreSQL or MySQL server instead of SQLite by updating the database connection string.

## Database Schema

The application uses SQLite with the following tables:
- `users` (NEW - unified user management)
- `airports`
- `navs`
- `checkpoints`
- `secrets`
- `pairings`
- `prenav_submissions`
- `flight_results`
- `start_gates`
- `members` (deprecated - kept for backward compatibility)
- `coach` (deprecated - kept for backward compatibility)

## New Authentication System (v0.2.0)

### User Roles
- **Competitor** (`is_coach=0, is_admin=0`): Access `/team` dashboard, can submit flights
- **Coach** (`is_coach=1, is_admin=0`): Access `/coach` dashboard (read-only)
- **Admin** (`is_admin=1`): Full CRUD access to all resources

### Self-Signup
- New users sign up at `/signup`
- Email must end with `@siu.edu`
- Account awaits admin approval (`is_approved=0` → `is_approved=1`)
- Admin can approve accounts in `/coach/members`

### Testing Credentials
After running `seed.py`:
- **Admin**: username=`admin`, password=`admin123`
- **Coach**: username=`coach`, password=`coach123`
- **Competitors**: pilot1-3, observer1-3, password=`pass123`
- **Pending**: username=`pending_user`, password=`pass123` (awaiting approval)
