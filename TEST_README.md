# Testing the NAV Scoring Foundation

This document explains how to test the foundation layer without needing the full web application.

## Quick Start

```bash
cd /home/michael/clawd/work/nav_scoring/
python test_foundation.py
```

## What Gets Tested

### Test 1: Database Initialization & CRUD
- ✅ Database schema initialization
- ✅ Create members (individuals)
- ✅ Create pairings (pilot + observer)
- ✅ Retrieve members and pairings
- ✅ List active members and pairings

**Tests:**
- Can we create "Alice Thompson" (pilot) and "Bob Chen" (observer)?
- Can we pair them together?
- Can we retrieve the pairing correctly?

### Test 2: Authentication
- ✅ Password hashing (bcrypt)
- ✅ Member login/logout
- ✅ Coach account initialization
- ✅ Coach login
- ✅ Token generation

**Tests:**
- Can Alice log in with the correct password?
- Does login fail with a wrong password?
- Can the coach log in?
- Can we generate secure tokens?

### Test 3: Pre-NAV Submission
- ✅ Create a test NAV and airport
- ✅ Create a pre-NAV submission (planning data)
- ✅ Retrieve submission by token
- ✅ Validate token expiry (48 hours)

**Tests:**
- Can Alice (pilot) submit pre-flight planning?
- Is the token generated correctly?
- Can we retrieve the submission by token?
- Do leg times and fuel estimates store correctly?

### Test 4: Scoring Engine
- ✅ Haversine distance (nautical miles)
- ✅ Bearing calculation
- ✅ Timing penalty scoring
- ✅ Off-course penalty scoring
- ✅ Fuel penalty scoring
- ✅ Secrets penalty scoring
- ✅ Overall score calculation

**Tests:**
- Can we calculate distance between San Francisco and San Jose (~40 NM)?
- Do leg time deviations get penalized correctly?
- Do off-course penalties scale from 0.25 NM to 5.0 NM?
- Do fuel penalties increase with error magnitude?
- Do secrets penalties match the config (20 pts for checkpoint, 10 pts for enroute)?

### Test 5: Flight Result Storage
- ✅ Create flight result in database
- ✅ Store GPX filename reference
- ✅ Store checkpoint results (JSON)
- ✅ Store overall score
- ✅ Retrieve results by pairing

**Tests:**
- Can we store a scored flight result?
- Are checkpoint details preserved in JSON?
- Can we retrieve results for a specific pairing?

## Expected Output

```
████████████████████████████████████████████████████████████
NAV SCORING FOUNDATION TEST SUITE
████████████████████████████████████████████████████████████

============================================================
TEST 1: DATABASE INITIALIZATION & CRUD
============================================================
INFO: ✅ Database initialized
INFO: ✅ Created member: alice (ID: 1)
INFO: ✅ Retrieved member: Alice Thompson (pilot_alice)
INFO: ✅ Created member: bob (ID: 2)
INFO: ✅ Created pairing: Alice Thompson (pilot) + Bob Chen (observer) (ID: 1)
INFO: ✅ Retrieved pairing: pilot_id=1, observer_id=2
INFO: ✅ Listed active members: 2 members found
INFO: ✅ Member Alice Thompson has 1 active pairing(s)

============================================================
TEST 2: AUTHENTICATION
============================================================
INFO: ✅ Password hashing and verification works
INFO: ✅ Set password for member: alice
INFO: ✅ Member login successful: Alice Thompson
INFO: ✅ Failed login rejected correctly
INFO: ✅ Coach account initialized
INFO: ✅ Coach login successful
INFO: ✅ Generated token: a1b2c3d4e5f6...

[... more test output ...]

████████████████████████████████████████████████████████████
✅ ALL TESTS PASSED
████████████████████████████████████████████████████████████

Foundation is solid and ready for API layer!
Test database: test_navs.db

To clean up: rm test_navs.db
```

## Troubleshooting

### ModuleNotFoundError: No module named 'pydantic'
```bash
pip install -r requirements.txt
```

### sqlite3.OperationalError: database is locked
Make sure no other process has the test database open. Try:
```bash
rm test_navs.db
python test_foundation.py
```

### AssertionError
Something didn't match expectations. The error message will tell you which test failed. Common issues:
- Database schema mismatch
- Auth logic incorrect
- Scoring calculation wrong

Check the error message and the relevant test function.

## After Tests Pass

Once all tests pass, you can:
1. ✅ Proceed to building the FastAPI web layer
2. ✅ Feel confident the foundation is solid
3. ✅ Know that members, pairings, prenav, and scoring all work

You can also:
- Inspect `test_navs.db` with SQLite browser to see the data
- Modify test values to verify edge cases
- Add more tests as needed

## Cleanup

```bash
rm test_navs.db
```

The test creates a temporary database. Delete it after testing.
