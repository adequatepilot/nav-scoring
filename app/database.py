"""
Database wrapper supporting both SQLite (dev) and PostgreSQL (prod).
Based on DATABASE_URL environment variable.
"""

import os
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Try to import psycopg2, but it's optional
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class Database:
    _migration_lock = threading.Lock()  # Class-level lock for thread-safe migrations
    
    def __init__(self, db_path: str = "data/navs.db"):
        """Initialize database connection (SQLite or PostgreSQL)."""
        self.db_url = os.getenv('DATABASE_URL')
        self.db_path = Path(db_path)
        self._initialized = False
        
        if self.db_url:
            if not PSYCOPG2_AVAILABLE:
                raise ImportError("PostgreSQL mode requires psycopg2-binary. Install with: pip install psycopg2-binary")
            self.db_type = 'postgres'
            logger.info(f"Database mode: PostgreSQL")
        else:
            self.db_type = 'sqlite'
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database mode: SQLite at {self.db_path}")

    def initialize(self):
        """
        Initialize database (run migrations if needed).
        MUST be called at app startup before handling any requests.
        Thread-safe and idempotent.
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        logger.info("Initializing database...")
        self._init_db()
        self._initialized = True
        logger.info("Database initialization complete")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        # Initialization MUST happen at app startup via db.initialize()
        # Fail fast if database not initialized
        if not self._initialized:
            raise RuntimeError(
                "Database not initialized. Call db.initialize() at app startup before handling requests."
            )
        
        if self.db_type == 'postgres':
            conn = psycopg2.connect(self.db_url)
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                conn.close()
        else:
            # SQLite mode
            conn = sqlite3.connect(str(self.db_path), timeout=300.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                conn.close()

    def _init_db(self):
        """Initialize database (for SQLite, just log if needed)."""
        if self.db_type == 'sqlite':
            try:
                if self.db_path.exists():
                    self._run_migrations()
                else:
                    logger.warning(
                        f"Database file does not exist at {self.db_path}. "
                        "Run: python3 bootstrap_db.py to create it."
                    )
            except Exception as e:
                logger.warning(f"Could not initialize database: {e}")

    def _run_migrations(self):
        """Run any pending migrations (SQLite only). THREAD-SAFE."""
        if self.db_type != 'sqlite':
            return
        
        # Acquire lock to prevent concurrent migrations
        with self._migration_lock:
            logger.info("Acquiring migration lock...")
            
            migrations_dir = Path(__file__).parent.parent / "migrations"
            migration_files = sorted([f for f in migrations_dir.glob("*.sql") if f.name != "001_initial_schema.sql"])
            
            if not migration_files:
                logger.info("No migrations to run")
                return
            
            logger.info(f"Running {len(migration_files)} migrations...")
            
            conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
            try:
                for migration_file in migration_files:
                    with open(migration_file, "r") as f:
                        sql = f.read()
                    
                    lines = []
                    for line in sql.split('\n'):
                        if not line.strip().startswith('--'):
                            lines.append(line)
                    
                    statements = '\n'.join(lines).split(';')
                    
                    for statement in statements:
                        statement = statement.strip()
                        if statement:
                            try:
                                conn.execute(statement)
                                logger.debug(f"Executed migration: {migration_file.name}")
                            except sqlite3.OperationalError as e:
                                if "already exists" in str(e) or "duplicate column" in str(e):
                                    logger.debug(f"Skipped (already applied): {migration_file.name}")
                                else:
                                    logger.error(f"Migration error in {migration_file.name}: {e}")
                    
                conn.commit()
                logger.info("Migrations completed successfully")
            finally:
                conn.close()

    def _execute_query(self, conn, query: str, params: tuple = None):
        """Execute a query with proper parameter handling for both DBs."""
        if self.db_type == 'postgres':
            # For PostgreSQL, use cursor from the connection
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())
            return cursor
        else:
            # For SQLite, use conn.execute
            cursor = conn.cursor() if hasattr(conn, 'cursor') else conn
            if hasattr(cursor, 'execute'):
                cursor.execute(query, params or ())
            else:
                cursor = conn.execute(query, params or ())
            return cursor

    def _insert_returning_id(self, conn, query: str, params: tuple):
        """Execute INSERT and return the ID (handles both DBs)."""
        if self.db_type == 'postgres':
            # PostgreSQL: Use RETURNING clause
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query if " RETURNING" in query else query + " RETURNING id", params)
            row = cursor.fetchone()
            cursor.close()
            return row['id'] if row else None
        else:
            # SQLite: Use lastrowid
            if hasattr(conn, 'cursor'):
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.lastrowid
            else:
                cursor = conn.execute(query, params)
                return cursor.lastrowid

    # ===== MEMBER MANAGEMENT =====

    def create_member(self, username: str, password_hash: str, email: str, name: str) -> int:
        """Create a new member account. Returns member ID."""
        with self.get_connection() as conn:
            query = """
                INSERT INTO members (username, password_hash, email, name)
                VALUES (%s, %s, %s, %s)
            """ if self.db_type == 'postgres' else """
                INSERT INTO members (username, password_hash, email, name)
                VALUES (?, ?, ?, ?)
            """
            member_id = self._insert_returning_id(conn, query, (username, password_hash, email, name))
            logger.info(f"Created member: {username} (ID: {member_id})")
            return member_id

    def get_member_by_username(self, username: str) -> Optional[Dict]:
        """Get member by username."""
        with self.get_connection() as conn:
            query = "SELECT * FROM members WHERE username = %s" if self.db_type == 'postgres' else "SELECT * FROM members WHERE username = ?"
            cursor = self._execute_query(conn, query, (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_member_by_id(self, member_id: int) -> Optional[Dict]:
        """Get member by ID."""
        with self.get_connection() as conn:
            query = "SELECT * FROM members WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM members WHERE id = ?"
            cursor = self._execute_query(conn, query, (member_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_members(self) -> List[Dict]:
        """List all members."""
        with self.get_connection() as conn:
            query = "SELECT * FROM members ORDER BY name"
            cursor = self._execute_query(conn, query)
            return [dict(row) for row in cursor.fetchall()]

    def list_active_members(self) -> List[Dict]:
        """List active members only."""
        with self.get_connection() as conn:
            if self.db_type == 'postgres':
                query = "SELECT * FROM members WHERE is_active = true ORDER BY name"
            else:
                query = "SELECT * FROM members WHERE is_active = 1 ORDER BY name"
            cursor = self._execute_query(conn, query)
            return [dict(row) for row in cursor.fetchall()]

    def update_member(self, member_id: int, **kwargs) -> bool:
        """Update member fields. Returns success."""
        allowed_fields = {"password_hash", "email", "name", "is_active"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        if self.db_type == 'postgres':
            set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
            query = f"UPDATE members SET {set_clause} WHERE id = %s"
        else:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            query = f"UPDATE members SET {set_clause} WHERE id = ?"
        
        values = list(updates.values()) + [member_id]
        with self.get_connection() as conn:
            cursor = self._execute_query(conn, query, tuple(values))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def update_member_last_login(self, member_id: int) -> bool:
        """Update last login timestamp."""
        with self.get_connection() as conn:
            if self.db_type == 'postgres':
                query = "UPDATE members SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
            else:
                query = "UPDATE members SET last_login = CURRENT_TIMESTAMP WHERE id = ?"
            cursor = self._execute_query(conn, query, (member_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def delete_member(self, member_id: int) -> bool:
        """Delete a member."""
        with self.get_connection() as conn:
            query = "DELETE FROM members WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM members WHERE id = ?"
            cursor = self._execute_query(conn, query, (member_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def bulk_create_members(self, members: List[Tuple[str, str, str]]) -> int:
        """Bulk create members. Input: [(username, email, name), ...]"""
        with self.get_connection() as conn:
            count = 0
            if self.db_type == 'postgres':
                query = """
                    INSERT INTO members (username, email, name, password_hash)
                    VALUES (%s, %s, %s, %s)
                """
                for u, e, n in members:
                    self._execute_query(conn, query, (u, e, n, ""))
                    count += 1
            else:
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT INTO members (username, email, name, password_hash)
                    VALUES (?, ?, ?, ?)
                    """,
                    [(u, e, n, "") for u, e, n in members],
                )
                count = cursor.rowcount
            
            logger.info(f"Bulk created {count} members")
            return count

    # ===== COACH MANAGEMENT =====

    def init_coach(self, username: str, password_hash: str, email: str) -> bool:
        """Initialize coach account."""
        with self.get_connection() as conn:
            # Check if coach exists
            check_query = "SELECT COUNT(*) as cnt FROM coach"
            cursor = self._execute_query(conn, check_query)
            row = cursor.fetchone()
            count = row['cnt'] if row else 0
            
            if count > 0:
                logger.warning("Coach account already exists")
                return False
            
            query = """
                INSERT INTO coach (username, password_hash, email) VALUES (%s, %s, %s)
            """ if self.db_type == 'postgres' else """
                INSERT INTO coach (username, password_hash, email) VALUES (?, ?, ?)
            """
            self._execute_query(conn, query, (username, password_hash, email))
            logger.info("Coach account initialized")
            return True

    def get_coach(self) -> Optional[Dict]:
        """Get coach account."""
        with self.get_connection() as conn:
            query = "SELECT * FROM coach LIMIT 1"
            cursor = self._execute_query(conn, query)
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_coach_password(self, password_hash: str) -> bool:
        """Update coach password."""
        with self.get_connection() as conn:
            query = "UPDATE coach SET password_hash = %s WHERE id = 1" if self.db_type == 'postgres' else "UPDATE coach SET password_hash = ? WHERE id = 1"
            cursor = self._execute_query(conn, query, (password_hash,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def update_coach_last_login(self) -> bool:
        """Update coach last login timestamp."""
        with self.get_connection() as conn:
            query = "UPDATE coach SET last_login = CURRENT_TIMESTAMP WHERE id = 1"
            cursor = self._execute_query(conn, query)
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def is_coach_admin(self) -> bool:
        """Check if coach is admin."""
        coach = self.get_coach()
        if not coach:
            return False
        is_admin = coach.get("is_admin", 0)
        return is_admin == 1 or is_admin == True

    def set_coach_admin(self, is_admin: bool) -> bool:
        """Set admin status for coach."""
        with self.get_connection() as conn:
            if self.db_type == 'postgres':
                query = "UPDATE coach SET is_admin = %s WHERE id = 1"
                value = True if is_admin else False
            else:
                query = "UPDATE coach SET is_admin = ? WHERE id = 1"
                value = 1 if is_admin else 0
            cursor = self._execute_query(conn, query, (value,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    # ===== UNIFIED USER MANAGEMENT =====

    def create_user(self, username: str, password_hash: str, email: str, name: str, 
                   is_coach: bool = False, is_admin: bool = False, is_approved: bool = False,
                   email_verified: bool = False, must_reset_password: bool = False) -> int:
        """Create a new user in the unified users table. Returns user ID."""
        with self.get_connection() as conn:
            if self.db_type == 'postgres':
                query = """
                    INSERT INTO users (username, password_hash, email, name, is_coach, is_admin, is_approved, email_verified, must_reset_password)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (username, password_hash, email, name, is_coach, is_admin, is_approved, email_verified, must_reset_password)
            else:
                query = """
                    INSERT INTO users (username, password_hash, email, name, is_coach, is_admin, is_approved, email_verified, must_reset_password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (username, password_hash, email, name, 
                         1 if is_coach else 0, 1 if is_admin else 0, 
                         1 if is_approved else 0, 1 if email_verified else 0, 1 if must_reset_password else 0)
            
            user_id = self._insert_returning_id(conn, query, params)
            logger.info(f"Created user: {email} (ID: {user_id}, coach={is_coach}, admin={is_admin})")
            return user_id

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username from unified users table."""
        with self.get_connection() as conn:
            query = "SELECT * FROM users WHERE username = %s" if self.db_type == 'postgres' else "SELECT * FROM users WHERE username = ?"
            cursor = self._execute_query(conn, query, (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID from unified users table."""
        with self.get_connection() as conn:
            query = "SELECT * FROM users WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM users WHERE id = ?"
            cursor = self._execute_query(conn, query, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email from unified users table."""
        with self.get_connection() as conn:
            query = "SELECT * FROM users WHERE email = %s" if self.db_type == 'postgres' else "SELECT * FROM users WHERE email = ?"
            cursor = self._execute_query(conn, query, (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_users(self, filter_type: str = "all") -> List[Dict]:
        """List users with optional filtering."""
        with self.get_connection() as conn:
            if filter_type == "pending":
                if self.db_type == 'postgres':
                    query = "SELECT * FROM users WHERE is_approved = false ORDER BY created_at"
                else:
                    query = "SELECT * FROM users WHERE is_approved = 0 ORDER BY created_at"
            elif filter_type == "coaches":
                if self.db_type == 'postgres':
                    query = "SELECT * FROM users WHERE is_coach = true ORDER BY name"
                else:
                    query = "SELECT * FROM users WHERE is_coach = 1 ORDER BY name"
            elif filter_type == "admins":
                if self.db_type == 'postgres':
                    query = "SELECT * FROM users WHERE is_admin = true ORDER BY name"
                else:
                    query = "SELECT * FROM users WHERE is_admin = 1 ORDER BY name"
            elif filter_type == "approved":
                if self.db_type == 'postgres':
                    query = "SELECT * FROM users WHERE is_approved = true ORDER BY name"
                else:
                    query = "SELECT * FROM users WHERE is_approved = 1 ORDER BY name"
            else:
                query = "SELECT * FROM users ORDER BY name"
            
            cursor = self._execute_query(conn, query)
            return [dict(row) for row in cursor.fetchall()]

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields. Returns success."""
        allowed_fields = {"password_hash", "email", "name", "is_coach", "is_admin", "is_approved", "must_reset_password", "profile_picture_path"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        if self.db_type == 'postgres':
            set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
            query = f"UPDATE users SET {set_clause} WHERE id = %s"
        else:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            query = f"UPDATE users SET {set_clause} WHERE id = ?"
        
        values = list(updates.values()) + [user_id]

        with self.get_connection() as conn:
            cursor = self._execute_query(conn, query, tuple(values))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def approve_user(self, user_id: int) -> bool:
        """Approve a pending user account."""
        return self.update_user(user_id, is_approved=1 if self.db_type == 'sqlite' else True)

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        with self.get_connection() as conn:
            query = "DELETE FROM users WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM users WHERE id = ?"
            cursor = self._execute_query(conn, query, (user_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def update_user_last_login(self, user_id: int) -> bool:
        """Update last login timestamp for user."""
        with self.get_connection() as conn:
            query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s" if self.db_type == 'postgres' else "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?"
            cursor = self._execute_query(conn, query, (user_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    # ===== EMAIL VERIFICATION =====

    def create_verification_pending(self, email: str, password_hash: str, name: str, 
                                   verification_token: str) -> int:
        """Create a pending verification entry. Returns ID."""
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        with self.get_connection() as conn:
            if self.db_type == 'postgres':
                query = """
                    INSERT INTO verification_pending (email, password_hash, name, verification_token, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                """
            else:
                query = """
                    INSERT INTO verification_pending (email, password_hash, name, verification_token, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """
            
            verification_id = self._insert_returning_id(conn, query, (email, password_hash, name, verification_token, expires_at.isoformat()))
            logger.info(f"Created verification pending: {email} (ID: {verification_id})")
            return verification_id

    def get_verification_pending_by_token(self, token: str) -> Optional[Dict]:
        """Get verification pending by token."""
        with self.get_connection() as conn:
            query = "SELECT * FROM verification_pending WHERE verification_token = %s" if self.db_type == 'postgres' else "SELECT * FROM verification_pending WHERE verification_token = ?"
            cursor = self._execute_query(conn, query, (token,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_verification_pending_by_email(self, email: str) -> Optional[Dict]:
        """Get verification pending by email."""
        with self.get_connection() as conn:
            query = "SELECT * FROM verification_pending WHERE email = %s" if self.db_type == 'postgres' else "SELECT * FROM verification_pending WHERE email = ?"
            cursor = self._execute_query(conn, query, (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_verification_pending(self, verification_id: int) -> bool:
        """Delete a verification pending entry."""
        with self.get_connection() as conn:
            query = "DELETE FROM verification_pending WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM verification_pending WHERE id = ?"
            cursor = self._execute_query(conn, query, (verification_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def cleanup_expired_verification_pending(self) -> int:
        """Delete expired verification pending entries. Returns count deleted."""
        from datetime import datetime
        with self.get_connection() as conn:
            query = "DELETE FROM verification_pending WHERE expires_at < %s" if self.db_type == 'postgres' else "DELETE FROM verification_pending WHERE expires_at < ?"
            cursor = self._execute_query(conn, query, (datetime.utcnow().isoformat(),))
            count = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
            if count > 0:
                logger.info(f"Cleaned up {count} expired verification tokens")
            return count

    # ===== PAIRING MANAGEMENT =====

    def create_pairing(self, pilot_id: int, safety_observer_id: int) -> int:
        """Create a new pairing. Returns pairing ID."""
        if pilot_id == safety_observer_id:
            raise ValueError("Pilot and safety observer must be different members")
        
        existing_pilot = self.get_user_active_pairing(pilot_id)
        if existing_pilot:
            pilot_user = self.get_user_by_id(pilot_id)
            pilot_name = pilot_user["name"] if pilot_user else f"User {pilot_id}"
            raise ValueError(f"Cannot create pairing: {pilot_name} is already in an active pairing")
        
        existing_observer = self.get_user_active_pairing(safety_observer_id)
        if existing_observer:
            observer_user = self.get_user_by_id(safety_observer_id)
            observer_name = observer_user["name"] if observer_user else f"User {safety_observer_id}"
            raise ValueError(f"Cannot create pairing: {observer_name} is already in an active pairing")
        
        with self.get_connection() as conn:
            if self.db_type == 'postgres':
                query = """
                    INSERT INTO pairings (pilot_id, safety_observer_id, is_active)
                    VALUES (%s, %s, true)
                """
            else:
                query = """
                    INSERT INTO pairings (pilot_id, safety_observer_id, is_active)
                    VALUES (?, ?, 1)
                """
            pairing_id = self._insert_returning_id(conn, query, (pilot_id, safety_observer_id))
            logger.info(f"Created pairing: pilot={pilot_id}, observer={safety_observer_id} (ID: {pairing_id})")
            return pairing_id

    def get_pairing(self, pairing_id: int) -> Optional[Dict]:
        """Get pairing by ID."""
        with self.get_connection() as conn:
            query = "SELECT * FROM pairings WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM pairings WHERE id = ?"
            cursor = self._execute_query(conn, query, (pairing_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_active_pairing(self, user_id: int) -> Optional[Dict]:
        """Check if user is in any active pairing (as pilot or observer)."""
        with self.get_connection() as conn:
            if self.db_type == 'postgres':
                query = """
                    SELECT * FROM pairings
                    WHERE (pilot_id = %s OR safety_observer_id = %s)
                    AND is_active = true
                """
            else:
                query = """
                    SELECT * FROM pairings
                    WHERE (pilot_id = ? OR safety_observer_id = ?)
                    AND is_active = 1
                """
            cursor = self._execute_query(conn, query, (user_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_pairings(self, active_only: bool = False) -> List[Dict]:
        """List all pairings with pilot and observer names."""
        with self.get_connection() as conn:
            if active_only:
                if self.db_type == 'postgres':
                    query = """
                        SELECT p.id, p.pilot_id, p.safety_observer_id, p.is_active, p.created_at,
                               pilot.name as pilot_name, pilot.email as pilot_email,
                               observer.name as observer_name, observer.email as observer_email
                        FROM pairings p
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        WHERE p.is_active = true
                        ORDER BY p.created_at DESC
                    """
                else:
                    query = """
                        SELECT p.id, p.pilot_id, p.safety_observer_id, p.is_active, p.created_at,
                               pilot.name as pilot_name, pilot.email as pilot_email,
                               observer.name as observer_name, observer.email as observer_email
                        FROM pairings p
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        WHERE p.is_active = 1
                        ORDER BY p.created_at DESC
                    """
            else:
                if self.db_type == 'postgres':
                    query = """
                        SELECT p.id, p.pilot_id, p.safety_observer_id, p.is_active, p.created_at,
                               pilot.name as pilot_name, pilot.email as pilot_email,
                               observer.name as observer_name, observer.email as observer_email
                        FROM pairings p
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        ORDER BY p.is_active DESC, p.created_at DESC
                    """
                else:
                    query = """
                        SELECT p.id, p.pilot_id, p.safety_observer_id, p.is_active, p.created_at,
                               pilot.name as pilot_name, pilot.email as pilot_email,
                               observer.name as observer_name, observer.email as observer_email
                        FROM pairings p
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        ORDER BY p.is_active DESC, p.created_at DESC
                    """
            
            cursor = self._execute_query(conn, query)
            return [dict(row) for row in cursor.fetchall()]

    def list_pairings_for_member(self, member_id: int, active_only: bool = True) -> List[Dict]:
        """List pairings for a specific member (as pilot or observer)."""
        with self.get_connection() as conn:
            if active_only:
                if self.db_type == 'postgres':
                    query = """
                        SELECT * FROM pairings 
                        WHERE (pilot_id = %s OR safety_observer_id = %s) AND is_active = true
                    """
                else:
                    query = """
                        SELECT * FROM pairings 
                        WHERE (pilot_id = ? OR safety_observer_id = ?) AND is_active = 1
                    """
            else:
                if self.db_type == 'postgres':
                    query = """
                        SELECT * FROM pairings 
                        WHERE pilot_id = %s OR safety_observer_id = %s
                    """
                else:
                    query = """
                        SELECT * FROM pairings 
                        WHERE pilot_id = ? OR safety_observer_id = ?
                    """
            
            cursor = self._execute_query(conn, query, (member_id, member_id))
            return [dict(row) for row in cursor.fetchall()]

    def get_active_pairing_for_member(self, member_id: int) -> Optional[Dict]:
        """Get active pairing for a member (should be only 1)."""
        pairings = self.list_pairings_for_member(member_id, active_only=True)
        return pairings[0] if pairings else None

    def update_pairing(self, pairing_id: int, **kwargs) -> bool:
        """Update pairing fields. Returns success."""
        allowed_fields = {"pilot_id", "safety_observer_id", "is_active"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        if self.db_type == 'postgres':
            set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
            query = f"UPDATE pairings SET {set_clause} WHERE id = %s"
        else:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            query = f"UPDATE pairings SET {set_clause} WHERE id = ?"
        
        values = list(updates.values()) + [pairing_id]

        with self.get_connection() as conn:
            cursor = self._execute_query(conn, query, tuple(values))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def break_pairing(self, pairing_id: int) -> bool:
        """Disable a pairing (set is_active = 0)."""
        return self.update_pairing(pairing_id, is_active=0 if self.db_type == 'sqlite' else False)

    def delete_pairing(self, pairing_id: int) -> bool:
        """Delete a pairing."""
        with self.get_connection() as conn:
            query = "DELETE FROM pairings WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM pairings WHERE id = ?"
            cursor = self._execute_query(conn, query, (pairing_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    # ===== AIRPORT MANAGEMENT =====

    def create_airport(self, code: str) -> int:
        """Create airport. Returns airport ID."""
        with self.get_connection() as conn:
            query = "INSERT INTO airports (code) VALUES (%s)" if self.db_type == 'postgres' else "INSERT INTO airports (code) VALUES (?)"
            airport_id = self._insert_returning_id(conn, query, (code,))
            return airport_id

    def get_airport(self, airport_id: int) -> Optional[Dict]:
        """Get airport by ID."""
        with self.get_connection() as conn:
            query = "SELECT * FROM airports WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM airports WHERE id = ?"
            cursor = self._execute_query(conn, query, (airport_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_airports(self) -> List[Dict]:
        """List all airports."""
        with self.get_connection() as conn:
            query = "SELECT * FROM airports ORDER BY code"
            cursor = self._execute_query(conn, query)
            return [dict(row) for row in cursor.fetchall()]

    def delete_airport(self, airport_id: int) -> bool:
        """Delete airport."""
        with self.get_connection() as conn:
            query = "DELETE FROM airports WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM airports WHERE id = ?"
            cursor = self._execute_query(conn, query, (airport_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    # ===== START GATE MANAGEMENT =====

    def create_start_gate(self, airport_id: int, name: str, lat: float, lon: float) -> int:
        """Create start gate. Returns gate ID."""
        with self.get_connection() as conn:
            query = """
                INSERT INTO start_gates (airport_id, name, lat, lon)
                VALUES (%s, %s, %s, %s)
            """ if self.db_type == 'postgres' else """
                INSERT INTO start_gates (airport_id, name, lat, lon)
                VALUES (?, ?, ?, ?)
            """
            gate_id = self._insert_returning_id(conn, query, (airport_id, name, lat, lon))
            return gate_id

    def delete_start_gate(self, gate_id: int) -> bool:
        """Delete start gate."""
        with self.get_connection() as conn:
            query = "DELETE FROM start_gates WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM start_gates WHERE id = ?"
            cursor = self._execute_query(conn, query, (gate_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    # ===== NAV & CHECKPOINT MANAGEMENT =====

    def create_nav(self, name: str, airport_id: int) -> int:
        """Create NAV route. Returns nav ID."""
        with self.get_connection() as conn:
            query = "INSERT INTO navs (name, airport_id) VALUES (%s, %s)" if self.db_type == 'postgres' else "INSERT INTO navs (name, airport_id) VALUES (?, ?)"
            nav_id = self._insert_returning_id(conn, query, (name, airport_id))
            return nav_id

    def delete_nav(self, nav_id: int) -> bool:
        """Delete NAV route."""
        with self.get_connection() as conn:
            query = "DELETE FROM navs WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM navs WHERE id = ?"
            cursor = self._execute_query(conn, query, (nav_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def create_checkpoint(self, nav_id: int, sequence: int, name: str, lat: float, lon: float) -> int:
        """Create checkpoint. Returns checkpoint ID."""
        with self.get_connection() as conn:
            query = """
                INSERT INTO checkpoints (nav_id, sequence, name, lat, lon)
                VALUES (%s, %s, %s, %s, %s)
            """ if self.db_type == 'postgres' else """
                INSERT INTO checkpoints (nav_id, sequence, name, lat, lon)
                VALUES (?, ?, ?, ?, ?)
            """
            checkpoint_id = self._insert_returning_id(conn, query, (nav_id, sequence, name, lat, lon))
            return checkpoint_id

    def get_checkpoint(self, checkpoint_id: int) -> Optional[Dict]:
        """Get checkpoint by ID."""
        with self.get_connection() as conn:
            query = "SELECT * FROM checkpoints WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM checkpoints WHERE id = ?"
            cursor = self._execute_query(conn, query, (checkpoint_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_checkpoint(self, checkpoint_id: int) -> bool:
        """Delete checkpoint."""
        with self.get_connection() as conn:
            query = "DELETE FROM checkpoints WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM checkpoints WHERE id = ?"
            cursor = self._execute_query(conn, query, (checkpoint_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    def get_nav(self, nav_id: int) -> Optional[Dict]:
        """Get NAV with checkpoints."""
        with self.get_connection() as conn:
            query = "SELECT * FROM navs WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM navs WHERE id = ?"
            cursor = self._execute_query(conn, query, (nav_id,))
            nav_row = cursor.fetchone()
            if not nav_row:
                return None
            nav = dict(nav_row)
            
            query = "SELECT * FROM checkpoints WHERE nav_id = %s ORDER BY sequence" if self.db_type == 'postgres' else "SELECT * FROM checkpoints WHERE nav_id = ? ORDER BY sequence"
            cursor = self._execute_query(conn, query, (nav_id,))
            nav["checkpoints"] = [dict(row) for row in cursor.fetchall()]
            return nav

    def list_navs(self) -> List[Dict]:
        """List all NAVs."""
        with self.get_connection() as conn:
            query = "SELECT * FROM navs ORDER BY name"
            cursor = self._execute_query(conn, query)
            return [dict(row) for row in cursor.fetchall()]

    def list_navs_by_airport(self, airport_id: int) -> List[Dict]:
        """List NAVs for an airport."""
        with self.get_connection() as conn:
            query = "SELECT * FROM navs WHERE airport_id = %s ORDER BY name" if self.db_type == 'postgres' else "SELECT * FROM navs WHERE airport_id = ? ORDER BY name"
            cursor = self._execute_query(conn, query, (airport_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_checkpoints(self, nav_id: int) -> List[Dict]:
        """Get checkpoints for a NAV."""
        with self.get_connection() as conn:
            query = "SELECT * FROM checkpoints WHERE nav_id = %s ORDER BY sequence" if self.db_type == 'postgres' else "SELECT * FROM checkpoints WHERE nav_id = ? ORDER BY sequence"
            cursor = self._execute_query(conn, query, (nav_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_start_gates(self, airport_id: int) -> List[Dict]:
        """Get start gates for an airport."""
        with self.get_connection() as conn:
            query = "SELECT * FROM start_gates WHERE airport_id = %s ORDER BY name" if self.db_type == 'postgres' else "SELECT * FROM start_gates WHERE airport_id = ? ORDER BY name"
            cursor = self._execute_query(conn, query, (airport_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_start_gate(self, gate_id: int) -> Optional[Dict]:
        """Get a specific start gate."""
        with self.get_connection() as conn:
            query = "SELECT * FROM start_gates WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM start_gates WHERE id = ?"
            cursor = self._execute_query(conn, query, (gate_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ===== SECRETS MANAGEMENT =====

    def get_secrets(self, nav_id: int) -> List[Dict]:
        """Get secrets for a NAV."""
        with self.get_connection() as conn:
            query = "SELECT * FROM secrets WHERE nav_id = %s ORDER BY id" if self.db_type == 'postgres' else "SELECT * FROM secrets WHERE nav_id = ? ORDER BY id"
            cursor = self._execute_query(conn, query, (nav_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_secret(self, secret_id: int) -> Optional[Dict]:
        """Get secret by ID."""
        with self.get_connection() as conn:
            query = "SELECT * FROM secrets WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM secrets WHERE id = ?"
            cursor = self._execute_query(conn, query, (secret_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_secret(self, nav_id: int, name: str, lat: float, lon: float, secret_type: str) -> int:
        """Create a secret. Returns secret ID."""
        with self.get_connection() as conn:
            query = """
                INSERT INTO secrets (nav_id, name, lat, lon, type)
                VALUES (%s, %s, %s, %s, %s)
            """ if self.db_type == 'postgres' else """
                INSERT INTO secrets (nav_id, name, lat, lon, type)
                VALUES (?, ?, ?, ?, ?)
            """
            secret_id = self._insert_returning_id(conn, query, (nav_id, name, lat, lon, secret_type))
            return secret_id

    def delete_secret(self, secret_id: int) -> bool:
        """Delete a secret."""
        with self.get_connection() as conn:
            query = "DELETE FROM secrets WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM secrets WHERE id = ?"
            cursor = self._execute_query(conn, query, (secret_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True

    # ===== PRE-NAV SUBMISSIONS =====

    def create_prenav(self, pairing_id: int, pilot_id: int, nav_id: int, leg_times: List[float],
                     total_time: float, fuel_estimate: float, token: str, expires_at: datetime) -> int:
        """Create a pre-NAV submission. Returns prenav ID."""
        with self.get_connection() as conn:
            query = """
                INSERT INTO prenav_submissions
                (pairing_id, pilot_id, nav_id, leg_times, total_time, fuel_estimate, token, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """ if self.db_type == 'postgres' else """
                INSERT INTO prenav_submissions
                (pairing_id, pilot_id, nav_id, leg_times, total_time, fuel_estimate, token, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            prenav_id = self._insert_returning_id(conn, query, 
                (pairing_id, pilot_id, nav_id, json.dumps(leg_times), total_time, fuel_estimate, token, expires_at))
            return prenav_id

    def get_prenav_by_token(self, token: str) -> Optional[Dict]:
        """Get pre-NAV by token."""
        with self.get_connection() as conn:
            query = "SELECT * FROM prenav_submissions WHERE token = %s" if self.db_type == 'postgres' else "SELECT * FROM prenav_submissions WHERE token = ?"
            cursor = self._execute_query(conn, query, (token,))
            row = cursor.fetchone()
            if not row:
                return None
            prenav = dict(row)
            prenav["leg_times"] = json.loads(prenav["leg_times"])
            return prenav

    def get_prenav(self, prenav_id: int) -> Optional[Dict]:
        """Get pre-NAV by ID."""
        with self.get_connection() as conn:
            query = "SELECT * FROM prenav_submissions WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM prenav_submissions WHERE id = ?"
            cursor = self._execute_query(conn, query, (prenav_id,))
            row = cursor.fetchone()
            if not row:
                return None
            prenav = dict(row)
            prenav["leg_times"] = json.loads(prenav["leg_times"])
            return prenav

    def delete_expired_prenavs(self) -> int:
        """Delete expired pre-NAV submissions. Returns count deleted."""
        with self.get_connection() as conn:
            query = "DELETE FROM prenav_submissions WHERE expires_at < CURRENT_TIMESTAMP"
            cursor = self._execute_query(conn, query)
            return cursor.rowcount if hasattr(cursor, 'rowcount') else 0

    # ===== FLIGHT RESULTS =====

    def create_flight_result(self, prenav_id: int, pairing_id: int, nav_id: int, gpx_filename: str,
                            actual_fuel: float, secrets_checkpoint: int, secrets_enroute: int,
                            start_gate_id: int, overall_score: float, checkpoint_results: List[Dict]) -> int:
        """Create a flight result. Returns result ID."""
        with self.get_connection() as conn:
            query = """
                INSERT INTO flight_results
                (prenav_id, pairing_id, nav_id, gpx_filename, actual_fuel,
                 secrets_missed_checkpoint, secrets_missed_enroute, start_gate_id,
                 overall_score, checkpoint_results)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """ if self.db_type == 'postgres' else """
                INSERT INTO flight_results
                (prenav_id, pairing_id, nav_id, gpx_filename, actual_fuel,
                 secrets_missed_checkpoint, secrets_missed_enroute, start_gate_id,
                 overall_score, checkpoint_results)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            result_id = self._insert_returning_id(conn, query,
                (prenav_id, pairing_id, nav_id, gpx_filename, actual_fuel, secrets_checkpoint,
                 secrets_enroute, start_gate_id, overall_score, json.dumps(checkpoint_results)))
            return result_id

    def get_flight_result(self, result_id: int) -> Optional[Dict]:
        """Get flight result by ID."""
        with self.get_connection() as conn:
            query = "SELECT * FROM flight_results WHERE id = %s" if self.db_type == 'postgres' else "SELECT * FROM flight_results WHERE id = ?"
            cursor = self._execute_query(conn, query, (result_id,))
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            try:
                if result["checkpoint_results"]:
                    result["checkpoint_results"] = json.loads(result["checkpoint_results"])
                else:
                    result["checkpoint_results"] = []
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error parsing checkpoint_results for result {result_id}: {e}")
                result["checkpoint_results"] = []
            return result

    def list_flight_results(self, pairing_id: Optional[int] = None, nav_id: Optional[int] = None,
                           start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """List flight results with optional filters."""
        with self.get_connection() as conn:
            query = "SELECT * FROM flight_results WHERE 1=1"
            params = []

            if pairing_id:
                query += " AND pairing_id = %s" if self.db_type == 'postgres' else " AND pairing_id = ?"
                params.append(pairing_id)
            if nav_id:
                query += " AND nav_id = %s" if self.db_type == 'postgres' else " AND nav_id = ?"
                params.append(nav_id)
            if start_date:
                query += " AND scored_at >= %s" if self.db_type == 'postgres' else " AND scored_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND scored_at <= %s" if self.db_type == 'postgres' else " AND scored_at <= ?"
                params.append(end_date)

            query += " ORDER BY scored_at DESC"

            cursor = self._execute_query(conn, query, tuple(params))
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                try:
                    if result["checkpoint_results"]:
                        result["checkpoint_results"] = json.loads(result["checkpoint_results"])
                    else:
                        result["checkpoint_results"] = []
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Error parsing checkpoint_results for result {result['id']}: {e}")
                    result["checkpoint_results"] = []
                results.append(result)
            return results

    def delete_flight_result(self, result_id: int) -> bool:
        """Delete a flight result."""
        with self.get_connection() as conn:
            query = "DELETE FROM flight_results WHERE id = %s" if self.db_type == 'postgres' else "DELETE FROM flight_results WHERE id = ?"
            cursor = self._execute_query(conn, query, (result_id,))
            return cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else True
