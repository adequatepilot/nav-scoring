"""
SQLite database wrapper for NAV Scoring system.
Handles schema migrations, queries, and data access.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
import pytz

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "data/navs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Don't initialize immediately - do it lazily on first use
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure database is initialized (lazy initialization)."""
        if self._initialized:
            return
        self._init_db()
        self._initialized = True

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        self._ensure_initialized()
        # Use WAL mode for better concurrency, shorter timeout for faster failure detection
        conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
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
        """Initialize database with schema and run migrations."""
        try:
            # Create initial schema (this also creates the database file)
            self._run_initial_schema()
            # Then run any pending migrations
            self._run_migrations()
            # Finally, seed default accounts if needed
            self._seed_default_accounts()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def _run_initial_schema(self):
        """Run initial schema creation (creates database file and base tables)."""
        migrations_dir = Path(__file__).parent.parent / "migrations"
        schema_file = migrations_dir / "001_initial_schema.sql"
        
        if not schema_file.exists():
            logger.warning(f"Initial schema file not found: {schema_file}")
            return
        
        # Create connection (which creates the database file)
        conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False, isolation_level=None)
        try:
            with open(schema_file, "r") as f:
                sql = f.read()
            
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for statement in statements:
                conn.execute(statement)
            conn.commit()
            logger.info("Initial schema created successfully")
        except Exception as e:
            logger.error(f"Error running initial schema: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _run_migrations(self):
        """Run any pending migrations."""
        migrations_dir = Path(__file__).parent.parent / "migrations"
        migration_files = sorted([f for f in migrations_dir.glob("*.sql") if f.name != "001_initial_schema.sql"])
        
        if not migration_files:
            return
        
        conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False, isolation_level=None)
        try:
            for migration_file in migration_files:
                with open(migration_file, "r") as f:
                    sql = f.read()
                
                # Remove comments
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
            logger.info("Migrations completed")
        finally:
            conn.close()
    
    def _seed_default_accounts(self):
        """Create default admin account if it doesn't exist."""
        try:
            from passlib.context import CryptContext
            
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
            cursor = conn.cursor()
            
            # Check if users table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                logger.error("❌ Users table does not exist after migrations! Cannot seed admin account.")
                conn.close()
                return
            
            logger.info("✓ Users table exists, checking for admin account...")
            
            # Check if admin already exists
            cursor.execute("SELECT id, email_verified FROM users WHERE email = ?", ("admin@siu.edu",))
            result = cursor.fetchone()
            
            if result:
                admin_id, is_verified = result
                if is_verified:
                    logger.info("✓ Admin account already exists and is verified")
                    conn.close()
                    return
                else:
                    # Admin exists but not verified - fix it
                    logger.info("✓ Admin exists but not verified - marking as verified...")
                    cursor.execute(
                        "UPDATE users SET email_verified=1 WHERE id=?",
                        (admin_id,)
                    )
                    conn.commit()
                    logger.info("✅ Admin account marked as verified")
                    conn.close()
                    return
            
            # Create admin account (all required fields)
            logger.info("Creating admin account...")
            admin_password_hash = pwd_context.hash("admin123")
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, name, is_admin, is_approved, is_coach, email_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("admin", "admin@siu.edu", admin_password_hash, "Main Administrator", 1, 1, 0, 1)
            )
            
            conn.commit()
            logger.info("✅ SUCCESS: Admin account created: admin@siu.edu / admin123")
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ FAILED to seed admin account: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ===== MEMBER MANAGEMENT =====

    def create_member(self, username: str, password_hash: str, email: str, name: str) -> int:
        """Create a new member account. Returns member ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO members (username, password_hash, email, name)
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, email, name),
            )
            member_id = cursor.lastrowid
            logger.info(f"Created member: {username} (ID: {member_id})")
            return member_id

    def get_member_by_username(self, username: str) -> Optional[Dict]:
        """Get member by username."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM members WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_member_by_id(self, member_id: int) -> Optional[Dict]:
        """Get member by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_members(self) -> List[Dict]:
        """List all members (approved users). Bug fix: query users table instead of members."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE is_approved = 1 ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def list_active_members(self) -> List[Dict]:
        """List active members only (approved users)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE is_approved = 1 ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def update_member(self, member_id: int, **kwargs) -> bool:
        """Update member fields. Returns success."""
        allowed_fields = {"password_hash", "email", "name", "is_active"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [member_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE members SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0

    def update_member_last_login(self, member_id: int) -> bool:
        """Update last login timestamp."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE members SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (member_id,),
            )
            return cursor.rowcount > 0

    def delete_member(self, member_id: int) -> bool:
        """Delete a member."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
            return cursor.rowcount > 0

    def bulk_create_members(self, members: List[Tuple[str, str, str]]) -> int:
        """Bulk create members. Input: [(username, email, name), ...]"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO members (username, email, name, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                [(u, e, n, "") for u, e, n in members],  # Empty password_hash initially
            )
            logger.info(f"Bulk created {cursor.rowcount} members")
            return cursor.rowcount

    # ===== COACH MANAGEMENT =====

    def init_coach(self, username: str, password_hash: str, email: str) -> bool:
        """Initialize coach account."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM coach")
            if cursor.fetchone()[0] > 0:
                logger.warning("Coach account already exists")
                return False
            cursor.execute(
                "INSERT INTO coach (username, password_hash, email) VALUES (?, ?, ?)",
                (username, password_hash, email),
            )
            logger.info("Coach account initialized")
            return True

    def get_coach(self) -> Optional[Dict]:
        """Get coach account."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM coach LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_coach_password(self, password_hash: str) -> bool:
        """Update coach password."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE coach SET password_hash = ? WHERE id = 1", (password_hash,))
            return cursor.rowcount > 0

    def update_coach_last_login(self) -> bool:
        """Update coach last login timestamp."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE coach SET last_login = CURRENT_TIMESTAMP WHERE id = 1"
            )
            return cursor.rowcount > 0

    def is_coach_admin(self) -> bool:
        """Check if coach is admin."""
        coach = self.get_coach()
        return coach.get("is_admin", 0) == 1 if coach else False

    def set_coach_admin(self, is_admin: bool) -> bool:
        """Set admin status for coach."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE coach SET is_admin = ? WHERE id = 1",
                (1 if is_admin else 0,)
            )
            return cursor.rowcount > 0

    # ===== UNIFIED USER MANAGEMENT (NEW) =====

    def create_user(self, username: str, password_hash: str, email: str, name: str, 
                   is_coach: bool = False, is_admin: bool = False, is_approved: bool = False,
                   email_verified: bool = False, must_reset_password: bool = False) -> int:
        """Create a new user in the unified users table. Returns user ID.
        username is now the same as email for consistency.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, email, name, is_coach, is_admin, is_approved, email_verified, must_reset_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (username, password_hash, email, name, 1 if is_coach else 0, 1 if is_admin else 0, 
                 1 if is_approved else 0, 1 if email_verified else 0, 1 if must_reset_password else 0),
            )
            user_id = cursor.lastrowid
            logger.info(f"Created user: {email} (ID: {user_id}, coach={is_coach}, admin={is_admin}, verified={email_verified}, must_reset={must_reset_password})")
            return user_id

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username from unified users table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID from unified users table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email from unified users table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_users(self, filter_type: str = "all") -> List[Dict]:
        """List users with optional filtering.
        filter_type: 'all', 'pending', 'coaches', 'admins', 'approved'
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if filter_type == "pending":
                cursor.execute("SELECT * FROM users WHERE is_approved = 0 ORDER BY created_at")
            elif filter_type == "coaches":
                cursor.execute("SELECT * FROM users WHERE is_coach = 1 ORDER BY name")
            elif filter_type == "admins":
                cursor.execute("SELECT * FROM users WHERE is_admin = 1 ORDER BY name")
            elif filter_type == "approved":
                cursor.execute("SELECT * FROM users WHERE is_approved = 1 ORDER BY name")
            else:
                cursor.execute("SELECT * FROM users ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def get_available_pairing_users(self) -> List[Dict]:
        """Get users available for pairing (exclude coaches, admins, and already-paired users)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.* FROM users u
                WHERE u.is_coach = 0 
                  AND u.is_admin = 0
                  AND u.is_approved = 1
                  AND u.id NOT IN (
                      SELECT pilot_id FROM pairings WHERE is_active = 1
                      UNION
                      SELECT safety_observer_id FROM pairings WHERE is_active = 1
                  )
                ORDER BY u.name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields. Returns success."""
        allowed_fields = {"password_hash", "email", "name", "is_coach", "is_admin", "is_approved", "profile_picture_path", "must_reset_password", "can_modify_profile_picture"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0

    def approve_user(self, user_id: int) -> bool:
        """Approve a pending user account."""
        return self.update_user(user_id, is_approved=1)

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0

    def update_user_last_login(self, user_id: int) -> bool:
        """Update last login timestamp for user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,),
            )
            return cursor.rowcount > 0

    # ===== USER EMAIL MANAGEMENT =====

    def add_user_email(self, user_id: int, email: str) -> bool:
        """Add additional email address for user. Returns success."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_emails (user_id, email, is_primary)
                    VALUES (?, ?, 0)
                    """,
                    (user_id, email),
                )
                logger.info(f"Added email {email} for user {user_id}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Email {email} already exists for another user")
            return False
        except Exception as e:
            logger.error(f"Error adding email for user {user_id}: {e}")
            return False

    def remove_user_email(self, user_id: int, email: str) -> bool:
        """Remove additional email address for user. Cannot remove primary email. Returns success."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Check if it's the primary email
                cursor.execute(
                    "SELECT is_primary FROM user_emails WHERE user_id = ? AND email = ?",
                    (user_id, email),
                )
                row = cursor.fetchone()
                
                if not row:
                    logger.warning(f"Email {email} not found for user {user_id}")
                    return False
                
                if row[0] == 1:  # is_primary = 1
                    logger.warning(f"Cannot remove primary email {email} for user {user_id}")
                    return False
                
                # Delete the additional email
                cursor.execute(
                    "DELETE FROM user_emails WHERE user_id = ? AND email = ?",
                    (user_id, email),
                )
                logger.info(f"Removed email {email} for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error removing email for user {user_id}: {e}")
            return False

    def get_user_emails(self, user_id: int) -> List[str]:
        """Get all additional (non-primary) email addresses for user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT email FROM user_emails WHERE user_id = ? AND is_primary = 0 ORDER BY created_at",
                    (user_id,),
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting additional emails for user {user_id}: {e}")
            return []

    def get_all_emails_for_user(self, user_id: int) -> List[str]:
        """Get all emails for user (primary + additional)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT email FROM user_emails WHERE user_id = ? ORDER BY is_primary DESC, created_at",
                    (user_id,),
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all emails for user {user_id}: {e}")
            # Fallback to just the primary email from users table
            user = self.get_user_by_id(user_id)
            return [user["email"]] if user else []

    def email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email exists in user_emails table (for a different user)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if exclude_user_id:
                    cursor.execute(
                        "SELECT 1 FROM user_emails WHERE email = ? AND user_id != ?",
                        (email, exclude_user_id),
                    )
                else:
                    cursor.execute(
                        "SELECT 1 FROM user_emails WHERE email = ?",
                        (email,),
                    )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking if email exists: {e}")
            return False

    # ===== EMAIL VERIFICATION =====

    def create_verification_pending(self, email: str, password_hash: str, name: str, 
                                   verification_token: str) -> int:
        """Create a pending verification entry. Returns ID."""
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO verification_pending (email, password_hash, name, verification_token, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email, password_hash, name, verification_token, expires_at.isoformat()),
            )
            verification_id = cursor.lastrowid
            logger.info(f"Created verification pending: {email} (ID: {verification_id})")
            return verification_id

    def get_verification_pending_by_token(self, token: str) -> Optional[Dict]:
        """Get verification pending by token."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM verification_pending WHERE verification_token = ?", (token,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_verification_pending_by_email(self, email: str) -> Optional[Dict]:
        """Get verification pending by email."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM verification_pending WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_verification_pending(self, verification_id: int) -> bool:
        """Delete a verification pending entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM verification_pending WHERE id = ?", (verification_id,))
            return cursor.rowcount > 0

    def cleanup_expired_verification_pending(self) -> int:
        """Delete expired verification pending entries. Returns count deleted."""
        from datetime import datetime
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM verification_pending WHERE expires_at < ?",
                (datetime.utcnow().isoformat(),)
            )
            count = cursor.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} expired verification tokens")
            return count

    # ===== PAIRING MANAGEMENT =====

    def create_pairing(self, pilot_id: int, safety_observer_id: int) -> int:
        """Create a new pairing. Returns pairing ID."""
        if pilot_id == safety_observer_id:
            raise ValueError("Pilot and safety observer must be different members")
        
        # Check if pilot is already in an active pairing (issue 12)
        existing_pilot = self.get_user_active_pairing(pilot_id)
        if existing_pilot:
            raise ValueError(f"Pilot is already in an active pairing")
        
        # Check if observer is already in an active pairing (issue 12)
        existing_observer = self.get_user_active_pairing(safety_observer_id)
        if existing_observer:
            raise ValueError(f"Observer is already in an active pairing")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pairings (pilot_id, safety_observer_id, is_active)
                VALUES (?, ?, 1)
                """,
                (pilot_id, safety_observer_id),
            )
            pairing_id = cursor.lastrowid
            logger.info(f"Created pairing: pilot={pilot_id}, observer={safety_observer_id} (ID: {pairing_id})")
            return pairing_id

    def get_pairing(self, pairing_id: int) -> Optional[Dict]:
        """Get pairing by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pairings WHERE id = ?", (pairing_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_active_pairing(self, user_id: int) -> Optional[Dict]:
        """Check if user is in any active pairing (as pilot or observer). Issue 12."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pairings
                WHERE (pilot_id = ? OR safety_observer_id = ?)
                AND is_active = 1
            """, (user_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_pairings(self, active_only: bool = False) -> List[Dict]:
        """List all pairings with pilot and observer names (issue 15)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("""
                    SELECT p.id, p.pilot_id, p.safety_observer_id, p.is_active, p.created_at,
                           pilot.name as pilot_name, pilot.email as pilot_email,
                           observer.name as observer_name, observer.email as observer_email
                    FROM pairings p
                    JOIN users pilot ON p.pilot_id = pilot.id
                    JOIN users observer ON p.safety_observer_id = observer.id
                    WHERE p.is_active = 1
                    ORDER BY p.created_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT p.id, p.pilot_id, p.safety_observer_id, p.is_active, p.created_at,
                           pilot.name as pilot_name, pilot.email as pilot_email,
                           observer.name as observer_name, observer.email as observer_email
                    FROM pairings p
                    JOIN users pilot ON p.pilot_id = pilot.id
                    JOIN users observer ON p.safety_observer_id = observer.id
                    ORDER BY p.is_active DESC, p.created_at DESC
                """)
            return [dict(row) for row in cursor.fetchall()]

    def list_pairings_for_member(self, member_id: int, active_only: bool = True) -> List[Dict]:
        """List pairings for a specific member (as pilot or observer)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute(
                    """
                    SELECT * FROM pairings 
                    WHERE (pilot_id = ? OR safety_observer_id = ?) AND is_active = 1
                    """,
                    (member_id, member_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM pairings 
                    WHERE pilot_id = ? OR safety_observer_id = ?
                    """,
                    (member_id, member_id),
                )
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

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [pairing_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE pairings SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0

    def break_pairing(self, pairing_id: int) -> bool:
        """Disable a pairing (set is_active = 0)."""
        return self.update_pairing(pairing_id, is_active=0)

    def delete_pairing(self, pairing_id: int) -> bool:
        """Delete a pairing."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pairings WHERE id = ?", (pairing_id,))
            return cursor.rowcount > 0

    # ===== AIRPORT MANAGEMENT =====

    def create_airport(self, code: str) -> int:
        """Create airport. Returns airport ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO airports (code) VALUES (?)",
                (code,),
            )
            return cursor.lastrowid

    def get_airport(self, airport_id: int) -> Optional[Dict]:
        """Get airport by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM airports WHERE id = ?", (airport_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_airports(self) -> List[Dict]:
        """List all airports."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM airports ORDER BY code")
            return [dict(row) for row in cursor.fetchall()]

    def delete_airport(self, airport_id: int) -> bool:
        """Delete airport."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM airports WHERE id = ?", (airport_id,))
            return cursor.rowcount > 0

    # ===== START GATE MANAGEMENT =====

    def create_start_gate(self, airport_id: int, name: str, lat: float, lon: float) -> int:
        """Create start gate. Returns gate ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO start_gates (airport_id, name, lat, lon)
                VALUES (?, ?, ?, ?)
                """,
                (airport_id, name, lat, lon),
            )
            return cursor.lastrowid

    def delete_start_gate(self, gate_id: int) -> bool:
        """Delete start gate."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM start_gates WHERE id = ?", (gate_id,))
            return cursor.rowcount > 0

    # ===== NAV & CHECKPOINT MANAGEMENT =====

    def create_nav(self, name: str, airport_id: int) -> int:
        """Create NAV route. Returns nav ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO navs (name, airport_id) VALUES (?, ?)",
                (name, airport_id),
            )
            return cursor.lastrowid

    def delete_nav(self, nav_id: int) -> bool:
        """Delete NAV route."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM navs WHERE id = ?", (nav_id,))
            return cursor.rowcount > 0

    def create_checkpoint(self, nav_id: int, sequence: int, name: str, lat: float, lon: float) -> int:
        """Create checkpoint. Returns checkpoint ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO checkpoints (nav_id, sequence, name, lat, lon)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nav_id, sequence, name, lat, lon),
            )
            return cursor.lastrowid

    def get_checkpoint(self, checkpoint_id: int) -> Optional[Dict]:
        """Get checkpoint by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM checkpoints WHERE id = ?", (checkpoint_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_checkpoint(self, checkpoint_id: int) -> bool:
        """Delete checkpoint."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checkpoints WHERE id = ?", (checkpoint_id,))
            return cursor.rowcount > 0

    def update_checkpoint(self, checkpoint_id: int, sequence: int, name: str, lat: float, lon: float) -> bool:
        """Update checkpoint details. Item 36."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE checkpoints
                SET sequence = ?, name = ?, lat = ?, lon = ?
                WHERE id = ?
            """, (sequence, name, lat, lon, checkpoint_id))
            return cursor.rowcount > 0

    def update_checkpoint_sequence(self, checkpoint_id: int, sequence: int) -> bool:
        """Update checkpoint sequence (for drag-and-drop reordering). Item 36."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE checkpoints SET sequence = ? WHERE id = ?", (sequence, checkpoint_id))
            return cursor.rowcount > 0

    def get_nav(self, nav_id: int) -> Optional[Dict]:
        """Get NAV with checkpoints."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM navs WHERE id = ?", (nav_id,))
            nav_row = cursor.fetchone()
            if not nav_row:
                return None
            nav = dict(nav_row)
            cursor.execute(
                "SELECT * FROM checkpoints WHERE nav_id = ? ORDER BY sequence",
                (nav_id,),
            )
            nav["checkpoints"] = [dict(row) for row in cursor.fetchall()]
            return nav

    def list_navs(self) -> List[Dict]:
        """List all NAVs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM navs ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def list_navs_by_airport(self, airport_id: int) -> List[Dict]:
        """List NAVs for an airport."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM navs WHERE airport_id = ? ORDER BY name",
                (airport_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_nav_pdf(self, nav_id: int, pdf_path: str) -> bool:
        """Update NAV PDF path."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE navs SET pdf_path = ? WHERE id = ?", (pdf_path, nav_id))
            return cursor.rowcount > 0

    def delete_nav_pdf(self, nav_id: int) -> bool:
        """Delete NAV PDF path (sets to NULL)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE navs SET pdf_path = NULL WHERE id = ?", (nav_id,))
            return cursor.rowcount > 0

    def get_checkpoints(self, nav_id: int) -> List[Dict]:
        """Get checkpoints for a NAV."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM checkpoints WHERE nav_id = ? ORDER BY sequence",
                (nav_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_start_gates(self, airport_id: int) -> List[Dict]:
        """Get start gates for an airport."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM start_gates WHERE airport_id = ? ORDER BY name",
                (airport_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_start_gate(self, gate_id: int) -> Optional[Dict]:
        """Get a specific start gate."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM start_gates WHERE id = ?", (gate_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ===== SECRETS MANAGEMENT =====

    def get_secrets(self, nav_id: int) -> List[Dict]:
        """Get secrets for a NAV."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM secrets WHERE nav_id = ? ORDER BY id",
                (nav_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_secret(self, secret_id: int) -> Optional[Dict]:
        """Get secret by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM secrets WHERE id = ?", (secret_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_secret(
        self, nav_id: int, name: str, lat: float, lon: float, secret_type: str
    ) -> int:
        """Create a secret. Returns secret ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO secrets (nav_id, name, lat, lon, type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nav_id, name, lat, lon, secret_type),
            )
            return cursor.lastrowid

    def delete_secret(self, secret_id: int) -> bool:
        """Delete a secret."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM secrets WHERE id = ?", (secret_id,))
            return cursor.rowcount > 0

    # ===== PRE-NAV SUBMISSIONS =====

    def create_prenav(
        self,
        pairing_id: int,
        pilot_id: int,
        nav_id: int,
        leg_times: List[float],
        total_time: float,
        fuel_estimate: float,
        token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> int:
        """Create a pre-NAV submission. Returns prenav ID.
        
        Note: token and expires_at are deprecated and kept for backwards compatibility.
        New submissions use status='open' instead.
        v0.4.0+: token is generated but not used in UI. status='open' determines workflow.
        """
        import hashlib
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate unique token if not provided (required by UNIQUE constraint)
            # v0.4.0+ doesn't use token in UI, but it's needed for backwards compat
            if token is None:
                # Generate unique token based on timestamp + pairing + nav
                token_seed = f"{datetime.utcnow().isoformat()}-{pairing_id}-{nav_id}"
                token = hashlib.sha256(token_seed.encode()).hexdigest()[:16]
            
            # expires_at: use provided or 48 hours from now (backwards compat)
            expires_value = expires_at if expires_at is not None else (datetime.utcnow() + timedelta(hours=48))
            
            cursor.execute(
                """
                INSERT INTO prenav_submissions
                (pairing_id, pilot_id, nav_id, leg_times, total_time, fuel_estimate, token, expires_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """,
                (
                    pairing_id,
                    pilot_id,
                    nav_id,
                    json.dumps(leg_times),
                    total_time,
                    fuel_estimate,
                    token,
                    expires_value,
                ),
            )
            return cursor.lastrowid

    def get_prenav_by_token(self, token: str) -> Optional[Dict]:
        """Get pre-NAV by token."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prenav_submissions WHERE token = ?", (token,))
            row = cursor.fetchone()
            if not row:
                return None
            prenav = dict(row)
            prenav["leg_times"] = json.loads(prenav["leg_times"])
            return prenav

    def get_prenav(self, prenav_id: int) -> Optional[Dict]:
        """Get pre-NAV by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prenav_submissions WHERE id = ?", (prenav_id,))
            row = cursor.fetchone()
            if not row:
                return None
            prenav = dict(row)
            prenav["leg_times"] = json.loads(prenav["leg_times"])
            return prenav

    def delete_expired_prenavs(self) -> int:
        """Delete expired pre-NAV submissions. Returns count deleted."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM prenav_submissions WHERE expires_at < CURRENT_TIMESTAMP"
            )
            return cursor.rowcount

    def get_open_prenav_submissions(self, user_id: Optional[int] = None, is_coach: bool = False, nav_id: Optional[int] = None) -> List[Dict]:
        """Get open prenav submissions with full details.
        
        Args:
            user_id: If provided and not coach, filter to that user's pairings only
            is_coach: If True, return all submissions regardless of user_id
            nav_id: If provided, filter to submissions for that NAV only
        
        Returns:
            List of open prenav submissions with pairing, nav, and user details.
            Includes submitted_at_display field with CST timezone conversion.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if is_coach or user_id is None:
                # Coaches/Admins see ALL open submissions
                if nav_id:
                    cursor.execute("""
                        SELECT 
                            ps.id, ps.pairing_id, ps.nav_id, ps.submitted_at as created_at, ps.status,
                            ps.pilot_id, ps.total_time, ps.fuel_estimate,
                            n.name as nav_name,
                            p.pilot_id, p.safety_observer_id,
                            pilot.name as pilot_name,
                            observer.name as observer_name
                        FROM prenav_submissions ps
                        JOIN navs n ON ps.nav_id = n.id
                        JOIN pairings p ON ps.pairing_id = p.id
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        WHERE ps.status = 'open' AND ps.nav_id = ?
                        ORDER BY ps.submitted_at DESC
                    """, (nav_id,))
                else:
                    cursor.execute("""
                        SELECT 
                            ps.id, ps.pairing_id, ps.nav_id, ps.submitted_at as created_at, ps.status,
                            ps.pilot_id, ps.total_time, ps.fuel_estimate,
                            n.name as nav_name,
                            p.pilot_id, p.safety_observer_id,
                            pilot.name as pilot_name,
                            observer.name as observer_name
                        FROM prenav_submissions ps
                        JOIN navs n ON ps.nav_id = n.id
                        JOIN pairings p ON ps.pairing_id = p.id
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        WHERE ps.status = 'open'
                        ORDER BY ps.submitted_at DESC
                    """)
            else:
                # Competitors see only their pairing's submissions
                if nav_id:
                    cursor.execute("""
                        SELECT 
                            ps.id, ps.pairing_id, ps.nav_id, ps.submitted_at as created_at, ps.status,
                            ps.pilot_id, ps.total_time, ps.fuel_estimate,
                            n.name as nav_name,
                            p.pilot_id, p.safety_observer_id,
                            pilot.name as pilot_name,
                            observer.name as observer_name
                        FROM prenav_submissions ps
                        JOIN navs n ON ps.nav_id = n.id
                        JOIN pairings p ON ps.pairing_id = p.id
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        WHERE ps.status = 'open'
                        AND (p.pilot_id = ? OR p.safety_observer_id = ?)
                        AND ps.nav_id = ?
                        ORDER BY ps.submitted_at DESC
                    """, (user_id, user_id, nav_id))
                else:
                    cursor.execute("""
                        SELECT 
                            ps.id, ps.pairing_id, ps.nav_id, ps.submitted_at as created_at, ps.status,
                            ps.pilot_id, ps.total_time, ps.fuel_estimate,
                            n.name as nav_name,
                            p.pilot_id, p.safety_observer_id,
                            pilot.name as pilot_name,
                            observer.name as observer_name
                        FROM prenav_submissions ps
                        JOIN navs n ON ps.nav_id = n.id
                        JOIN pairings p ON ps.pairing_id = p.id
                        JOIN users pilot ON p.pilot_id = pilot.id
                        JOIN users observer ON p.safety_observer_id = observer.id
                        WHERE ps.status = 'open'
                        AND (p.pilot_id = ? OR p.safety_observer_id = ?)
                        ORDER BY ps.submitted_at DESC
                    """, (user_id, user_id))
            
            submissions = [dict(row) for row in cursor.fetchall()]
            
            # Convert UTC timestamps to CST and add submitted_at_display field
            cst = pytz.timezone('America/Chicago')
            for submission in submissions:
                timestamp_str = submission.get('created_at') or submission.get('submitted_at')
                if timestamp_str:
                    try:
                        # Parse the UTC timestamp from the database
                        utc_time = datetime.fromisoformat(timestamp_str)
                        # Localize to UTC
                        utc_time = pytz.utc.localize(utc_time)
                        # Convert to CST
                        cst_time = utc_time.astimezone(cst)
                        # Format as "Feb 14, 2026 07:38 PM"
                        submission['submitted_at_display'] = cst_time.strftime('%b %d, %Y %I:%M %p')
                    except Exception as e:
                        logger.warning(f"Failed to convert timestamp {timestamp_str}: {e}")
                        submission['submitted_at_display'] = timestamp_str
                else:
                    submission['submitted_at_display'] = 'Unknown'
            
            return submissions

    def mark_prenav_scored(self, prenav_id: int) -> bool:
        """Mark a prenav submission as scored. Returns success."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE prenav_submissions SET status = 'scored' WHERE id = ?",
                (prenav_id,)
            )
            return cursor.rowcount > 0

    def archive_prenav(self, prenav_id: int) -> bool:
        """Archive a prenav submission (admin only). Returns success."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE prenav_submissions SET status = 'archived' WHERE id = ?",
                (prenav_id,)
            )
            return cursor.rowcount > 0

    def get_prenav_by_id(self, prenav_id: int) -> Optional[Dict]:
        """Get single prenav submission by ID with full details."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    ps.id, ps.pairing_id, ps.nav_id, ps.submitted_at, ps.status,
                    ps.pilot_id, ps.total_time, ps.fuel_estimate, ps.leg_times,
                    n.name as nav_name,
                    p.pilot_id, p.safety_observer_id,
                    pilot.name as pilot_name,
                    observer.name as observer_name
                FROM prenav_submissions ps
                JOIN navs n ON ps.nav_id = n.id
                JOIN pairings p ON ps.pairing_id = p.id
                JOIN users pilot ON p.pilot_id = pilot.id
                JOIN users observer ON p.safety_observer_id = observer.id
                WHERE ps.id = ?
            """, (prenav_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            prenav = dict(row)
            
            # Parse leg_times from JSON
            if prenav.get('leg_times'):
                try:
                    prenav['leg_times'] = json.loads(prenav['leg_times'])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse leg_times for prenav {prenav_id}")
                    prenav['leg_times'] = []
            else:
                prenav['leg_times'] = []
            
            # Convert UTC timestamp to CST and add display fields
            cst = pytz.timezone('America/Chicago')
            timestamp_str = prenav.get('submitted_at')
            if timestamp_str:
                try:
                    utc_time = datetime.fromisoformat(timestamp_str)
                    utc_time = pytz.utc.localize(utc_time)
                    cst_time = utc_time.astimezone(cst)
                    prenav['submitted_at_display'] = cst_time.strftime('%b %d, %Y %I:%M %p')
                except Exception as e:
                    logger.warning(f"Failed to convert timestamp {timestamp_str}: {e}")
                    prenav['submitted_at_display'] = timestamp_str
            else:
                prenav['submitted_at_display'] = 'Unknown'
            
            # Format total_time for display
            total_time = prenav.get('total_time', 0)
            hours = int(total_time // 3600)
            minutes = int((total_time % 3600) // 60)
            seconds = int(total_time % 60)
            prenav['total_time_display'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            return prenav

    def delete_prenav_submission(self, prenav_id: int) -> bool:
        """Delete a pre-flight submission (admin only). Returns success."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM prenav_submissions WHERE id = ?', (prenav_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ===== FLIGHT RESULTS =====

    def create_flight_result(
        self,
        prenav_id: int,
        pairing_id: int,
        nav_id: int,
        gpx_filename: str,
        actual_fuel: float,
        secrets_checkpoint: int,
        secrets_enroute: int,
        start_gate_id: int,
        overall_score: float,
        checkpoint_results: List[Dict],
        leg_penalties: float = 0,
        total_time_penalty: float = 0,
        total_time_deviation: float = 0,
        estimated_total_time: float = 0,
        actual_total_time: float = 0,
        total_off_course: float = 0,
        fuel_error_pct: float = 0,
        estimated_fuel_burn: float = 0,
        checkpoint_radius: float = 0.25,
    ) -> int:
        """Create a flight result. Returns result ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO flight_results
                (prenav_id, pairing_id, nav_id, gpx_filename, actual_fuel,
                 secrets_missed_checkpoint, secrets_missed_enroute, start_gate_id,
                 overall_score, checkpoint_results, leg_penalties, total_time_penalty,
                 total_time_deviation, estimated_total_time, actual_total_time,
                 total_off_course, fuel_error_pct, estimated_fuel_burn, checkpoint_radius)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prenav_id,
                    pairing_id,
                    nav_id,
                    gpx_filename,
                    actual_fuel,
                    secrets_checkpoint,
                    secrets_enroute,
                    start_gate_id,
                    overall_score,
                    json.dumps(checkpoint_results),
                    leg_penalties,
                    total_time_penalty,
                    total_time_deviation,
                    estimated_total_time,
                    actual_total_time,
                    total_off_course,
                    fuel_error_pct,
                    estimated_fuel_burn,
                    checkpoint_radius,
                ),
            )
            return cursor.lastrowid

    def get_flight_result(self, result_id: int) -> Optional[Dict]:
        """Get flight result by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM flight_results WHERE id = ?", (result_id,))
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            result["checkpoint_results"] = json.loads(result["checkpoint_results"])
            return result

    def list_flight_results(
        self,
        pairing_id: Optional[int] = None,
        nav_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """List flight results with optional filters."""
        query = "SELECT * FROM flight_results WHERE 1=1"
        params = []

        if pairing_id:
            query += " AND pairing_id = ?"
            params.append(pairing_id)
        if nav_id:
            query += " AND nav_id = ?"
            params.append(nav_id)
        if start_date:
            query += " AND scored_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND scored_at <= ?"
            params.append(end_date)

        query += " ORDER BY scored_at DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result["checkpoint_results"] = json.loads(result["checkpoint_results"])
                results.append(result)
            return results

    def delete_flight_result(self, result_id: int) -> bool:
        """Delete a flight result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM flight_results WHERE id = ?", (result_id,))
            return cursor.rowcount > 0

    # ===== ACTIVITY LOGGING =====

    def log_activity(
        self,
        user_id: int,
        category: str,
        activity_type: str,
        details: str = None,
        entity_type: str = None,
        entity_id: int = None,
        ip_address: str = None,
    ) -> int:
        """
        Log user activity.
        
        Categories: 'auth', 'nav', 'flight', 'admin', 'pairing', 'user'
        Types: 'login', 'logout', 'create_nav', 'edit_nav', 'delete_nav',
               'submit_prenav', 'submit_postnav', 'create_pairing', etc.
        """
        with self.get_connection() as conn:
            # Get user info for logging
            user = self.get_user_by_id(user_id)
            user_email = user.get("email") if user else None
            user_name = user.get("name") if user else None
            
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activity_log 
                (user_id, user_email, user_name, activity_category, activity_type, 
                 activity_details, related_entity_type, related_entity_id, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_email,
                    user_name,
                    category,
                    activity_type,
                    details,
                    entity_type,
                    entity_id,
                    ip_address,
                ),
            )
            log_id = cursor.lastrowid
            logger.debug(
                f"Activity logged: user={user_id} category={category} type={activity_type}"
            )
            return log_id

    def get_activity_log(
        self,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        activity_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Get activity log entries with optional filters."""
        query = "SELECT * FROM activity_log WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if category:
            query += " AND activity_category = ?"
            params.append(category)
        if activity_type:
            query += " AND activity_type = ?"
            params.append(activity_type)
        if entity_type:
            query += " AND related_entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND related_entity_id = ?"
            params.append(entity_id)
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_activity_count(
        self,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> int:
        """Get total count of activity log entries."""
        query = "SELECT COUNT(*) FROM activity_log WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if category:
            query += " AND activity_category = ?"
            params.append(category)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    # ===== NAV ASSIGNMENT METHODS (Item 37) =====

    def create_assignment(
        self,
        nav_id: int,
        pairing_id: int,
        assigned_by: int,
        semester: str = None,
        notes: str = None
    ) -> Optional[int]:
        """Create a new NAV assignment. Returns assignment ID or None if duplicate."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO nav_assignments (nav_id, pairing_id, assigned_by, semester, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (nav_id, pairing_id, assigned_by, semester or "Spring 2026", notes))
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Duplicate assignment (same nav + pairing + semester)
            logger.warning(f"Duplicate assignment: NAV {nav_id} already assigned to pairing {pairing_id} in semester {semester}")
            return None
        except Exception as e:
            logger.error(f"Error creating assignment: {e}")
            return None

    def get_assignments_for_pairing(
        self,
        pairing_id: int,
        completed: Optional[bool] = None,
        semester: str = None
    ) -> List[Dict]:
        """Get all assignments for a pairing. Can filter by completed status and semester."""
        query = """
            SELECT 
                a.id,
                a.nav_id,
                a.pairing_id,
                a.assigned_at,
                a.assigned_by,
                a.completed_at,
                a.semester,
                a.notes,
                n.name as nav_name,
                n.airport_id,
                ap.code as airport_code,
                u.name as assigned_by_name
            FROM nav_assignments a
            JOIN navs n ON a.nav_id = n.id
            JOIN airports ap ON n.airport_id = ap.id
            LEFT JOIN users u ON a.assigned_by = u.id
            WHERE a.pairing_id = ?
        """
        params = [pairing_id]

        if completed is not None:
            if completed:
                query += " AND a.completed_at IS NOT NULL"
            else:
                query += " AND a.completed_at IS NULL"

        if semester:
            query += " AND a.semester = ?"
            params.append(semester)

        query += " ORDER BY a.assigned_at DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_assignments(
        self,
        completed: Optional[bool] = None,
        semester: str = None
    ) -> List[Dict]:
        """Get all assignments (admin view). Can filter by completed status and semester."""
        query = """
            SELECT 
                a.id,
                a.nav_id,
                a.pairing_id,
                a.assigned_at,
                a.assigned_by,
                a.completed_at,
                a.semester,
                a.notes,
                n.name as nav_name,
                n.airport_id,
                ap.code as airport_code,
                p.id as pairing_id,
                pilot.name as pilot_name,
                observer.name as observer_name,
                u.name as assigned_by_name
            FROM nav_assignments a
            JOIN navs n ON a.nav_id = n.id
            JOIN airports ap ON n.airport_id = ap.id
            JOIN pairings p ON a.pairing_id = p.id
            JOIN users pilot ON p.pilot_id = pilot.id
            JOIN users observer ON p.safety_observer_id = observer.id
            LEFT JOIN users u ON a.assigned_by = u.id
            WHERE 1=1
        """
        params = []

        if completed is not None:
            if completed:
                query += " AND a.completed_at IS NOT NULL"
            else:
                query += " AND a.completed_at IS NULL"

        if semester:
            query += " AND a.semester = ?"
            params.append(semester)

        query += " ORDER BY a.assigned_at DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_assignment(self, assignment_id: int) -> Optional[Dict]:
        """Get a single assignment by ID."""
        query = """
            SELECT 
                a.id,
                a.nav_id,
                a.pairing_id,
                a.assigned_at,
                a.assigned_by,
                a.completed_at,
                a.semester,
                a.notes,
                n.name as nav_name,
                n.airport_id,
                ap.code as airport_code,
                pilot.name as pilot_name,
                observer.name as observer_name,
                u.name as assigned_by_name
            FROM nav_assignments a
            JOIN navs n ON a.nav_id = n.id
            JOIN airports ap ON n.airport_id = ap.id
            JOIN pairings p ON a.pairing_id = p.id
            JOIN users pilot ON p.pilot_id = pilot.id
            JOIN users observer ON p.safety_observer_id = observer.id
            LEFT JOIN users u ON a.assigned_by = u.id
            WHERE a.id = ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (assignment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def mark_assignment_complete(self, assignment_id: int) -> bool:
        """Mark an assignment as completed."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE nav_assignments
                    SET completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (assignment_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking assignment complete: {e}")
            return False

    def get_assignment_by_prenav(self, prenav_id: int) -> Optional[Dict]:
        """Get assignment associated with a pre-nav submission."""
        query = """
            SELECT 
                a.id,
                a.nav_id,
                a.pairing_id,
                a.assigned_at,
                a.assigned_by,
                a.completed_at,
                a.semester,
                a.notes
            FROM nav_assignments a
            JOIN prenav_submissions p ON p.nav_id = a.nav_id AND p.pairing_id = a.pairing_id
            WHERE p.id = ? AND a.completed_at IS NULL
            LIMIT 1
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (prenav_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_assignment(self, assignment_id: int) -> bool:
        """Delete an assignment (admin only)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM nav_assignments WHERE id = ?", (assignment_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting assignment: {e}")
            return False

    def check_duplicate_assignment(
        self,
        nav_id: int,
        pairing_id: int,
        semester: str = None
    ) -> bool:
        """Check if an assignment already exists (including completed ones)."""
        query = """
            SELECT COUNT(*) FROM nav_assignments
            WHERE nav_id = ? AND pairing_id = ? AND semester = ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (nav_id, pairing_id, semester or "Spring 2026"))
            count = cursor.fetchone()[0]
            return count > 0
