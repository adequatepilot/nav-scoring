"""
Test cases to verify NIFA scoring formula fixes.
Tests Issue 1: Off-Course Penalty and Issue 2: Fuel Penalty
"""

import math
from app.scoring_engine import NavScoringEngine


def test_off_course_penalties():
    """Test Issue 1: Off-Course Penalty Formula"""
    print("\n" + "="*60)
    print("TEST ISSUE 1: Off-Course Penalty Formula")
    print("="*60)
    
    # Config with checkpoint_radius = 0.25 NM (Red Book v0.4.6)
    config = {
        "scoring": {
            "checkpoint_radius_nm": 0.25,
            "timing_penalty_per_second": 1.0,
            "off_course": {
                "checkpoint_radius_nm": 0.25,
                "min_penalty": 100,
                "max_penalty": 600,
                "max_distance_nm": 5.0,
            },
            "fuel_burn": {
                "over_estimate_multiplier": 250,
                "under_estimate_multiplier": 500,
                "over_estimate_threshold": 0.1,
            },
            "secrets": {}
        }
    }
    
    engine = NavScoringEngine(config)
    
    test_cases = [
        (0.25, 0, "Within radius"),
        (0.26, 100, "At threshold"),
        (2.63, 350, "Halfway point"),
        (5.0, 600, "At max distance"),
    ]
    
    print("\nTest cases (expected vs actual):")
    print("-" * 60)
    
    all_passed = True
    for distance_nm, expected_penalty, description in test_cases:
        within_025_nm = distance_nm <= 0.25
        leg_score, actual_penalty = engine.calculate_leg_score(
            actual_time=0,
            estimated_time=0,
            distance_nm=distance_nm,
            within_025_nm=within_025_nm
        )
        
        # Round to nearest integer for comparison
        actual_penalty = round(actual_penalty)
        passed = actual_penalty == expected_penalty
        all_passed = all_passed and passed
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} | {distance_nm:5.2f} NM | Expected: {expected_penalty:3d} | "
              f"Got: {actual_penalty:3d} | {description}")
    
    return all_passed


def test_fuel_penalties():
    """Test Issue 2: Fuel Penalty Formula"""
    print("\n" + "="*60)
    print("TEST ISSUE 2: Fuel Penalty Formula")
    print("="*60)
    
    config = {
        "scoring": {
            "fuel_burn": {
                "over_estimate_multiplier": 250,  # Corrected from 500
                "under_estimate_multiplier": 500,  # Corrected from 250
                "over_estimate_threshold": 0.1,  # New: 10% threshold
            }
        }
    }
    
    engine = NavScoringEngine(config)
    
    test_cases = [
        # (estimated, actual, description, should_have_penalty)
        (10.0, 9.2, "8% under (< 10% threshold)", False),
        (10.0, 8.8, "12% under (> 10%, uses 500 multiplier)", True),
        (10.0, 10.1, "1% over (no threshold, uses 500 multiplier)", True),
    ]
    
    print("\nTest cases (expected behavior):")
    print("-" * 60)
    
    all_passed = True
    for estimated, actual, description, should_have_penalty in test_cases:
        penalty = engine.calculate_fuel_penalty(estimated, actual)
        has_penalty = penalty > 0
        passed = has_penalty == should_have_penalty
        all_passed = all_passed and passed
        
        status = "✓ PASS" if passed else "✗ FAIL"
        error_pct = abs(estimated - actual) / estimated * 100
        print(f"{status} | Est: {estimated:.1f}, Act: {actual:.1f} | "
              f"Error: {error_pct:5.1f}% | Penalty: {penalty:7.2f} | {description}")
    
    return all_passed


if __name__ == "__main__":
    test1_pass = test_off_course_penalties()
    test2_pass = test_fuel_penalties()
    
    print("\n" + "="*60)
    if test1_pass and test2_pass:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*60 + "\n")
