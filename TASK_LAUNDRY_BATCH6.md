# Task: NAV Scoring Laundry List Batch 6

## Context
Four remaining issues after v0.4.1 deployment. Two were supposedly "fixed" in previous batches but Mike says they're still broken.

## Project Location
`/home/michael/clawd/work/nav_scoring/`

**Current version:** v0.4.1  
**Deployed at:** http://localhost:8000 (Docker container)  
**Admin login:** admin@siu.edu / admin123  
**Test users:** pilot1@siu.edu / pass123, observer1@siu.edu / pass123  
**GitHub repo:** https://github.com/adequatepilot/nav-scoring

## Issues to Fix

### 19.3: Profile status STILL showing "pending approval" (2nd report)
**Mike's report:** "19.2 is still persisting"  
**Previously reported:** Fixed in v0.4.1  
**Current status:** Still broken

**Problem:** User profiles show "Account Status: Pending Approval" even when user is approved in admin panel.

**Debug steps:**
1. Login as pilot1@siu.edu / pass123
2. Go to Profile page
3. Check what "Account Status" displays
4. Check database: What is `is_approved` value for pilot1?
5. Check session: Does session contain `is_approved` field?
6. Check template: How does it determine status to display?

**Likely causes:**
- Session not updated with `is_approved` field (even though v0.4.1 claimed to fix this)
- Profile route not passing `is_approved` to template
- Template using wrong field name
- Database query returning wrong value

**Expected behavior:**
- Approved users (is_approved=1) see: "Account Status: Active"
- Pending users (is_approved=0) see: "Account Status: Pending Approval"

**Files to check:**
- `app/app.py` - Profile route and session creation
- `app/auth.py` - Login function (session data)
- `templates/competitor/profile.html` - Status display logic
- Database seeding - Verify pilot1 has is_approved=1

**Test:**
1. Login as pilot1@siu.edu / pass123
2. Navigate to /profile
3. Verify status shows "Active" (or "Approved"), NOT "Pending Approval"

### 20.4: Pairing error STILL showing "Error 409: Conflict" (2nd report)
**Mike's report:** "Still getting the error 409 message instead of something like 'pairing cannot be made user abc is already paired'"  
**Previously reported:** Fixed in v0.3.5 and v0.4.0  
**Current status:** Still broken

**Problem:** Generic "Error 409: Conflict" message instead of descriptive error with user name.

**Debug steps:**
1. Login as admin@siu.edu / admin123
2. Go to Pairings page
3. Try to pair someone who's already paired (e.g., pilot1 is already paired with observer1)
4. Check what error message displays
5. Check browser console/network tab for actual error response

**Likely causes:**
- Backend returns correct message but frontend displays generic one
- Frontend error handling strips out the detailed message
- JavaScript displays HTTP status instead of message body
- Error message format doesn't match what frontend expects

**Expected behavior:**
When trying to pair pilot1 (already paired), should show:
"Cannot create pairing: Alex Johnson is already in an active pairing"

**Files to check:**
- `app/app.py` - Pairing creation route (check what gets returned on conflict)
- `app/database.py` - create_pairing function (check error message format)
- `templates/coach/pairings.html` - JavaScript error handling (check if it's stripping the message)

**Test:**
1. Login as admin
2. Try to pair pilot1@siu.edu with observer3@siu.edu (pilot1 already paired)
3. Verify error message includes "Alex Johnson" (user's actual name)
4. Message should NOT be generic "Error 409: Conflict"

### 21.2: Password reset needs success/failure confirmation
**Status:** New requirement (21.1 was partially fixed)

**Problem:** Password reset works, but user gets no feedback on success or failure.

**Required behavior:**
- **On success:** Green message: "Password updated successfully"
- **On failure:** Red message with reason:
  - "Current password is incorrect"
  - "New passwords do not match"
  - "Password must be at least 8 characters"
  - etc.

**Implementation:**
1. Backend validates and returns success/error response
2. Frontend displays message (green for success, red for error)
3. Success message auto-hides after 3 seconds
4. Error message persists until dismissed or form resubmitted

**Files:**
- `app/app.py` - /profile POST route (return JSON with success/error)
- `templates/competitor/profile.html` - Add message display area and AJAX handling

**Test:**
1. Login as pilot1@siu.edu / pass123
2. Go to Profile
3. **Test success:** Current: pass123, New: newpass123, Confirm: newpass123
   - Should show green "Password updated successfully"
4. Logout and verify newpass123 works
5. Login again, go to Profile
6. **Test failure:** Current: wrongpass, New: anything, Confirm: anything
   - Should show red "Current password is incorrect"

### 16.4: Make HH/MM/SS input boxes slightly bigger
**Problem:** Input boxes are too small, cutting off placeholder text.

**Current:** Placeholder text like "HH" or "MM" or "SS" is partially hidden  
**Required:** Boxes wide enough to show full placeholder

**Implementation:**
Simple CSS fix in prenav form:
```css
input[type="number"].time-input {
    width: 50px;  /* or whatever width shows full placeholder */
}
```

**Files:**
- `templates/team/prenav.html` - Add CSS or inline styles to time input boxes

**Test:**
1. Login as pilot1@siu.edu / pass123
2. Go to prenav form
3. Select NAV-1
4. Check HH/MM/SS input boxes
5. Verify placeholder text (e.g., "00") is fully visible

## Testing Checklist
- [ ] Profile shows "Active" for approved users (not "Pending")
- [ ] Pairing error shows user name (not "Error 409: Conflict")
- [ ] Password reset shows green success message
- [ ] Password reset shows red error message with reason when it fails
- [ ] HH/MM/SS input boxes wide enough to show placeholders

## Workflow
1. Fix all issues
2. Test each one yourself (especially 19.3 and 20.4 which were previously "fixed")
3. Update CHANGELOG.md
4. Run: `bash scripts/release.sh patch` (bumps to v0.4.2)
5. Docker rebuild + redeploy
6. Test deployed version
7. Report back

## Priority Order
1. **19.3** - Profile status (user-facing, confusing)
2. **20.4** - Pairing error message (admin-facing, confusing)
3. **21.2** - Password confirmation (UX improvement)
4. **16.4** - Input box sizing (cosmetic)

## Git Commit Style
```
Fix laundry list batch 6 (status display + error messages)

- Fix profile status showing "pending" for approved users (19.3)
- Fix pairing error showing generic "409" instead of user name (20.4)
- Add success/failure messages for password reset (21.2)
- Increase HH/MM/SS input box width (16.4)

Issues 19.3 and 20.4 were previously reported as fixed but still broken.
Root cause identified and properly fixed this time.

Closes issues 16.4, 19.3, 20.4, 21.2
```

## Notes
- Issues 19.3 and 20.4 were reported as "fixed" but Mike says they're still broken
- This suggests the "fix" wasn't actually deployed or wasn't correct
- Double-check the actual deployed code, not just what's in git
- Test in the running container, not just local files
- Mike is testing on iPhone - check mobile display

**BE THOROUGH with 19.3 and 20.4 - they've been "fixed" before but still broken.**
