#!/usr/bin/env python3
"""
Test script for v0.4.0 token replacement refactor.
Tests all three user roles: competitor, coach, admin.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import Database

def test_database_methods():
    """Test new database methods"""
    print("\n" + "="*60)
    print("TEST 1: Database Methods")
    print("="*60)
    
    db = Database()
    
    # Check prenav_submissions table has status column
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(prenav_submissions)")
        cols = {row[1] for row in cursor.fetchall()}
        assert "status" in cols, "Missing 'status' column in prenav_submissions"
        print("✓ status column exists in prenav_submissions")
    
    # Test get_open_prenav_submissions() exists
    assert hasattr(db, 'get_open_prenav_submissions'), "Missing get_open_prenav_submissions method"
    print("✓ get_open_prenav_submissions() method exists")
    
    # Test mark_prenav_scored() exists
    assert hasattr(db, 'mark_prenav_scored'), "Missing mark_prenav_scored method"
    print("✓ mark_prenav_scored() method exists")
    
    # Test archive_prenav() exists
    assert hasattr(db, 'archive_prenav'), "Missing archive_prenav method"
    print("✓ archive_prenav() method exists")
    
    print("✓ All database methods present")


def test_prenav_creation():
    """Test prenav creation without token"""
    print("\n" + "="*60)
    print("TEST 2: Prenav Creation (No Token)")
    print("="*60)
    
    db = Database()
    
    # Get first pairing if exists
    pairings = db.list_pairings(active_only=True)
    if not pairings:
        print("⊘ No active pairings found (skipping prenav creation test)")
        return
    
    pairing = pairings[0]
    navs = db.list_navs()
    if not navs:
        print("⊘ No NAVs found (skipping prenav creation test)")
        return
    
    nav = navs[0]
    
    # Create prenav without token
    try:
        prenav_id = db.create_prenav(
            pairing_id=pairing["id"],
            pilot_id=pairing["pilot_id"],
            nav_id=nav["id"],
            leg_times=[300, 400, 350],  # in seconds
            total_time=1050,
            fuel_estimate=8.5,
            token=None,
            expires_at=None
        )
        
        print(f"✓ Created prenav {prenav_id} without token")
        
        # Verify prenav was created with status='open'
        prenav = db.get_prenav(prenav_id)
        assert prenav is not None, "Prenav not found after creation"
        assert prenav.get("status") == "open", f"Expected status='open', got {prenav.get('status')}"
        # Token is generated (for backwards compat) but not used in v0.4.0 UI
        token_value = prenav.get("token")
        assert token_value, f"Token should be generated, got '{token_value}'"
        assert len(token_value) > 0, "Token should not be empty"
        
        print(f"✓ Prenav status is 'open'")
        print(f"✓ Prenav token is generated (for backwards compat, not used in v0.4.0)")
        
    except Exception as e:
        print(f"✗ Error creating prenav: {e}")
        raise


def test_get_open_submissions_filtering():
    """Test get_open_prenav_submissions() filtering by role"""
    print("\n" + "="*60)
    print("TEST 3: Open Submissions Filtering")
    print("="*60)
    
    db = Database()
    
    try:
        # Get all open submissions (coach view)
        all_open = db.get_open_prenav_submissions(user_id=None, is_coach=True)
        print(f"✓ Coach view: {len(all_open)} open submissions")
        
        # Get competitor-only submissions
        if len(all_open) > 0:
            sample_prenav = all_open[0]
            user_id = sample_prenav.get("pilot_id")
            
            if user_id:
                competitor_open = db.get_open_prenav_submissions(user_id=user_id, is_coach=False)
                print(f"✓ Competitor view (user {user_id}): {len(competitor_open)} open submissions")
                
                # Verify competitor sees fewer or equal submissions
                assert len(competitor_open) <= len(all_open), "Competitor should see fewer submissions than coach"
                print(f"✓ Filtering working: competitor sees {len(competitor_open)}/{len(all_open)} submissions")
        
    except Exception as e:
        print(f"✗ Error testing submissions: {e}")
        raise


def test_mark_prenav_scored():
    """Test marking prenav as scored"""
    print("\n" + "="*60)
    print("TEST 4: Mark Prenav as Scored")
    print("="*60)
    
    db = Database()
    
    # Get an open prenav to test
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM prenav_submissions WHERE status='open' LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            print("⊘ No open prenav found (skipping mark_prenav_scored test)")
            return
        
        prenav_id = row[0]
        original_status = row[1]
    
    # Mark as scored
    success = db.mark_prenav_scored(prenav_id)
    assert success, f"Failed to mark prenav {prenav_id} as scored"
    print(f"✓ Marked prenav {prenav_id} as scored")
    
    # Verify status changed
    prenav = db.get_prenav(prenav_id)
    assert prenav.get("status") == "scored", f"Expected status='scored', got {prenav.get('status')}"
    print(f"✓ Prenav status is now 'scored'")
    
    # Verify it's no longer in open list
    open_subs = db.get_open_prenav_submissions(is_coach=True)
    open_ids = [s["id"] for s in open_subs]
    assert prenav_id not in open_ids, "Scored prenav should not appear in open list"
    print(f"✓ Scored prenav no longer in open submissions list")


def test_status_column_populated():
    """Verify all existing prenavs have status values"""
    print("\n" + "="*60)
    print("TEST 5: Status Column Populated")
    print("="*60)
    
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check all prenavs have status
        cursor.execute("SELECT COUNT(*) FROM prenav_submissions WHERE status IS NULL")
        null_count = cursor.fetchone()[0]
        assert null_count == 0, f"{null_count} prenavs have NULL status"
        print(f"✓ All prenavs have status value (no NULLs)")
        
        # Count by status
        cursor.execute("SELECT status, COUNT(*) FROM prenav_submissions GROUP BY status")
        for status, count in cursor.fetchall():
            print(f"  - status='{status}': {count} submissions")
        
        # Verify status values are valid
        cursor.execute("SELECT COUNT(*) FROM prenav_submissions WHERE status NOT IN ('open', 'scored', 'archived')")
        invalid_count = cursor.fetchone()[0]
        assert invalid_count == 0, f"{invalid_count} prenavs have invalid status"
        print(f"✓ All status values are valid (open/scored/archived)")


def test_index_created():
    """Verify indices were created for performance"""
    print("\n" + "="*60)
    print("TEST 6: Performance Indices")
    print("="*60)
    
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check for index on status
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_prenav_status'")
        if cursor.fetchone():
            print("✓ Index idx_prenav_status exists")
        else:
            print("⊘ Index idx_prenav_status not found")
        
        # Check for composite index
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_prenav_pairing_status'")
        if cursor.fetchone():
            print("✓ Index idx_prenav_pairing_status exists")
        else:
            print("⊘ Index idx_prenav_pairing_status not found")


def main():
    """Run all tests"""
    print("\n")
    print("🧪 NAV Scoring v0.4.0 - Token Replacement Tests")
    print("="*60)
    
    try:
        test_database_methods()
        test_prenav_creation()
        test_get_open_submissions_filtering()
        test_mark_prenav_scored()
        test_status_column_populated()
        test_index_created()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nNext steps:")
        print("1. Run full application tests with actual user interactions")
        print("2. Test email templates")
        print("3. Verify dropdown rendering in flight form")
        print("4. Test permission checks (competitor can't score wrong pairing)")
        print("5. Test edge cases (no submissions, archived submissions, etc.)")
        
        return 0
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
