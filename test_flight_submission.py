#!/usr/bin/env python3
"""
Test script to verify flight submission fuel field handling.
Tests both the combined hidden field approach and separate inputs approach.
"""

import sys

# Test fuel parsing logic (mimicking what the server does)
def test_fuel_parsing():
    """Test the fuel field parsing logic from POST /flight."""
    print("Testing fuel field parsing...")
    
    test_cases = [
        {
            "name": "Combined hidden field (8.5 gallons)",
            "actual_fuel": 8.5,
            "actual_fuel_gallons": None,
            "actual_fuel_tenths": None,
            "expected": 8.5,
            "should_pass": True
        },
        {
            "name": "Separate inputs (8 gallons + 5 tenths)",
            "actual_fuel": None,
            "actual_fuel_gallons": "8",
            "actual_fuel_tenths": "5",
            "expected": 8.5,
            "should_pass": True
        },
        {
            "name": "Separate inputs as strings (12.3 gallons)",
            "actual_fuel": None,
            "actual_fuel_gallons": "12",
            "actual_fuel_tenths": "3",
            "expected": 12.3,
            "should_pass": True
        },
        {
            "name": "Missing tenths input",
            "actual_fuel": None,
            "actual_fuel_gallons": "8",
            "actual_fuel_tenths": None,
            "expected": None,
            "should_pass": False
        },
        {
            "name": "Empty string inputs",
            "actual_fuel": None,
            "actual_fuel_gallons": "",
            "actual_fuel_tenths": "",
            "expected": None,
            "should_pass": False
        },
        {
            "name": "Invalid gallons (101)",
            "actual_fuel": None,
            "actual_fuel_gallons": "101",
            "actual_fuel_tenths": "5",
            "expected": None,
            "should_pass": False
        },
        {
            "name": "Zero fuel (0 gallons, 0 tenths)",
            "actual_fuel": None,
            "actual_fuel_gallons": "0",
            "actual_fuel_tenths": "0",
            "expected": 0.0,
            "should_pass": True
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        actual_fuel = test["actual_fuel"]
        actual_fuel_gallons = test["actual_fuel_gallons"]
        actual_fuel_tenths = test["actual_fuel_tenths"]
        
        # Mimic server-side logic
        error = None
        result = None
        
        if actual_fuel is None:
            if actual_fuel_gallons and actual_fuel_tenths:
                try:
                    gallons = float(actual_fuel_gallons.strip())
                    tenths = float(actual_fuel_tenths.strip())
                    
                    # Validate ranges
                    if gallons < 0 or gallons > 99:
                        error = f"Gallons must be between 0 and 99, got {gallons}"
                    elif tenths < 0 or tenths > 9:
                        error = f"Tenths must be between 0 and 9, got {tenths}"
                    else:
                        result = gallons + (tenths / 10.0)
                except (ValueError, AttributeError) as e:
                    error = f"Invalid fuel values: {str(e)}"
            else:
                error = "Missing fuel values"
        else:
            result = actual_fuel
        
        # Check result
        test_passed = False
        if test["should_pass"]:
            test_passed = (error is None and result is not None and abs(result - test["expected"]) < 0.01)
        else:
            test_passed = (error is not None or result is None)
        
        status = "✓ PASS" if test_passed else "✗ FAIL"
        passed += 1 if test_passed else 0
        failed += 0 if test_passed else 1
        
        print(f"  {status}: {test['name']}")
        if not test_passed:
            print(f"    Expected: {test['expected']}, Got: {result}, Error: {error}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = test_fuel_parsing()
    sys.exit(0 if success else 1)
