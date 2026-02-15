# Test Plan: Token Replacement with Selection List v0.4.0

## Overview
Replace token-based prenav/postnav linking with selection list system. Test all user roles (competitor, coach, admin).

## Database Setup
- ✅ Migration 008 applied: `status` column added to `prenav_submissions`
- ✅ Existing submissions marked: scored/open based on flight_results
- ✅ Indices created for faster queries

## Test Scenarios

### Test 1: Competitor Workflow
**Goal**: Verify competitor can submit prenav, see only own submissions, and score with dropdown

1. **Login as Competitor** (pilot_id)
   - Navigate to `/prenav`
   - Should see: Own pairing info + NAV selector + leg times + fuel input

2. **Submit Pre-Flight Plan**
   - Select NAV route
   - Enter leg times (HH:MM:SS format)
   - Enter total time
   - Enter fuel estimate
   - Click Submit
   - Expected: Redirected to confirmation page
   - Expected: No token displayed in UI
   - Expected: Shows submission details (date, NAV, pilot, observer)
   - Expected: Email received without token

3. **Navigate to Post-Flight Form** (`/flight`)
   - Expected: Dropdown showing open submissions
   - Expected: Should see ONLY OWN submissions (not other pairings)
   - Expected: Dropdown shows: "Date - NAV - Pilot (Pilot) + Observer (Observer)"

4. **Submit Post-Flight (Score)**
   - Select own submission from dropdown
   - Select start gate
   - Upload GPX file
   - Enter actual fuel, secrets missed
   - Submit
   - Expected: Flight result created
   - Expected: Prenav marked as 'scored' (status='scored')
   - Expected: Same submission no longer appears in dropdown

5. **Verify Permissions**
   - Competitor should NOT be able to score another pairing's submission
   - Expected: Error "You are not authorized to score this submission"

### Test 2: Coach Workflow
**Goal**: Verify coach sees all submissions and can score any submission

1. **Login as Coach**
   - Navigate to `/prenav`
   - Should see: Pairing dropdown + NAV selector + form fields
   - Can submit for ANY pairing

2. **Navigate to Post-Flight Form** (`/flight`)
   - Expected: Dropdown showing ALL open submissions
   - Expected: See submissions from multiple pairings
   - Expected: Can select and score any submission

3. **Score Submission**
   - Select ANY pairing's submission
   - Complete and submit post-flight
   - Expected: Submission marked as 'scored'
   - Expected: Status='scored' prevents re-scoring

### Test 3: Admin Workflow
**Goal**: Verify admin has same permissions as coach + archive capability

1. **Login as Admin**
   - All coach permissions apply
   - Can see all submissions
   - Can score any submission

2. **Archive Function** (Future: `/coach/prenav/<id>/archive`)
   - Submit prenav
   - Mark as 'archived'
   - Expected: No longer appears in dropdown
   - Expected: Status='archived'

### Test 4: Edge Cases

#### 4.1: No Open Submissions
- Competitor submits prenav
- Before scoring it, delete the prenav or mark as archived
- Navigate to `/flight`
- Expected: Dropdown shows message "No open pre-flight submissions found"
- Expected: Can't submit empty form

#### 4.2: Can't Score Twice
- Submit flight and score prenav (status -> 'scored')
- Try to submit again with same prenav_id
- Expected: Error "This submission has already been scored or archived"

#### 4.3: Archived Submissions
- Prenav status='archived'
- Try to score it
- Expected: Error "This submission has already been scored or archived"

#### 4.4: Permission Violation
- Competitor A submits prenav
- Competitor B tries to score Competitor A's prenav
- Expected: Error "You are not authorized to score this submission"

### Test 5: Email Templates

#### 5.1: Pre-Flight Confirmation Email
- Should NOT contain token
- Should show submission details:
  - NAV Route
  - Submission Date/Time
  - Pilot Name
  - Observer Name
- Should instruct to "select from dropdown" when submitting post-flight

#### 5.2: Post-Flight Results Email
- Existing format should work
- Should reference the submission that was just scored

## Database Validation

After running tests, validate database state:

```sql
-- Check status values are correct
SELECT id, pairing_id, status, token FROM prenav_submissions;

-- Verify status='open' submissions don't have associated flight_results
SELECT ps.id, ps.status, COUNT(fr.id) as results_count
FROM prenav_submissions ps
LEFT JOIN flight_results fr ON ps.id = fr.prenav_id
GROUP BY ps.id;

-- Verify no orphaned 'scored' without flight_results
SELECT ps.id, ps.status
FROM prenav_submissions ps
LEFT JOIN flight_results fr ON ps.id = fr.prenav_id
WHERE ps.status = 'scored' AND fr.id IS NULL;
```

## Code Changes Summary

| File | Changes |
|------|---------|
| `migrations/008_prenav_status.sql` | NEW - Add status column |
| `app/database.py` | Updated `create_prenav()`, added `get_open_prenav_submissions()`, `mark_prenav_scored()`, `archive_prenav()` |
| `app/app.py` | `/prenav` POST, `/prenav_confirmation` GET, `/flight` GET/POST routes |
| `templates/team/flight.html` | Replaced token input with prenav dropdown |
| `templates/team/prenav_confirmation.html` | Shows submission details instead of token |
| `app/email.py` | Updated `send_prenav_confirmation()` |
| `VERSION` | 0.4.0 |
| `CHANGELOG.md` | Documented breaking change |

## Success Criteria
- ✅ Competitors can submit prenav without seeing token
- ✅ Competitors see only own submissions in dropdown
- ✅ Coaches/Admins see all submissions
- ✅ Can't score same submission twice
- ✅ Can't score wrong pairing (permissions)
- ✅ Email templates updated (no token)
- ✅ Database status tracking working
- ✅ All three user roles work correctly

## Deployment Steps
1. Run migration 008 ✓
2. Deploy updated code
3. Test with actual users
4. Monitor for errors
5. Commit to GitHub with tag v0.4.0

## Rollback Plan
If issues found:
1. Keep migration (safe - only adds columns)
2. Revert app code to v0.3.11
3. Routes will still work (token validation)
4. Can re-migrate at later time
