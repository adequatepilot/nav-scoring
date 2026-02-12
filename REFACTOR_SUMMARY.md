# NAV Scoring System Refactor Summary

**Date:** February 12, 2026  
**Version:** 0.2.0 (Breaking Change)  
**Commit:** d7b6a0b

## Overview

Major refactoring of the NAV Scoring system to implement a unified user management system with role-based access control and self-signup with admin approval.

## Changes Made

### 1. Database Schema (Migration 003)

**New Table: `users`**
Unified user management table replacing the separate `members` and `coach` tables:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_coach INTEGER DEFAULT 0,        -- Coach dashboard access
    is_admin INTEGER DEFAULT 0,         -- Full CRUD permissions
    is_approved INTEGER DEFAULT 0,      -- Self-signup approval
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

**Old Tables:** `members` and `coach` retained for backward compatibility.

### 2. Authentication System (app/auth.py)

**New Methods:**
- `signup(username, email, name, password)` - Self-registration with @siu.edu validation
- `login(username, password)` - Unified login for all users
- `approve_user(user_id)` - Admin approval of pending accounts
- `change_password(user_id, old_password, new_password)` - User password management

**Removed:**
- `member_login()` - Replaced by unified `login()`
- `coach_login()` - Replaced by unified `login()`
- `member_register()` - Replaced by `signup()`
- `coach_init()` - Coaches created via `create_user()` in database

### 3. Database Layer (app/database.py)

**New Methods:**
- `create_user()` - Create user with role flags
- `get_user_by_username()`
- `get_user_by_id()`
- `get_user_by_email()`
- `list_users(filter_type)` - Filter: all, pending, coaches, admins, approved
- `update_user()` - Update user fields and roles
- `approve_user()` - Approve pending account
- `delete_user()`
- `update_user_last_login()`

**Improved:** Lazy database initialization to handle CIFS mount issues

### 4. Application Routes (app/app.py)

**Updated Routes:**
- `/` - Redirect to appropriate dashboard based on role
- `/login` - Unified login (updated form, no user_type selection needed)
- `/signup` (NEW) - Public self-signup form
- `/team` - Team member dashboard (require_member)
- `/prenav`, `/flight`, `/results` - Team routes (require_member)
- `/coach/*` - Coach dashboard routes (require_coach)
- `/coach/config` - Admin configuration (require_admin)

**New Permission Decorators:**
```python
require_login()      # Any logged-in user
require_member()     # Team members (is_coach=0)
require_coach()      # Coaches or admins (is_coach=1 or is_admin=1)
require_admin()      # Admins only (is_admin=1)
```

### 5. User Interface

**Updated Templates:**
- `login.html` - Simplified form, added signup link
- `signup.html` (NEW) - Self-signup form with @siu.edu validation
- `signup_confirmation.html` (NEW) - Confirmation after signup

**Missing UI Updates:**
The following would need implementation in the coach dashboard:
- `/coach/members` - Show all users with coach/admin checkboxes
- Pending user approval badge/count
- Approve/reject buttons for pending users

### 6. Data Management

**New Seed Data:**
- Admin account: `admin` / `admin123` (is_coach=1, is_admin=1)
- Coach account: `coach` / `coach123` (is_coach=1, is_admin=0)
- Test competitors: `pilot1-3` / `observer1-3` / `pass123`
- Pending user: `pending_user` / `pass123` (is_approved=0)

**Bootstrap Script:**
- `bootstrap_db.py` - Manually creates database schema for environments with CIFS mounting issues

### 7. Session Management

**Updated Session Storage:**
```python
request.session["user"] = {
    "user_id": int,
    "username": str,
    "name": str,
    "email": str,
    "is_coach": bool,      # NEW
    "is_admin": bool       # NEW
}
```

**Removed:** `user_type` field (now inferred from `is_coach` and `is_admin`)

## Key Features

### Self-Signup Workflow
1. User visits `/signup`
2. Enters username, email (@siu.edu required), full name, password
3. Account created with `is_approved=0`
4. Shows "Awaiting admin approval" message
5. Admin logs in and approves account in members list
6. User notified and can now login

### Role-Based Access Control
- **Competitor** (is_coach=0, is_admin=0)
  - Can submit flights via `/team`, `/prenav`, `/flight`
  - Can view own results
  - No access to `/coach`

- **Coach** (is_coach=1, is_admin=0)
  - Access to `/coach` dashboard (read-only)
  - Can view results, NAVs, members, pairings
  - Cannot create/edit resources (except as admin)

- **Admin** (is_admin=1)
  - Full CRUD access to all resources
  - Can approve/disapprove users
  - Can configure system settings
  - Can delete results, modify pairings
  - Can create/edit NAVs, checkpoints, secrets

### Backward Compatibility
- Old `members` and `coach` tables retained
- Existing pairings reference still work
- Migrations are additive (no data loss)

## Testing Checklist

- [ ] Database initializes without errors
- [ ] Admin can login with `admin` / `admin123`
- [ ] Admin dashboard accessible at `/coach`
- [ ] Competitor can login with `pilot1` / `pass123`
- [ ] Competitor dashboard accessible at `/team`
- [ ] Coach can login with `coach` / `coach123`
- [ ] Coach sees read-only `/coach` dashboard
- [ ] Signup form validates @siu.edu email
- [ ] Pending user cannot login
- [ ] Admin can approve pending user in members list
- [ ] After approval, pending user can login
- [ ] Permission checks block unauthorized access
- [ ] Session management works correctly
- [ ] Logout clears session

## Known Issues / Limitations

### CIFS Mount Issue
Development environments with CIFS mounts (network file systems) experience file locking issues with SQLite. This is why the application is designed to run in Docker for production.

**Workaround:**
- Run in Docker: `docker build -t nav-scoring:. && docker run -d ...`
- Or use local filesystem: `python3 bootstrap_db.py` then `uvicorn app.app:app`
- Or use different database backend (PostgreSQL, MySQL)

### UI Incomplete
Coach member approval UI not fully implemented:
- Members list needs checkboxes for coach/admin role assignment
- Pending approval badge not shown on dashboard
- Need admin interface to approve/reject users

These can be implemented in `/coach/members` template.

## Deployment

### Docker (Recommended)
```bash
docker build -t nav-scoring:latest .
docker run -d --name nav-scoring -p 8000:8000 nav-scoring:latest
docker exec nav-scoring python3 seed.py
```

### Local Development
```bash
pip install -r requirements.txt
python3 bootstrap_db.py
python3 seed.py
python3 -m uvicorn app.app:app --reload
```

See `SETUP.md` for detailed instructions.

## Files Modified

### Core Logic
- `app/auth.py` - Unified authentication system
- `app/database.py` - New user table methods
- `app/app.py` - Updated routes and decorators

### Database
- `migrations/003_unified_users.sql` - Create users table
- `bootstrap_db.py` - Manual schema creation tool

### UI
- `templates/login.html` - Simplified, added signup link
- `templates/signup.html` - New signup form
- `templates/signup_confirmation.html` - Signup confirmation
- `seed.py` - Updated for new users table

### Documentation
- `SETUP.md` - Setup and deployment instructions
- `REFACTOR_SUMMARY.md` - This file

## Next Steps

1. **Test the system thoroughly** with the testing checklist
2. **Implement missing UI** for user approval in `/coach/members`
3. **Add email notifications** when user accounts are approved
4. **Update admin dashboard** to show pending user count
5. **Migrate existing data** if upgrading from v0.1.x
6. **Deploy to production** using Docker
7. **Monitor logs** for any permission or authentication issues

## Version History

- **v0.2.0** (Feb 12, 2026) - Unified user system with roles and self-signup (BREAKING)
- **v0.1.1** (Previous) - Admin system and SMTP config
- **v0.1.0** (Initial) - Basic NAV scoring system
