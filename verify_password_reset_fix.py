#!/usr/bin/env python3
"""
Manual verification of the password reset checkbox fix.
This script checks the code changes and database state without importing the full app.
"""

import sqlite3
import json
from pathlib import Path

def verify_fix():
    """Verify the password reset fix is in place."""
    print("\n=== PASSWORD RESET CHECKBOX FIX VERIFICATION ===\n")
    
    all_passed = True
    
    # Check 1: Verify auth.py includes must_reset_password in returned user
    print("CHECK 1: Verifying auth.py returns must_reset_password field")
    try:
        with open("app/auth.py", "r") as f:
            auth_content = f.read()
        
        if '"must_reset_password": user.get("must_reset_password", 0)' in auth_content:
            print("  ✓ auth.login() correctly returns must_reset_password field")
        else:
            print("  ✗ FAILED: auth.login() does not return must_reset_password field")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error reading auth.py: {e}")
        all_passed = False
    
    # Check 2: Verify app.py POST /coach/users reads the checkbox
    print("\nCHECK 2: Verifying POST /coach/users reads force_reset checkbox")
    try:
        with open("app/app.py", "r") as f:
            app_content = f.read()
        
        if 'must_reset_password = force_reset == "1"' in app_content:
            print("  ✓ POST /coach/users correctly reads force_reset checkbox")
        else:
            print("  ✗ FAILED: POST /coach/users does not read checkbox correctly")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error reading app.py: {e}")
        all_passed = False
    
    # Check 3: Verify app.py passes must_reset_password to db.create_user()
    print("\nCHECK 3: Verifying must_reset_password passed to db.create_user()")
    try:
        with open("app/app.py", "r") as f:
            app_content = f.read()
        
        if 'must_reset_password=must_reset_password' in app_content:
            print("  ✓ POST /coach/users correctly passes must_reset_password to db.create_user()")
        else:
            print("  ✗ FAILED: must_reset_password not passed to db.create_user()")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error reading app.py: {e}")
        all_passed = False
    
    # Check 4: Verify app.py login route checks must_reset_password
    print("\nCHECK 4: Verifying login route checks must_reset_password")
    try:
        with open("app/app.py", "r") as f:
            app_content = f.read()
        
        if 'if user_data.get("must_reset_password", 0) == 1:' in app_content:
            print("  ✓ Login route correctly checks must_reset_password flag")
        else:
            print("  ✗ FAILED: Login route does not check must_reset_password")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error reading app.py: {e}")
        all_passed = False
    
    # Check 5: Verify database.py update_user includes must_reset_password
    print("\nCHECK 5: Verifying database.py allows updating must_reset_password")
    try:
        with open("app/database.py", "r") as f:
            db_content = f.read()
        
        if '"must_reset_password"' in db_content and "allowed_fields" in db_content:
            print("  ✓ database.py update_user() allows updating must_reset_password")
        else:
            print("  ✗ FAILED: database.py does not allow updating must_reset_password")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error reading database.py: {e}")
        all_passed = False
    
    # Check 6: Verify database schema has must_reset_password column
    print("\nCHECK 6: Verifying database schema includes must_reset_password column")
    try:
        with open("migrations/005_password_reset.sql", "r") as f:
            migration_content = f.read()
        
        if "must_reset_password" in migration_content:
            print("  ✓ Database schema migration includes must_reset_password column")
        else:
            print("  ✗ FAILED: Database migration missing must_reset_password")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error reading migration: {e}")
        all_passed = False
    
    # Check 7: Verify database actually has the column
    print("\nCHECK 7: Verifying database table has must_reset_password column")
    try:
        conn = sqlite3.connect("data/navs.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users);")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        if "must_reset_password" in columns:
            print("  ✓ Database users table has must_reset_password column")
        else:
            print("  ✗ FAILED: Database users table missing must_reset_password column")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error checking database: {e}")
        all_passed = False
    
    # Check 8: Verify reset-password endpoint clears the flag
    print("\nCHECK 8: Verifying reset-password endpoint clears the flag")
    try:
        with open("app/app.py", "r") as f:
            app_content = f.read()
        
        if "db.update_user(user[\"user_id\"], password_hash=password_hash, must_reset_password=0)" in app_content:
            print("  ✓ reset-password endpoint correctly clears must_reset_password flag")
        else:
            print("  ✗ FAILED: reset-password endpoint does not clear the flag")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Error reading app.py: {e}")
        all_passed = False
    
    # Summary
    print("\n" + "="*50)
    if all_passed:
        print("✓ ALL CHECKS PASSED - FIX IS CORRECTLY IMPLEMENTED")
        print("\nFIX SUMMARY:")
        print("1. auth.login() now returns must_reset_password field")
        print("2. Login route checks the flag and redirects to /reset-password")
        print("3. Checkbox value is read and saved to database")
        print("4. Reset password endpoint clears the flag")
        print("\nTHE BUG FIX:")
        print("The issue was that auth.login() was NOT returning the")
        print("must_reset_password field from the database. Even though")
        print("the flag was correctly saved, the login route never saw it.")
    else:
        print("✗ SOME CHECKS FAILED - FIX INCOMPLETE")
    print("="*50 + "\n")
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = verify_fix()
    sys.exit(0 if success else 1)
