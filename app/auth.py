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

    # ===== UNIFIED USER AUTHENTICATION (NEW) =====

    def signup(self, email: str, name: str, password: str) -> dict:
        """
        Register a new user account via self-signup.
        Email must end with @siu.edu.
        Stores user in verification_pending table until email is verified.
        Returns {"success": bool, "message": str, "verification_token": str or None}
        """
        # Validate email domain
        if not email.endswith("@siu.edu"):
            return {"success": False, "message": "Email must end with @siu.edu"}

        # Check if email exists in users table
        existing = self.db.get_user_by_email(email)
        if existing:
            return {"success": False, "message": "Email already registered"}

        # Check if email is pending verification
        pending = self.db.get_verification_pending_by_email(email)
        if pending:
            return {"success": False, "message": "Email verification already pending. Check your email."}

        try:
            password_hash = self.hash_password(password)
            verification_token = self.generate_token()
            
            # Store in verification_pending table, not users table yet
            verification_id = self.db.create_verification_pending(
                email=email,
                password_hash=password_hash,
                name=name,
                verification_token=verification_token
            )
            
            logger.info(f"User registered (pending email verification): {email}")
            return {
                "success": True,
                "message": "Verification email sent. Check your inbox.",
                "verification_token": verification_token,
            }
        except Exception as e:
            logger.error(f"Signup error: {e}")
            return {"success": False, "message": "Registration failed"}
    
    def verify_email(self, verification_token: str) -> dict:
        """
        Verify user email and create user account.
        Returns {"success": bool, "message": str, "user_id": int or None}
        """
        try:
            # Look up token in verification_pending
            pending = self.db.get_verification_pending_by_token(verification_token)
            if not pending:
                return {"success": False, "message": "Invalid or expired verification link"}
            
            # Check if expired (24 hours)
            from datetime import datetime
            expires_at = datetime.fromisoformat(pending["expires_at"])
            if expires_at < datetime.utcnow():
                logger.warning(f"Verification token expired: {pending['email']}")
                # Delete expired entry
                self.db.delete_verification_pending(pending["id"])
                return {"success": False, "message": "Verification link has expired. Please sign up again."}
            
            # Create user in users table with is_approved=0, email_verified=1
            user_id = self.db.create_user(
                username=pending["email"],  # Use email as username
                password_hash=pending["password_hash"],
                email=pending["email"],
                name=pending["name"],
                is_coach=False,
                is_admin=False,
                is_approved=False,  # Pending admin approval
                email_verified=True
            )
            
            # Delete from verification_pending
            self.db.delete_verification_pending(pending["id"])
            
            logger.info(f"User email verified and account created (pending approval): {pending['email']}")
            return {
                "success": True,
                "message": "Email verified! Account created and awaiting admin approval.",
                "user_id": user_id,
            }
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return {"success": False, "message": "Verification failed"}

    def login(self, email: str, password: str) -> dict:
        """
        Authenticate a user by email (unified method for all roles).
        Returns {"success": bool, "message": str, "user": dict or None}
        """
        # Look up user by email
        user = self.db.get_user_by_email(email)
        if not user:
            logger.warning(f"Login attempt: user not found: {email}")
            return {"success": False, "message": "Invalid email or password"}

        # Check if email is verified
        if not user.get("email_verified"):
            logger.warning(f"Login attempt: email not verified: {email}")
            return {"success": False, "message": "Email not verified. Check your inbox for verification link."}

        # Check if account is approved
        if not user.get("is_approved"):
            logger.warning(f"Login attempt: account not approved: {email}")
            return {"success": False, "message": "Account pending approval. Contact admin."}

        if not user.get("password_hash"):
            return {
                "success": False,
                "message": "Password not set. Contact admin.",
            }

        if not self.verify_password(password, user["password_hash"]):
            logger.warning(f"Login attempt: wrong password: {email}")
            return {"success": False, "message": "Invalid email or password"}

        # Update last login
        self.db.update_user_last_login(user["id"])
        logger.info(f"User logged in: {email} (coach={user.get('is_coach')}, admin={user.get('is_admin')})")

        return {
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "is_coach": user.get("is_coach", 0) == 1,
                "is_admin": user.get("is_admin", 0) == 1,
                "is_approved": user.get("is_approved", 0) == 1,
                "must_reset_password": user.get("must_reset_password", 0) == 1,
            },
        }

    def approve_user(self, user_id: int) -> dict:
        """
        Approve a pending user account (admin only).
        Returns {"success": bool, "message": str}
        """
        try:
            success = self.db.approve_user(user_id)
            if success:
                logger.info(f"User approved: ID {user_id}")
                return {"success": True, "message": "User approved"}
            else:
                return {"success": False, "message": "User not found"}
        except Exception as e:
            logger.error(f"Approve user error: {e}")
            return {"success": False, "message": "Failed to approve user"}

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        """
        Change password for a user.
        Returns {"success": bool, "message": str}
        """
        user = self.db.get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": "User not found"}

        if not self.verify_password(old_password, user["password_hash"]):
            logger.warning(f"Password change: wrong old password for user {user_id}")
            return {"success": False, "message": "Invalid old password"}

        password_hash = self.hash_password(new_password)
        success = self.db.update_user(user_id, password_hash=password_hash)
        if success:
            logger.info(f"Password changed for user {user_id}")
            return {"success": True, "message": "Password changed"}
        else:
            return {"success": False, "message": "Failed to change password"}

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
