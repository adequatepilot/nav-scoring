# Task: NAV Scoring Laundry List Batch 4

## Context
Mike reports that issue 16.1/17.1 (prenav submission) is STILL broken even after v0.3.5 "fix". Code looks correct, but Mike can't submit the form. Also has 7 new issues to address.

## Project Location
`/home/michael/clawd/work/nav_scoring/`

**Current version:** v0.3.5  
**Deployed at:** http://localhost:8000 (Docker container)  
**Admin login:** admin@siu.edu / admin123  
**GitHub repo:** https://github.com/adequatepilot/nav-scoring

## CRITICAL: Verify Prenav Actually Works

**Before doing anything else**, test the prenav submission yourself:
1. Login as a test user with active pairing
2. Navigate to prenav form
3. Select a NAV route
4. Fill in leg times with HH/MM/SS inputs
5. Fill in fuel estimate
6. Click "Submit Pre-Flight Plan"
7. Verify you get token/confirmation (not "nothing happens")

If it doesn't work, debug why:
- Check browser console for JavaScript errors
- Check network tab for failed requests
- Test if event listener is actually attaching
- Check if there's a validation error not being displayed

**Do not report success unless you can personally complete the prenav workflow.**

## Issues to Fix

### 16.2/17.2: Prenav submission STILL broken (CRITICAL)
**Mike's report:** "16.1 still not resolved, persistent issue"

**Code appears correct** - event listener exists, AJAX submission implemented, form structure looks good.

**Possible causes:**
1. Browser cache (Mike might need hard refresh)
2. JavaScript error preventing listener from attaching
3. Validation failing silently
4. Different issue than what was "fixed"

**Your job:**
1. Test it yourself in the container (see above)
2. If broken, fix it for real this time
3. If working, document exact steps so Mike can reproduce
4. Consider adding debug logging or better error visibility

### 13.3: Auto-require password reset for new users
**Requirement:** When admin creates a new user, `must_reset_password` should default to 1 (checked).

**Implementation:**
- In user creation form: Make "Force password reset on next login" checkbox default to checked
- In database: When creating new user, set `must_reset_password = 1` by default
- Exception: Admin account should NOT be forced to reset

**Files:**
- `templates/coach/members.html` (create user form)
- `app/database.py` (create_user function)
- `app/app.py` (user creation route)

### 18.3: Simplify results page buttons
**Current:** Two buttons on results page  
**Required:** Single button "Return to Dashboard"

**Files:**
- `templates/competitor/results_list.html` (or whatever template shows results)

### 20.2: Improve pairing error message
**Current:** "Cannot create pairing: Error 409: Conflict"  
**Required:** "Cannot create pairing: [User Name] is already in an active pairing"

**The error message should:**
- Name which user is causing the conflict
- Explain what "conflict" means (already paired)
- Be friendly and actionable

**Files:**
- `app/database.py` (create_pairing error messages)
- `app/app.py` (pairing route error handling)

### 20.3: Success message for pairing creation
**Requirement:** When pairing created successfully, show green confirmation message: "Pairing created successfully: [Pilot Name] paired with [Observer Name]"

**Implementation:**
- Backend returns success message with names
- Frontend displays green success banner (auto-hide after 3 seconds)
- Success message scrolls to top for visibility

**Files:**
- `app/app.py` (pairing creation route - return success message)
- `templates/coach/pairings.html` (display success message)

### 21: User profile editing (NEW FEATURE)
**Requirements:**
- Users can edit their own profile (separate from admin editing users)
- Profile page accessible from dashboard (new "Profile" link in navbar)
- Features:
  - Reset own password (current + new + confirm)
  - Add additional email addresses (send notifications to ALL emails)
  - Upload profile picture (store in database/filesystem)
  - Future-proof for other settings

**Implementation scope:**
- Create `/profile` route and template
- Add "Profile" link to navbar
- Password change form with validation
- Email management (add/remove additional emails)
- Profile picture upload (basic implementation)

**Database changes:**
- May need new table: `user_emails` (user_id, email, is_primary)
- May need column: `users.profile_picture_path`

**Files to create/modify:**
- `templates/competitor/profile.html` (new)
- `app/app.py` (add /profile route)
- Database migration for new columns/tables
- File upload handling for profile pictures

### 22: Display profile pictures on dashboard (NEW FEATURE)
**Requirements:**
- On team dashboard, show profile pictures:
  - User's own picture (right side of pairing info)
  - Paired partner's picture (if in active pairing)
- Pictures should be circular thumbnails
- Fallback to initials if no picture uploaded

**Implementation:**
- Add profile picture to dashboard template
- CSS for circular image display
- Fallback to initials in colored circle (like Google)

**Files:**
- `templates/competitor/dashboard.html` (add image display)
- CSS for profile picture styling
- Helper function for initials fallback

## Testing Checklist
- [ ] **CRITICAL:** Prenav submission actually works (test it yourself!)
- [ ] New users auto-require password reset
- [ ] Results page has single "Return to Dashboard" button
- [ ] Pairing error message is descriptive with user names
- [ ] Pairing success message appears and names both users
- [ ] Profile page accessible and functional
- [ ] Can change password from profile
- [ ] Can add additional email addresses
- [ ] Can upload profile picture
- [ ] Profile pictures display on dashboard
- [ ] Fallback initials work when no picture

## Workflow
1. **TEST PRENAV FIRST** - Don't proceed if you can't make it work yourself
2. Fix all issues
3. Test thoroughly (especially prenav end-to-end)
4. Update CHANGELOG.md
5. Run: `bash scripts/release.sh minor` (bumps to v0.4.0 due to new features)
6. Docker rebuild + redeploy
7. Test deployed version
8. Report back with: version number, what was fixed, prenav test results

## Priority Order
1. **16.2/17.2** - Prenav submission (BLOCKING)
2. **13.3** - Auto password reset for new users
3. **20.2/20.3** - Pairing error/success messages
4. **18.3** - Results button simplification
5. **21** - User profile page (new feature, may take time)
6. **22** - Profile pictures (depends on #21)

## Notes
- Items 21 & 22 are NEW FEATURES, not bugs - may take longer
- Mike is testing on iPhone - mobile matters
- Don't claim prenav is fixed unless you can personally complete the workflow
- Consider bumping to v0.4.0 (minor version) due to new profile features

**BE THOROUGH. Mike is frustrated that prenav still doesn't work. Test it yourself before reporting success.**
