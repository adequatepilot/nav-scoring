#!/usr/bin/env python3
"""
Bootstrap script to initialize the database cleanly.
This creates all tables without migration file complexity.
"""

import sqlite3
from pathlib import Path

def create_database():
    """Create the database schema from scratch."""
    
    db_path = Path("data/navs.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Delete existing if it exists
    if db_path.exists():
        db_path.unlink()
        print("Removed existing database")
    
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    cursor = conn.cursor()
    
    print("Creating tables...")
    
    # Airports
    cursor.execute("""
        CREATE TABLE airports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL
        )
    """)
    print("  ✓ airports")
    
    # Start Gates
    cursor.execute("""
        CREATE TABLE start_gates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            FOREIGN KEY (airport_id) REFERENCES airports(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ start_gates")
    
    # NAVs
    cursor.execute("""
        CREATE TABLE navs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            airport_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (airport_id) REFERENCES airports(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ navs")
    
    # Checkpoints
    cursor.execute("""
        CREATE TABLE checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nav_id INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ checkpoints")
    
    # Secrets
    cursor.execute("""
        CREATE TABLE secrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nav_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            type TEXT NOT NULL DEFAULT 'checkpoint',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ secrets")
    
    # Members (old table - keeping for backward compatibility)
    cursor.execute("""
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    print("  ✓ members")
    
    # Coach (old table - keeping for backward compatibility)
    cursor.execute("""
        CREATE TABLE coach (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL DEFAULT 'coach',
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_admin INTEGER DEFAULT 0
        )
    """)
    print("  ✓ coach")
    
    # Unified Users table (NEW)
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            is_coach INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0,
            email_verified INTEGER DEFAULT 0,
            must_reset_password INTEGER DEFAULT 0,
            profile_picture_path TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    print("  ✓ users")
    
    # Pairings
    cursor.execute("""
        CREATE TABLE pairings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pilot_id INTEGER NOT NULL,
            safety_observer_id INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pilot_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY (safety_observer_id) REFERENCES members(id) ON DELETE CASCADE,
            UNIQUE(pilot_id, safety_observer_id)
        )
    """)
    print("  ✓ pairings")
    
    # Pre-flight NAV submissions
    cursor.execute("""
        CREATE TABLE prenav_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pairing_id INTEGER NOT NULL,
            pilot_id INTEGER NOT NULL,
            nav_id INTEGER NOT NULL,
            leg_times TEXT NOT NULL,
            total_time REAL NOT NULL,
            fuel_estimate REAL NOT NULL,
            token TEXT UNIQUE NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (pairing_id) REFERENCES pairings(id) ON DELETE CASCADE,
            FOREIGN KEY (pilot_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ prenav_submissions")
    
    # Flight results
    cursor.execute("""
        CREATE TABLE flight_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prenav_id INTEGER NOT NULL,
            pairing_id INTEGER NOT NULL,
            nav_id INTEGER NOT NULL,
            gpx_filename TEXT NOT NULL,
            actual_fuel REAL NOT NULL,
            secrets_missed_checkpoint INTEGER DEFAULT 0,
            secrets_missed_enroute INTEGER DEFAULT 0,
            secrets_found TEXT,
            start_gate_id INTEGER,
            overall_score REAL NOT NULL,
            checkpoint_results TEXT NOT NULL,
            pdf_filename TEXT,
            scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prenav_id) REFERENCES prenav_submissions(id) ON DELETE CASCADE,
            FOREIGN KEY (pairing_id) REFERENCES pairings(id) ON DELETE CASCADE,
            FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE,
            FOREIGN KEY (start_gate_id) REFERENCES start_gates(id)
        )
    """)
    print("  ✓ flight_results")
    
    # Create indexes
    cursor.execute("CREATE INDEX idx_members_username ON members(username)")
    cursor.execute("CREATE INDEX idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX idx_users_is_coach ON users(is_coach)")
    cursor.execute("CREATE INDEX idx_users_is_admin ON users(is_admin)")
    cursor.execute("CREATE INDEX idx_users_is_approved ON users(is_approved)")
    cursor.execute("CREATE INDEX idx_pairings_pilot ON pairings(pilot_id)")
    cursor.execute("CREATE INDEX idx_pairings_observer ON pairings(safety_observer_id)")
    cursor.execute("CREATE INDEX idx_pairings_active ON pairings(is_active)")
    cursor.execute("CREATE INDEX idx_prenav_token ON prenav_submissions(token)")
    cursor.execute("CREATE INDEX idx_prenav_pairing ON prenav_submissions(pairing_id)")
    cursor.execute("CREATE INDEX idx_prenav_pilot ON prenav_submissions(pilot_id)")
    cursor.execute("CREATE INDEX idx_flight_pairing ON flight_results(pairing_id)")
    cursor.execute("CREATE INDEX idx_flight_nav ON flight_results(nav_id)")
    cursor.execute("CREATE INDEX idx_flight_date ON flight_results(scored_at)")
    cursor.execute("CREATE INDEX idx_secrets_nav ON secrets(nav_id)")
    cursor.execute("CREATE INDEX idx_checkpoints_nav ON checkpoints(nav_id)")
    print("  ✓ indexes")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Database created successfully at data/navs.db")
    return True

if __name__ == '__main__':
    try:
        create_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
