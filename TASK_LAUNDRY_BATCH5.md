# Task: NAV Scoring Laundry List Batch 5

## Context
Mike is VERY frustrated. Prenav submission has been "fixed" 4 times and still doesn't work. This time we need to get it right.

## Project Location
`/home/michael/clawd/work/nav_scoring/`

**Current version:** v0.4.0  
**Deployed at:** http://localhost:8000 (Docker container)  
**Admin login:** admin@siu.edu / admin123  
**Test users:** pilot1@siu.edu / pass123, observer1@siu.edu / pass123  
**GitHub repo:** https://github.com/adequatepilot/nav-scoring

## MANDATORY FIRST STEP: TEST PRENAV YOURSELF

**DO NOT PROCEED UNTIL YOU CAN COMPLETE THIS WORKFLOW:**

1. Login as **pilot1@siu.edu / pass123** (already paired with observer1)
2. Click "Submit Pre-Flight Plan" on dashboard
3. Select a NAV route from dropdown
4. Fill in HH/MM/SS inputs for each leg (e.g., 00:05:30 for each leg)
5. Fill in total flight time (MM:SS format, e.g., 48:30)
6. Fill in fuel estimate (e.g., 52.5)
7. Click "Submit Pre-Flight Plan" button
8. **VERIFY:** You get redirected to confirmation page with 48-hour token
9. **VERIFY:** Token is visible and can be copied

**If ANY step fails, debug until it works. Use browser console, network tab, add logging.**

**Document EXACT steps that work so Mike can follow them.**

## Issues to Fix

### 16.3/17.3: Prenav submission STILL broken (4th time reported)
**Mike's frustration level:** Maximum - "Still persisting, what gives"

**This has been "fixed" 4 times:**
- v0.3.5: Removed HTML5 required attributes, added AJAX
- v0.4.0: (supposedly working according to sub-agent)
- Mike: Still doesn't work

**Debugging approach:**
1. Test it yourself FIRST (see mandatory step above)
2. If broken, add verbose console logging at every step
3. Check if JavaScript is even loading
4. Check if event listener is attaching
5. Check if form validation is passing
6. Check if AJAX call is being made
7. Check if backend route is being hit
8. Check backend logs for errors

**Possible causes (new theories):**
- Browser cache issue (Mike might need hard refresh)
- Mobile vs desktop difference (Mike tests on iPhone)
- JavaScript syntax error preventing listener from attaching
- Race condition with dynamic field generation
- Backend route changed but frontend still calling old URL
- Session issue preventing POST

**Your job:**
1. Make it work in YOUR testing
2. Add better error visibility (show ALL validation errors on screen)
3. Add loading spinner during submission
4. Add debug mode that logs every step
5. Write EXACT steps for Mike to test

### 21.1: Password reset in user profile doesn't work
**Problem:** User fills out password reset form (current + new + confirm), submits, but old password still works and new password doesn't. No confirmation message shown.

**Expected behavior:**
1. User enters current password correctly
2. User enters new password (twice for confirmation)
3. Clicks "Update Password"
4. Password is actually changed in database
5. Old password no longer works
6. New password works
7. Green success message: "Password updated successfully"

**Files to check:**
- `/profile` route in `app/app.py`
- Password update logic in `app/database.py`
- `templates/competitor/profile.html` (form + error display)

**Test yourself:**
1. Login as pilot1@siu.edu / pass123
2. Go to Profile
3. Current password: pass123
4. New password: newpass123
5. Submit
6. Logout
7. Try logging in with newpass123 (should work)
8. Try logging in with pass123 (should fail)

### 20.2: Pairing error message not descriptive
**Current:** "Cannot create pairing: Error 409: Conflict"  
**Required:** "Cannot create pairing: [User Name] is already in an active pairing"

**This was supposedly fixed in v0.3.5 and v0.4.0, but Mike says it's still showing the generic message.**

**Check:**
1. `app/database.py` - Does `create_pairing()` return descriptive error with user name?
2. `app/app.py` - Does pairing route pass through the error message correctly?
3. `templates/coach/pairings.html` - Does it display the error properly?

**Test:**
1. Login as admin
2. Try to pair someone who's already paired
3. Verify error message includes user's name

### 19.2: Profile shows "pending approval" for approved users
**Problem:** User profiles show "Account Status: Pending Approval" even when:
- User is approved in admin panel
- User created by bootstrap (should be auto-approved)
- User can already login and access the system

**Expected:**
- Approved users see: "Account Status: Active" (or "Approved")
- Pending users see: "Account Status: Pending Approval"
- Status should match what admin panel shows

**Files:**
- `templates/competitor/profile.html` (status display)
- Profile route in `app/app.py` (user data retrieval)
- Check `is_approved` field in database

**Test:**
1. Login as pilot1@siu.edu (bootstrap user, should be approved)
2. Check profile - should show "Active" not "Pending Approval"
3. Admin creates new user with approval checkbox checked
4. New user logs in, checks profile - should show "Active"

### 18.3: Results page has two buttons, should be one
**Current:** Two buttons on results page  
**Required:** Single button "Return to Dashboard"

**This is a simple UI fix.**

**Files:**
- `templates/competitor/results_list.html` (or wherever results are shown)
- Remove extra button, keep single "Return to Dashboard" button

## Testing Checklist (DO NOT SKIP)
- [ ] **CRITICAL:** Prenav submission works (YOU tested it, not just "looks right in code")
- [ ] Documented exact steps for Mike to test prenav
- [ ] Password reset actually changes password
- [ ] Password reset shows success/error messages
- [ ] Pairing error message includes user name (no generic "409 Conflict")
- [ ] Approved users see "Active" status on profile (not "Pending")
- [ ] Results page has single "Return to Dashboard" button
- [ ] All fixes tested on fresh database

## Workflow
1. **TEST PRENAV FIRST** - Don't move on until YOU can complete it
2. Fix all issues
3. Test each one yourself
4. Update CHANGELOG.md
5. Run: `bash scripts/release.sh patch` (bumps to v0.4.1)
6. Docker rebuild + redeploy
7. Test deployed version again
8. Write detailed test instructions for Mike
9. Report back

## Priority Order
1. **16.3/17.3** - Prenav (CRITICAL - Mike is frustrated)
2. **21.1** - Password reset (core functionality broken)
3. **20.2** - Pairing error message
4. **19.2** - Profile status display
5. **18.3** - Results button (cosmetic)

## Git Commit Style
```
Fix laundry list batch 5 (prenav submission + core bugs)

- FINALLY fix prenav submission (4th attempt - thoroughly tested)
- Fix password reset in user profile (was not updating database)
- Fix pairing error message to include user name
- Fix profile status showing "pending" for approved users
- Simplify results page to single "Return to Dashboard" button

Tested end-to-end with documented steps for Mike.

Closes issues 16.3, 17.3, 18.3, 19.2, 20.2, 21.1
```

## Notes
- Mike is testing on iPhone (mobile matters)
- This is the 4th time prenav has been reported as broken
- Don't report success unless YOU personally complete the workflow
- Write VERY detailed test steps for Mike (assume nothing)
- Consider adding debug mode to help troubleshoot

**BE THOROUGH. Mike's patience is running out with prenav. Make it work.**
