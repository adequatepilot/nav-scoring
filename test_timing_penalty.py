"""
Test cases for total time penalty fix (v0.4.7)
Verifies that timing score includes both leg penalties and total time deviation penalty.
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_perfect_flight_perfect_math():
    """
    Test Case 1: Perfect flight, perfect math
    - All 5 legs: 1 second off each
    - Total ETE: 50:00 (5 * 10:00)
    - Total ATE: 49:59 (50:00 - 0:01 total deviation)
    - Expected leg penalties: 5 points (1 per leg)
    - Expected total time penalty: 1 point (|50:00 - 49:59|)
    - Expected total score: 6 points
    """
    print("\n=== Test 1: Perfect Flight, Perfect Math ===")
    
    # Simulate checkpoint results
    checkpoint_results = [
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 1.0},  # 10:00 actual vs 10:00 expected = 0
        {"actual_time": 599.0, "estimated_time": 600, "leg_score": 1.0},  # 9:59 actual vs 10:00 expected = -1
        {"actual_time": 601.0, "estimated_time": 600, "leg_score": 1.0},  # 10:01 actual vs 10:00 expected = +1
        {"actual_time": 599.0, "estimated_time": 600, "leg_score": 1.0},  # 9:59 actual vs 10:00 expected = -1
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 1.0},  # 10:00 actual vs 10:00 expected = 0
    ]
    
    # Calculate metrics
    leg_penalties = sum(cp["leg_score"] for cp in checkpoint_results)
    actual_total_time = sum(cp["actual_time"] for cp in checkpoint_results)
    estimated_total_time = 50 * 60  # 50:00 in seconds
    
    total_time_deviation = abs(estimated_total_time - actual_total_time)
    total_time_penalty = total_time_deviation * 1.0  # timing_penalty_per_second = 1.0
    total_time_score = leg_penalties + total_time_penalty
    
    print(f"Leg penalties:       {leg_penalties:.1f} pts")
    print(f"Actual total time:   {actual_total_time:.0f}s ({actual_total_time//60:.0f}:{actual_total_time%60:05.1f})")
    print(f"Estimated total:     {estimated_total_time:.0f}s ({estimated_total_time//60:.0f}:{estimated_total_time%60:05.1f})")
    print(f"Total time deviation: {total_time_deviation:.1f}s")
    print(f"Total time penalty:  {total_time_penalty:.1f} pts")
    print(f"TOTAL SCORE:         {total_time_score:.1f} pts")
    
    assert leg_penalties == 5.0, f"Expected 5 leg penalties, got {leg_penalties}"
    assert abs(actual_total_time - 2999) < 0.1, f"Expected actual_total_time ~2999s, got {actual_total_time}"
    assert total_time_deviation == 1.0, f"Expected 1s total deviation, got {total_time_deviation}"
    assert total_time_penalty == 1.0, f"Expected 1 point total time penalty, got {total_time_penalty}"
    assert total_time_score == 6.0, f"Expected total score of 6 pts, got {total_time_score}"
    
    print("✓ PASS\n")

def test_math_error_wrong_total():
    """
    Test Case 2: Math error - user enters wrong total
    - All 5 legs: correct (1 second off each) = 5 points
    - Leg ETEs sum to 50:00, but user types 51:00 (math error)
    - Actual total: 49:59
    - Expected leg penalties: 5 points
    - Expected total time penalty: |51:00 - 49:59| = 61 points
    - Expected total score: 66 points (penalized for bad math!)
    """
    print("=== Test 2: Math Error - Wrong Total ===")
    
    # Simulate checkpoint results (same as test 1)
    checkpoint_results = [
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 1.0},
        {"actual_time": 599.0, "estimated_time": 600, "leg_score": 1.0},
        {"actual_time": 601.0, "estimated_time": 600, "leg_score": 1.0},
        {"actual_time": 599.0, "estimated_time": 600, "leg_score": 1.0},
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 1.0},
    ]
    
    # Calculate metrics
    leg_penalties = sum(cp["leg_score"] for cp in checkpoint_results)
    actual_total_time = sum(cp["actual_time"] for cp in checkpoint_results)
    estimated_total_time = 51 * 60  # User entered 51:00 (WRONG! legs sum to 50:00)
    
    total_time_deviation = abs(estimated_total_time - actual_total_time)
    total_time_penalty = total_time_deviation * 1.0  # timing_penalty_per_second = 1.0
    total_time_score = leg_penalties + total_time_penalty
    
    print(f"Leg penalties:       {leg_penalties:.1f} pts")
    print(f"Actual total time:   {actual_total_time:.0f}s ({actual_total_time//60:.0f}:{actual_total_time%60:05.1f})")
    print(f"Estimated total:     {estimated_total_time:.0f}s ({estimated_total_time//60:.0f}:{estimated_total_time%60:05.1f}) ← USER INPUT (WRONG!)")
    print(f"Total time deviation: {total_time_deviation:.1f}s")
    print(f"Total time penalty:  {total_time_penalty:.1f} pts")
    print(f"TOTAL SCORE:         {total_time_score:.1f} pts")
    
    assert leg_penalties == 5.0, f"Expected 5 leg penalties, got {leg_penalties}"
    assert abs(actual_total_time - 2999) < 0.1, f"Expected actual_total_time ~2999s, got {actual_total_time}"
    assert total_time_deviation == 61.0, f"Expected 61s total deviation, got {total_time_deviation}"
    assert total_time_penalty == 61.0, f"Expected 61 point total time penalty, got {total_time_penalty}"
    assert total_time_score == 66.0, f"Expected total score of 66 pts, got {total_time_score}"
    
    print("✓ PASS\n")

def test_all_perfect():
    """
    Test Case 3: Everything perfect
    - All legs exactly on time
    - Total exactly on time
    - Expected total score: 0 points
    """
    print("=== Test 3: Everything Perfect ===")
    
    checkpoint_results = [
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 0.0},
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 0.0},
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 0.0},
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 0.0},
        {"actual_time": 600.0, "estimated_time": 600, "leg_score": 0.0},
    ]
    
    leg_penalties = sum(cp["leg_score"] for cp in checkpoint_results)
    actual_total_time = sum(cp["actual_time"] for cp in checkpoint_results)
    estimated_total_time = 50 * 60  # 50:00
    
    total_time_deviation = abs(estimated_total_time - actual_total_time)
    total_time_penalty = total_time_deviation * 1.0
    total_time_score = leg_penalties + total_time_penalty
    
    print(f"Leg penalties:       {leg_penalties:.1f} pts")
    print(f"Actual total time:   {actual_total_time:.0f}s ({actual_total_time//60:.0f}:{actual_total_time%60:05.1f})")
    print(f"Estimated total:     {estimated_total_time:.0f}s ({estimated_total_time//60:.0f}:{estimated_total_time%60:05.1f})")
    print(f"Total time deviation: {total_time_deviation:.1f}s")
    print(f"Total time penalty:  {total_time_penalty:.1f} pts")
    print(f"TOTAL SCORE:         {total_time_score:.1f} pts")
    
    assert leg_penalties == 0.0, f"Expected 0 leg penalties, got {leg_penalties}"
    assert total_time_deviation == 0.0, f"Expected 0s total deviation, got {total_time_deviation}"
    assert total_time_score == 0.0, f"Expected total score of 0 pts, got {total_time_score}"
    
    print("✓ PASS\n")

def test_leg_penalties_only():
    """
    Test Case 4: Legs off, but total math is correct
    - Each leg is 10 seconds off
    - Total is exactly correct (math was good)
    - Expected leg penalties: 5 * 10 = 50 points
    - Expected total time penalty: 0 (math correct!)
    - Expected total score: 50 points
    """
    print("=== Test 4: Leg Deviations but Correct Total ===")
    
    checkpoint_results = [
        {"actual_time": 610.0, "estimated_time": 600, "leg_score": 10.0},
        {"actual_time": 610.0, "estimated_time": 600, "leg_score": 10.0},
        {"actual_time": 610.0, "estimated_time": 600, "leg_score": 10.0},
        {"actual_time": 610.0, "estimated_time": 600, "leg_score": 10.0},
        {"actual_time": 610.0, "estimated_time": 600, "leg_score": 10.0},
    ]
    
    leg_penalties = sum(cp["leg_score"] for cp in checkpoint_results)
    actual_total_time = sum(cp["actual_time"] for cp in checkpoint_results)
    estimated_total_time = 50 * 60 + 50  # 50:50 (user did math correctly: 10:10 * 5)
    
    total_time_deviation = abs(estimated_total_time - actual_total_time)
    total_time_penalty = total_time_deviation * 1.0
    total_time_score = leg_penalties + total_time_penalty
    
    print(f"Leg penalties:       {leg_penalties:.1f} pts")
    print(f"Actual total time:   {actual_total_time:.0f}s ({int(actual_total_time//60)}:{int(actual_total_time%60)})")
    print(f"Estimated total:     {estimated_total_time:.0f}s ({int(estimated_total_time//60)}:{int(estimated_total_time%60)})")
    print(f"Total time deviation: {total_time_deviation:.1f}s")
    print(f"Total time penalty:  {total_time_penalty:.1f} pts")
    print(f"TOTAL SCORE:         {total_time_score:.1f} pts")
    
    assert leg_penalties == 50.0, f"Expected 50 leg penalties, got {leg_penalties}"
    assert total_time_deviation == 0.0, f"Expected 0s total deviation, got {total_time_deviation}"
    assert total_time_score == 50.0, f"Expected total score of 50 pts, got {total_time_score}"
    
    print("✓ PASS\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TIMING SCORE CALCULATION TESTS (v0.4.7)")
    print("="*60)
    
    try:
        test_perfect_flight_perfect_math()
        test_math_error_wrong_total()
        test_all_perfect()
        test_leg_penalties_only()
        
        print("="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60 + "\n")
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        exit(1)
