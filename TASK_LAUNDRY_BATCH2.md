# Task: NAV Scoring Laundry List Batch 2

## Context
You are fixing the second batch of issues from Mike's laundry list for the nav_scoring application. First batch (items 1-9) is complete in v0.3.1. This is the remaining cleanup.

## Project Location
`/home/michael/clawd/work/nav_scoring/`

**Current version:** v0.3.1  
**Deployed at:** http://localhost:8000 (Docker container)  
**Admin login:** admin@siu.edu / admin123  
**GitHub repo:** https://github.com/adequatepilot/nav-scoring

## Architecture Quick Reference
- **Backend:** FastAPI (app/app.py)
- **Database:** SQLite with migrations (migrations/*.sql)
- **Templates:** templates/*.html (Jinja2)
- **Auth:** Session-based (app/auth.py)
- **Users:** Unified users table with role flags (is_coach, is_admin, is_approved, force_password_reset)

## Issues to Fix

### 13.1: Remove "(Issue 13)" text from edit user form
**File:** `templates/coach/edit_user.html`  
**Fix:** Change label text from "Force user to reset password on next login (Issue 13)" to just "Force user to reset password on next login"

### 13.2: Force password reset not actually working
**Current state:** Checkbox exists in edit user form, database column exists  
**Problem:** When force_password_reset=1, user can still login without being prompted to reset  
**Fix needed:**
1. After successful login, check if user.force_password_reset == 1
2. If yes, redirect to password reset page (create if doesn't exist: `/reset-password`)
3. After reset, set force_password_reset=0
4. User cannot access any other pages until password is reset

**Implementation:**
- Add middleware or login route check for force_password_reset
- Create `/reset-password` route and template
- Force redirect until password is changed
- Clear force_password_reset flag after successful reset

### 14: Clarify pairing deletion UI
**Current state:** Both "Delete Pairing" and "Break Pairing" exist, unclear what each does  
**Mike's question:** "I don't quite understand the difference... specifically regarding the overall repercussions/results"

**Fix:** Add tooltips or help text explaining:
- **Delete Pairing:** Permanently removes pairing record from database (use if pairing was created by mistake)
- **Break Pairing:** Marks pairing as inactive but preserves history (use if team is changing mid-season)

OR simplify to just one button ("Delete Pairing") if there's no actual functional difference currently.

**Check code first** to see what each actually does, then either:
- Add clear help text explaining the difference, OR
- Remove redundant option if they do the same thing

### 15: Pairing shows "Pilot:unknown" and "Observer:Unknown"
**Problem:** User is successfully placed in pairing (database shows pilot_id and observer_id correctly), but competitor dashboard displays "Pilot:unknown" and "Observer:Unknown"

**Likely cause:** Template rendering issue - probably looking up user by wrong field or missing JOIN in query

**Files to check:**
- `templates/competitor/dashboard.html` (pairing display section)
- `app/app.py` route that serves competitor dashboard (probably `/competitor/dashboard`)
- Query that fetches pairing data

**Fix:** Ensure pairing query properly JOINs with users table to get actual names:
```sql
SELECT p.*, 
       pilot.name as pilot_name, pilot.email as pilot_email,
       observer.name as observer_name, observer.email as observer_email
FROM pairings p
JOIN users pilot ON p.pilot_id = pilot.id
JOIN users observer ON p.observer_id = observer.id
WHERE p.pilot_id = ? OR p.observer_id = ?
```

### 16: Prenav input needs separate HH/MM/SS boxes per leg
**Current state:** Single text input per leg (probably MM:SS format)  
**Problem:** "They will screw up input otherwise"

**Fix:** Change prenav submission form to have 3 separate number inputs per leg:
- Hours (00-23, max 2 digits)
- Minutes (00-59, max 2 digits)
- Seconds (00-59, max 2 digits)

**Backend:** Combine HH:MM:SS into total seconds before storing (or store as formatted string, depending on current implementation)

**Files:**
- `templates/competitor/submit_prenav.html` (form inputs)
- `app/app.py` prenav submission route (combine inputs into proper format)

### 17: Prenav fuel to nearest 0.1 gallon
**Current state:** Probably integer or unspecified precision  
**Fix:** 
- Input field: `<input type="number" step="0.1" min="0" max="999.9">`
- Validation: Round to 1 decimal place
- Display: Show as "X.X gallons" (e.g., "52.5 gallons")

**Files:**
- `templates/competitor/submit_prenav.html`
- Backend validation in prenav submission route

### 18 & 18.1: View results shows error
**Current error:** `{"detail":"Error loading results: 'result' is undefined"}`

**Problem:** JavaScript error trying to access undefined 'result' variable

**Files to check:**
- `templates/competitor/results.html` (or wherever results viewer is)
- JavaScript that loads/displays results
- `/competitor/results` route (or similar)

**Likely causes:**
- API endpoint returning wrong data structure
- JavaScript expecting different field name
- Missing null check for empty results

**Fix:**
1. Check what data `/competitor/results` endpoint actually returns
2. Check JavaScript that processes response
3. Add proper null checks: `if (data && data.results) { ... }`
4. Add error handling for empty results case

### 19.1: Status column redundant, no auto-refresh after approval
**Current state:** Members page has both "Status" and "Approved" columns showing same info  
**Problem:** After clicking approve button, page must be manually refreshed to see status change

**Fix:**
1. **Remove redundant column** - Keep either Status OR Approved column (probably keep Status)
2. **Add auto-refresh** - After approve/deny button click:
   - AJAX call to backend
   - On success, update row in-place with JavaScript (no page reload)
   - Update status text directly: "Pending" → "Active"
   - Remove approve/deny buttons from that row
   - Show success toast/message

**Files:**
- `templates/coach/members.html` (remove column, add JavaScript)
- Approve endpoint already exists, just need to return success JSON

### 20: No error message when pairing fails
**Current state:** Duplicate pairing prevention works (users can only be in one pairing), but no feedback to user when it fails silently

**Fix:** 
- When pairing creation fails due to duplicate, return error message
- Display error message on page: "Cannot create pairing: [User Name] is already in an active pairing"
- Highlight which user is causing the conflict

**Files:**
- `app/app.py` pairing creation route
- `templates/coach/pairings.html` (add error message display area)

## Testing Checklist
After fixes:
- [ ] Edit user form shows correct label (no "Issue 13" text)
- [ ] Force password reset actually redirects on next login
- [ ] Pairing deletion has clear help text or simplified UI
- [ ] Pairing display shows actual pilot/observer names (not "unknown")
- [ ] Prenav form has separate HH/MM/SS inputs per leg
- [ ] Prenav fuel accepts decimal (0.1 precision)
- [ ] View results loads without error
- [ ] Members page has single status column (not duplicate)
- [ ] Approve button updates status without page refresh
- [ ] Failed pairing shows error message explaining why

## Workflow (CRITICAL)
1. Make all fixes
2. Test thoroughly (check each item above)
3. Update CHANGELOG.md with all changes
4. Run: `bash scripts/release.sh patch` (bumps to v0.3.2)
5. Docker rebuild: `cd /home/michael/clawd/work/nav_scoring && docker build -t nav-scoring:latest .`
6. Docker redeploy: `docker stop nav-scoring && docker rm nav-scoring && docker run -d --name nav-scoring -p 8000:8000 -v $(pwd)/database:/app/database nav-scoring:latest`
7. Test deployed version at http://localhost:8000
8. Report back with: version number, what was fixed, any issues encountered

## Git Commit Style
```
Fix laundry list batch 2 (items 13.1-20)

- Remove "(Issue 13)" text from edit user form
- Implement force password reset redirect on login
- Clarify pairing deletion UI with help text
- Fix "unknown" pairing display bug with proper JOIN
- Add separate HH/MM/SS inputs for prenav leg times
- Set fuel input to 0.1 gallon precision
- Fix results viewer undefined variable error
- Remove redundant status column, add auto-refresh on approve
- Add error message when pairing creation fails

Closes issues 13.1, 13.2, 14, 15, 16, 17, 18, 18.1, 19.1, 20
```

## Notes
- Mike is a pilot/instructor, not a developer - clarity matters
- Mobile-first design (test on small screens)
- SIU branding (dark gray navbar, maroon accents)
- This is for actual competition use - accuracy and UX are critical

Good luck!
