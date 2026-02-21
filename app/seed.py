"""
Seed database with default admin account on first run.
"""

import sqlite3
from pathlib import Path
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def seed_database():
    """Create default admin account if it doesn't exist."""
    db_path = Path("data/navs.db")
    
    if not db_path.exists():
        logger.warning("Database file not found - cannot seed")
        return
    
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        
        # Check if admin already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@siu.edu",))
        if cursor.fetchone():
            logger.info("Admin account already exists")
            return
        
        # Create admin account
        admin_password_hash = hash_password("admin123")
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, is_admin, is_approved, is_coach)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Main Administrator", "admin@siu.edu", admin_password_hash, 1, 1, 0)
        )
        
        conn.commit()
        logger.info("✅ Admin account created: admin@siu.edu / admin123")
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_database()
