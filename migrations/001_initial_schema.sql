-- Initial schema migration for NAV Scoring system

-- Airports (from existing navs.db)
CREATE TABLE IF NOT EXISTS airports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL
);

-- Start Gates (departure points per airport)
CREATE TABLE IF NOT EXISTS start_gates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    airport_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    FOREIGN KEY (airport_id) REFERENCES airports(id) ON DELETE CASCADE
);

-- NAV routes
CREATE TABLE IF NOT EXISTS navs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    airport_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (airport_id) REFERENCES airports(id) ON DELETE CASCADE
);

-- Checkpoints (landmarks within NAVs)
CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nav_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE
);

-- Secrets (checkpoint/enroute secrets for Phase 2)
CREATE TABLE IF NOT EXISTS secrets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nav_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    type TEXT NOT NULL DEFAULT 'checkpoint',  -- 'checkpoint' or 'enroute'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE
);

-- Members (individual users)
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,  -- Full name of member
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active INTEGER DEFAULT 1  -- 0 = disabled/moved on, 1 = active
);

-- Coach account
CREATE TABLE IF NOT EXISTS coach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL DEFAULT 'coach',
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Team Pairings (pilot + safety observer)
CREATE TABLE IF NOT EXISTS pairings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pilot_id INTEGER NOT NULL,
    safety_observer_id INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pilot_id) REFERENCES members(id) ON DELETE CASCADE,
    FOREIGN KEY (safety_observer_id) REFERENCES members(id) ON DELETE CASCADE,
    UNIQUE(pilot_id, safety_observer_id)
);

-- Pre-flight NAV submissions (submitted by pilot of a pairing)
CREATE TABLE IF NOT EXISTS prenav_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pairing_id INTEGER NOT NULL,
    pilot_id INTEGER NOT NULL,  -- Pilot who submitted (for audit/verify)
    nav_id INTEGER NOT NULL,
    leg_times TEXT NOT NULL,  -- JSON array: [900, 1200, 800, ...]
    total_time REAL NOT NULL,  -- seconds
    fuel_estimate REAL NOT NULL,  -- gallons
    token TEXT UNIQUE NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (pairing_id) REFERENCES pairings(id) ON DELETE CASCADE,
    FOREIGN KEY (pilot_id) REFERENCES members(id) ON DELETE CASCADE,
    FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE
);

-- Flight results (scored flight for a pairing)
CREATE TABLE IF NOT EXISTS flight_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prenav_id INTEGER NOT NULL,
    pairing_id INTEGER NOT NULL,
    nav_id INTEGER NOT NULL,
    gpx_filename TEXT NOT NULL,
    actual_fuel REAL NOT NULL,  -- gallons
    secrets_missed_checkpoint INTEGER DEFAULT 0,
    secrets_missed_enroute INTEGER DEFAULT 0,
    secrets_found TEXT,  -- JSON: [{secret_id, lat, lon, timestamp}, ...]
    start_gate_id INTEGER,
    overall_score REAL NOT NULL,
    checkpoint_results TEXT NOT NULL,  -- JSON: detailed results per checkpoint
    pdf_filename TEXT,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prenav_id) REFERENCES prenav_submissions(id) ON DELETE CASCADE,
    FOREIGN KEY (pairing_id) REFERENCES pairings(id) ON DELETE CASCADE,
    FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE,
    FOREIGN KEY (start_gate_id) REFERENCES start_gates(id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_members_username ON members(username);
CREATE INDEX IF NOT EXISTS idx_pairings_pilot ON pairings(pilot_id);
CREATE INDEX IF NOT EXISTS idx_pairings_observer ON pairings(safety_observer_id);
CREATE INDEX IF NOT EXISTS idx_pairings_active ON pairings(is_active);
CREATE INDEX IF NOT EXISTS idx_prenav_token ON prenav_submissions(token);
CREATE INDEX IF NOT EXISTS idx_prenav_pairing ON prenav_submissions(pairing_id);
CREATE INDEX IF NOT EXISTS idx_prenav_pilot ON prenav_submissions(pilot_id);
CREATE INDEX IF NOT EXISTS idx_flight_pairing ON flight_results(pairing_id);
CREATE INDEX IF NOT EXISTS idx_flight_nav ON flight_results(nav_id);
CREATE INDEX IF NOT EXISTS idx_flight_date ON flight_results(scored_at);
CREATE INDEX IF NOT EXISTS idx_secrets_nav ON secrets(nav_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_nav ON checkpoints(nav_id);
