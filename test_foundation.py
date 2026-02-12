#!/usr/bin/env python3
"""
Test script for NAV Scoring foundation layer.
Tests: database, auth, models, scoring engine, email.
Run: python test_foundation.py
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import Database
from app.auth import Auth
from app.scoring_engine import NavScoringEngine
from app.email import EmailService

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test config
TEST_DB_PATH = "test_navs.db"
TEST_CONFIG = {
    "scoring": {
        "timing_penalty_per_second": 1.0,
        "off_course": {
            "max_no_penalty_nm": 0.25,
            "max_penalty_distance_nm": 5.0,
            "max_penalty_points": 500
        },
        "fuel_burn": {
            "over_estimate_multiplier": 500,
            "under_estimate_threshold": 0.1,
            "under_estimate_multiplier": 250
        },
        "secrets": {
            "checkpoint_penalty": 20,
            "enroute_penalty": 10,
            "max_distance_miles": 1.0
        }
    },
    "email": {
        "smtp_host": "smtp.zoho.com",
        "smtp_port": 587,
        "sender_email": "test@example.com",
        "sender_password": "test_password",
        "sender_name": "Test NAV Scoring",
        "recipients_coach": "coach@example.com"
    }
}

def test_database():
    """Test database initialization and CRUD operations."""
    print("\n" + "="*60)
    print("TEST 1: DATABASE INITIALIZATION & CRUD")
    print("="*60)
    
    # Clean up old test DB
    Path(TEST_DB_PATH).unlink(missing_ok=True)
    
    # Initialize
    db = Database(TEST_DB_PATH)
    logger.info("✅ Database initialized")
    
    # Test member creation
    member_id = db.create_member(
        username="pilot_alice",
        password_hash="hashed_password_123",
        email="alice@example.com",
        name="Alice Thompson"
    )
    logger.info(f"✅ Created member: alice (ID: {member_id})")
    
    # Test member retrieval
    member = db.get_member_by_id(member_id)
    assert member is not None
    assert member["username"] == "pilot_alice"
    logger.info(f"✅ Retrieved member: {member['name']} ({member['username']})")
    
    # Create second member for pairing
    member2_id = db.create_member(
        username="observer_bob",
        password_hash="hashed_password_456",
        email="bob@example.com",
        name="Bob Chen"
    )
    logger.info(f"✅ Created member: bob (ID: {member2_id})")
    
    # Test pairing creation
    pairing_id = db.create_pairing(pilot_id=member_id, safety_observer_id=member2_id)
    logger.info(f"✅ Created pairing: {member['name']} (pilot) + Bob Chen (observer) (ID: {pairing_id})")
    
    # Test pairing retrieval
    pairing = db.get_pairing(pairing_id)
    assert pairing is not None
    assert pairing["pilot_id"] == member_id
    assert pairing["safety_observer_id"] == member2_id
    logger.info(f"✅ Retrieved pairing: pilot_id={pairing['pilot_id']}, observer_id={pairing['safety_observer_id']}")
    
    # Test list active members
    active_members = db.list_active_members()
    assert len(active_members) == 2
    logger.info(f"✅ Listed active members: {len(active_members)} members found")
    
    # Test list pairings for member
    member_pairings = db.list_pairings_for_member(member_id, active_only=True)
    assert len(member_pairings) == 1
    logger.info(f"✅ Member {member['name']} has {len(member_pairings)} active pairing(s)")
    
    return db, member_id, member2_id, pairing_id

def test_auth(db):
    """Test authentication layer."""
    print("\n" + "="*60)
    print("TEST 2: AUTHENTICATION")
    print("="*60)
    
    auth = Auth(db)
    
    # Test password hashing
    password = "secure_password_123"
    hashed = auth.hash_password(password)
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("wrong_password", hashed)
    logger.info("✅ Password hashing and verification works")
    
    # Test member login
    # First, set a password for the test member
    test_member = db.get_member_by_username("pilot_alice")
    password = "alice_password_123"
    password_hash = auth.hash_password(password)
    db.update_member(test_member["id"], password_hash=password_hash)
    logger.info(f"✅ Set password for member: alice")
    
    # Now test login
    result = auth.member_login("pilot_alice", "alice_password_123")
    assert result["success"] == True
    assert result["member"]["username"] == "pilot_alice"
    logger.info(f"✅ Member login successful: {result['member']['name']}")
    
    # Test failed login
    result = auth.member_login("pilot_alice", "wrong_password")
    assert result["success"] == False
    logger.info("✅ Failed login rejected correctly")
    
    # Test coach account
    auth.coach_init("coach_mike", "coach@example.com", "coach_password_123")
    logger.info("✅ Coach account initialized")
    
    result = auth.coach_login("coach_mike", "coach_password_123")
    assert result["success"] == True
    logger.info("✅ Coach login successful")
    
    # Test token generation
    token = Auth.generate_token()
    assert len(token) > 0
    logger.info(f"✅ Generated token: {token[:16]}...")
    
    return auth

def test_prenav_submission(db, member_id, pairing_id):
    """Test pre-NAV submission creation."""
    print("\n" + "="*60)
    print("TEST 3: PRE-NAV SUBMISSION")
    print("="*60)
    
    # Create a NAV first (need to populate some reference data)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO airports (code) VALUES ('KMDH')")
        airport_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO navs (name, airport_id) VALUES (?, ?)",
            ("Test_NAV_01", airport_id)
        )
        nav_id = cursor.lastrowid
    logger.info("✅ Created test NAV and airport")
    
    # Create prenav submission
    token = Auth.generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=48)
    leg_times = [900, 1200, 800]  # 15min, 20min, 13min legs
    total_time = 2900.0  # 48min 20sec
    fuel_estimate = 8.5  # gallons
    
    prenav_id = db.create_prenav(
        pairing_id=pairing_id,
        pilot_id=member_id,
        nav_id=nav_id,
        leg_times=leg_times,
        total_time=total_time,
        fuel_estimate=fuel_estimate,
        token=token,
        expires_at=expires_at
    )
    logger.info(f"✅ Created prenav submission (ID: {prenav_id})")
    
    # Retrieve prenav
    prenav = db.get_prenav_by_token(token)
    assert prenav is not None
    assert prenav["pairing_id"] == pairing_id
    assert prenav["leg_times"] == leg_times
    logger.info(f"✅ Retrieved prenav by token: {prenav['leg_times']}")
    
    return nav_id, prenav_id, token

def test_scoring_engine():
    """Test scoring engine calculations."""
    print("\n" + "="*60)
    print("TEST 4: SCORING ENGINE")
    print("="*60)
    
    engine = NavScoringEngine(TEST_CONFIG)
    
    # Test haversine distance
    coord1 = {"lat": 37.7749, "lon": -122.4194}  # San Francisco
    coord2 = {"lat": 37.3382, "lon": -121.8863}  # San Jose
    distance = engine.haversine_distance(coord1, coord2)
    assert 30 < distance < 50  # ~40 NM
    logger.info(f"✅ Haversine distance: {distance:.2f} NM (SF to SJ)")
    
    # Test bearing calculation
    bearing = engine.calculate_bearing(coord1, coord2)
    assert 0 <= bearing <= 360
    logger.info(f"✅ Bearing calculation: {bearing:.1f}°")
    
    # Test timing penalty
    leg_score, off_course = engine.calculate_leg_score(
        actual_time=950,      # 15min 50sec (50sec over)
        estimated_time=900,   # 15min
        distance_nm=0.1,      # 0.1 NM off course
        within_025_nm=True
    )
    assert leg_score == 50  # 50 seconds * 1.0 penalty = 50 points
    assert off_course == 0  # Within 0.25 NM = no penalty
    logger.info(f"✅ Timing score: {leg_score} pts, Off-course: {off_course} pts")
    
    # Test fuel penalty (over-estimate)
    fuel_penalty = engine.calculate_fuel_penalty(
        estimated_fuel=8.0,
        actual_fuel=9.0  # Used 1 more gallon
    )
    assert fuel_penalty > 0
    logger.info(f"✅ Fuel penalty (over): {fuel_penalty:.1f} pts")
    
    # Test secrets penalty
    checkpoint_penalty, enroute_penalty = engine.calculate_secrets_penalty(
        missed_checkpoint=2,
        missed_enroute=1
    )
    assert checkpoint_penalty == 40  # 2 * 20
    assert enroute_penalty == 10     # 1 * 10
    logger.info(f"✅ Secrets penalties: checkpoint={checkpoint_penalty} pts, enroute={enroute_penalty} pts")
    
    # Test overall score calculation
    checkpoint_scores = [(50, 0), (40, 0), (30, 0)]  # 3 legs
    total_time_score = 100
    fuel_penalty = 25
    checkpoint_secrets = 40
    enroute_secrets = 10
    
    overall = engine.calculate_overall_score(
        checkpoint_scores=checkpoint_scores,
        total_time_score=total_time_score,
        fuel_penalty=fuel_penalty,
        checkpoint_secrets_penalty=checkpoint_secrets,
        enroute_secrets_penalty=enroute_secrets
    )
    expected = 50+40+30 + 100 + 25 + 40 + 10  # 295
    assert overall == expected
    logger.info(f"✅ Overall score: {overall} pts (lower is better)")

def test_flight_result(db, pairing_id, nav_id, prenav_id):
    """Test flight result storage."""
    print("\n" + "="*60)
    print("TEST 5: FLIGHT RESULT STORAGE")
    print("="*60)
    
    # Create a start gate for the NAV
    with db.get_connection() as conn:
        cursor = conn.cursor()
        airport_id = cursor.execute("SELECT airport_id FROM navs WHERE id = ?", (nav_id,)).fetchone()[0]
        cursor.execute(
            "INSERT INTO start_gates (airport_id, name, lat, lon) VALUES (?, ?, ?, ?)",
            (airport_id, "Runway 18L", 37.5495, -89.5666)
        )
        start_gate_id = cursor.lastrowid
    logger.info("✅ Created start gate")
    
    # Create flight result
    checkpoint_results = [
        {"name": "Checkpoint 1", "distance_nm": 0.1, "method": "CTP", "deviation": 30},
        {"name": "Checkpoint 2", "distance_nm": 0.2, "method": "Radius Entry", "deviation": -20},
        {"name": "Checkpoint 3", "distance_nm": 0.05, "method": "CTP", "deviation": 10},
    ]
    
    result_id = db.create_flight_result(
        prenav_id=prenav_id,
        pairing_id=pairing_id,
        nav_id=nav_id,
        gpx_filename="gpx_flight_20260210_001.gpx",
        actual_fuel=8.2,
        secrets_checkpoint=1,
        secrets_enroute=0,
        start_gate_id=start_gate_id,
        overall_score=245.5,
        checkpoint_results=checkpoint_results
    )
    logger.info(f"✅ Created flight result (ID: {result_id})")
    
    # Retrieve flight result
    result = db.get_flight_result(result_id)
    assert result is not None
    assert result["overall_score"] == 245.5
    assert len(result["checkpoint_results"]) == 3
    logger.info(f"✅ Retrieved flight result: score={result['overall_score']} pts")
    
    # Test list flight results for pairing
    results = db.list_flight_results(pairing_id=pairing_id)
    assert len(results) == 1
    logger.info(f"✅ Listed flight results: {len(results)} result(s) for pairing")

def main():
    """Run all tests."""
    print("\n" + "█"*60)
    print("NAV SCORING FOUNDATION TEST SUITE")
    print("█"*60)
    
    try:
        # Test 1: Database
        db, member_id, member2_id, pairing_id = test_database()
        
        # Test 2: Auth
        auth = test_auth(db)
        
        # Test 3: PreNav Submission
        nav_id, prenav_id, token = test_prenav_submission(db, member_id, pairing_id)
        
        # Test 4: Scoring Engine
        test_scoring_engine()
        
        # Test 5: Flight Result
        test_flight_result(db, pairing_id, nav_id, prenav_id)
        
        # Summary
        print("\n" + "█"*60)
        print("✅ ALL TESTS PASSED")
        print("█"*60)
        print("\nFoundation is solid and ready for API layer!")
        print(f"Test database: {TEST_DB_PATH}")
        print("\nTo clean up: rm test_navs.db")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
