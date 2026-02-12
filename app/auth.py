"""
Authentication and session management for NAV Scoring system.
"""

import secrets
import logging
from typing import Optional
from passlib.context import CryptContext
from app.database import Database

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Auth:
    def __init__(self, db: Database):
        self.db = db

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(password, password_hash)

    # ===== MEMBER AUTHENTICATION =====

    def member_register(self, username: str, email: str, name: str, password: str) -> dict:
        """
        Register a new member account.
        Returns {"success": bool, "message": str, "member_id": int or None}
        """
        # Check if username exists
        existing = self.db.get_member_by_username(username)
        if existing:
            return {"success": False, "message": "Username already exists"}

        try:
            password_hash = self.hash_password(password)
            member_id = self.db.create_member(username, password_hash, email, name)
            logger.info(f"Member registered: {username}")
            return {
                "success": True,
                "message": "Registration successful",
                "member_id": member_id,
            }
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return {"success": False, "message": "Registration failed"}

    def member_login(self, username: str, password: str) -> dict:
        """
        Authenticate a member.
        Returns {"success": bool, "message": str, "member": dict or None}
        """
        member = self.db.get_member_by_username(username)
        if not member:
            logger.warning(f"Login attempt: user not found: {username}")
            return {"success": False, "message": "Invalid username or password"}

        if not member.get("is_active"):
            logger.warning(f"Login attempt: inactive member: {username}")
            return {"success": False, "message": "Account is inactive"}

        if not member.get("password_hash"):
            return {
                "success": False,
                "message": "Password not set. Contact coach to set initial password.",
            }

        if not self.verify_password(password, member["password_hash"]):
            logger.warning(f"Login attempt: wrong password: {username}")
            return {"success": False, "message": "Invalid username or password"}

        # Update last login
        self.db.update_member_last_login(member["id"])
        logger.info(f"Member logged in: {username}")

        return {
            "success": True,
            "message": "Login successful",
            "member": {
                "id": member["id"],
                "username": member["username"],
                "name": member["name"],
                "email": member["email"],
            },
        }

    def member_set_password(self, member_id: int, password: str) -> dict:
        """
        Set password for a member (first login or reset).
        Returns {"success": bool, "message": str}
        """
        try:
            password_hash = self.hash_password(password)
            success = self.db.update_member(member_id, password_hash=password_hash)
            if success:
                logger.info(f"Password set for member ID {member_id}")
                return {"success": True, "message": "Password updated"}
            else:
                return {"success": False, "message": "Member not found"}
        except Exception as e:
            logger.error(f"Password set error: {e}")
            return {"success": False, "message": "Failed to set password"}

    def member_change_password(self, member_id: int, old_password: str, new_password: str) -> dict:
        """
        Change password for a member.
        Returns {"success": bool, "message": str}
        """
        member = self.db.get_member_by_id(member_id)
        if not member:
            return {"success": False, "message": "Member not found"}

        if not self.verify_password(old_password, member["password_hash"]):
            logger.warning(f"Password change: wrong old password for member {member_id}")
            return {"success": False, "message": "Invalid old password"}

        password_hash = self.hash_password(new_password)
        success = self.db.update_member(member_id, password_hash=password_hash)
        if success:
            logger.info(f"Password changed for member {member_id}")
            return {"success": True, "message": "Password changed"}
        else:
            return {"success": False, "message": "Failed to change password"}

    # ===== COACH AUTHENTICATION =====

    def coach_init(self, username: str, email: str, password: str) -> dict:
        """
        Initialize coach account (one-time setup).
        Returns {"success": bool, "message": str}
        """
        coach = self.db.get_coach()
        if coach:
            return {"success": False, "message": "Coach account already exists"}

        try:
            password_hash = self.hash_password(password)
            success = self.db.init_coach(username, password_hash, email)
            if success:
                logger.info("Coach account initialized")
                return {"success": True, "message": "Coach account created"}
            else:
                return {"success": False, "message": "Failed to create coach account"}
        except Exception as e:
            logger.error(f"Coach init error: {e}")
            return {"success": False, "message": "Failed to create coach account"}

    def coach_login(self, username: str, password: str) -> dict:
        """
        Authenticate coach.
        Returns {"success": bool, "message": str, "coach": dict or None}
        """
        coach = self.db.get_coach()
        if not coach:
            logger.warning("Login attempt: no coach account exists")
            return {"success": False, "message": "Coach account not initialized"}

        if coach["username"] != username:
            logger.warning(f"Coach login: wrong username: {username}")
            return {"success": False, "message": "Invalid credentials"}

        if not self.verify_password(password, coach["password_hash"]):
            logger.warning("Coach login: wrong password")
            return {"success": False, "message": "Invalid credentials"}

        # Update last login
        self.db.update_coach_last_login()
        logger.info("Coach logged in")

        return {
            "success": True,
            "message": "Login successful",
            "coach": {
                "id": coach["id"],
                "username": coach["username"],
                "email": coach["email"],
                "is_admin": coach.get("is_admin", 0) == 1,
            },
        }

    def coach_change_password(self, old_password: str, new_password: str) -> dict:
        """
        Change coach password.
        Returns {"success": bool, "message": str}
        """
        coach = self.db.get_coach()
        if not coach:
            return {"success": False, "message": "Coach account not found"}

        if not self.verify_password(old_password, coach["password_hash"]):
            logger.warning("Coach password change: wrong old password")
            return {"success": False, "message": "Invalid old password"}

        password_hash = self.hash_password(new_password)
        success = self.db.update_coach_password(password_hash)
        if success:
            logger.info("Coach password changed")
            return {"success": True, "message": "Password changed"}
        else:
            return {"success": False, "message": "Failed to change password"}

    def coach_reset_member_password(self, member_id: int, new_password: str) -> dict:
        """
        Coach resets a member's password.
        Returns {"success": bool, "message": str}
        """
        member = self.db.get_member_by_id(member_id)
        if not member:
            return {"success": False, "message": "Member not found"}

        try:
            password_hash = self.hash_password(new_password)
            success = self.db.update_member(member_id, password_hash=password_hash)
            if success:
                logger.info(f"Coach reset password for member {member_id}")
                return {"success": True, "message": "Password reset"}
            else:
                return {"success": False, "message": "Failed to reset password"}
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return {"success": False, "message": "Failed to reset password"}

    # ===== TOKEN GENERATION =====

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_hex(length // 2)

    # ===== SESSION MANAGEMENT =====

    @staticmethod
    def create_session_token() -> str:
        """Create a session token."""
        return secrets.token_urlsafe(32)
