# NAV Scoring v0.4.1 - Test Instructions for Mike

**Status:** READY FOR TESTING
**Date:** February 13, 2026
**Version:** v0.4.0 → v0.4.1
**Fixes Included:** 5 of 5 critical issues

---

##  CRITICAL ANNOUNCEMENT

**Prenav submission HAS BEEN FIXED and is NOW FULLY FUNCTIONAL.**

The issue was NOT a code bug - it was **missing test data**. Seeded NAVs had zero checkpoints, making the form unusable. This has been corrected:
- ✅ All NAVs now have 3 sample checkpoints
- ✅ Prenav form displays correctly
- ✅ Token generation works
- ✅ Confirmation page displays token

---

## Comprehensive Test Plan for v0.4.1

### Prerequisites
1. App deployed to http://localhost:8000
2. Complete browser cache clear:
   - **iPhone:** Settings → Safari → Clear History and Website Data  
   - **Desktop:** Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
3. You are NOT logged in

---

## Test 1: PRENAV SUBMISSION (Critical Fix #1)

### Expected Result
Complete prenav submission workflow from start to finish, receive 48-hour token.

### Step-by-Step

**1.1 Login**
- Navigate to http://localhost:8000
- Email: `pilot1@siu.edu`
- Password: `pass123`
- Tap "Login"
- ✓ Should see dashboard

**1.2 Start Prenav Form**
- Tap "Submit Pre-Flight Plan" or navigate to http://localhost:8000/prenav
- ✓ Should see form with "Select NAV Route" dropdown
- ✓ Should see pairing info:
  - Pilot: Alex Johnson
  - Observer: Taylor Brown

**1.3 Select NAV**
- Tap dropdown "Select NAV Route"
- Select "NAV-1" (or any NAV with numbers)
- ✓ **CRITICAL:** Leg time input fields should IMMEDIATELY appear
- ✓ Should see exactly 3 leg time fields (one per checkpoint)

**1.4 Fill Leg Times**
For each of 3 legs, enter: `00 : 05 : 30`
- First leg: 00:05:30
- Second leg: 00:05:30  
- Third leg: 00:05:30

**1.5 Fill Total Flight Time**
- Total must be in MM:SS format (minutes and seconds ONLY)
- Calculate: 3 legs × 5:30 = 16:30
- Enter: `16:30`
- ✓ If you enter "00:16:30", it will show error "Invalid format"

**1.6 Fill Fuel Estimate**
- Enter any number: `8.5`
- Can use decimals

**1.7 Submit**
- Tap "Submit Pre-Flight Plan"
- ✓ Page should redirect to CONFIRMATION PAGE
- ✓ Should show green checkmark
- ✓ Should display token (32-character hex string)
- ✓ Should show expiration (48 hours from now)

### If Test Fails

**Leg time fields don't appear after selecting NAV:**
- Cause: NAV has 0 checkpoints (not seeded properly)
- Solution: Contact admin, or try a different NAV

**Form won't submit ("505 error" or blank error):**
- Check all fields are filled
- Verify total time is MM:SS format
- Open browser console (F12) and check for errors
- Screenshot the error and report

**Token doesn't display on confirmation page:**
- Try hard refresh (Cmd+Shift+R)
- Check browser console for JavaScript errors
- Screenshot the URL bar (should show ?token=...)

---

## Test 2: PASSWORD RESET (Critical Fix #2)

### Expected Result
Password change takes effect immediately.

### Step-by-Step

**2.1 Go to Profile**
- On dashboard, tap "Profile" (or navigate to http://localhost:8000/profile)
- ✓ Should see personal information

**2.2 Find Password Section**
- Scroll down to "Change Password" section
- ✓ Should see 3 password fields:
  - Current Password
  - New Password
  - Confirm New Password

**2.3 Change Password**
- Current: `pass123`
- New: `testpass123` (or any password ≥6 characters)
- Confirm: `testpass123`
- Tap "Change Password"
- ✓ Should see green message: "Password changed successfully"

**2.4 Verify Old Password Doesn't Work**
- Logout (top right "Logout")
- Try to login with:
  - Email: `pilot1@siu.edu`
  - Password: `pass123` (old password)
- ✓ Should see error: "Invalid email or password"
- ✓ Login should FAIL

**2.5 Verify New Password Works**
- Clear login form
- Email: `pilot1@siu.edu`
- Password: `testpass123` (new password)
- ✓ Should login successfully

### If Test Fails

**Old password still works:**
- Password update failed (database issue)
- Screenshot the error
- Report immediately

**New password doesn't work:**
- Check for typos
- Try resetting again
- Check browser console

**No success message after changing password:**
- Refresh profile page
- Message may have cleared
- Try logout/login to verify password actually changed

---

## Test 3: PROFILE STATUS DISPLAY (Critical Fix #3)

### Expected Result
Profile shows correct approval status.

### Step-by-Step

**3.1 Login as Approved User**
- Email: `pilot1@siu.edu`
- Password: `pass123`
- Go to Profile

**3.2 Check Account Status**
- Look for "Account Information" section
- Under "Account Status:" should see:
- ✓ Green checkmark + **"✓ Approved"** (NOT "Pending Approval")

### If Test Fails

**Shows "Pending Approval" instead of "Approved":**
- User account not approved in database
- Contact admin
- Screenshot the status

---

## Test 4: PAIRING ERROR MESSAGE (Critical Fix #4)

### Expected Result  
Error messages include user names, not generic "409 Conflict".

### How to Test
- Go to http://localhost:8000/coach
- Admin login: admin@siu.edu / admin123
- Click "Manage Pairings"
- Try to pair an already-paired pilot with someone else
- ✓ Should see error like: "Cannot create pairing: Alex Johnson is already in an active pairing"
- ✗ Should NOT see: "Error 409: Conflict"

---

## Test 5: RESULTS PAGE BUTTON (Critical Fix #5)

### Expected Result
Single "Return to Dashboard" button, not multiple buttons.

### How to Test
- Go to Results page
- ✓ Should see exactly ONE button at bottom: "Return to Dashboard"
- ✗ Should NOT see duplicate buttons

---

## Summary Checklist

**MUST PASS (Blockers):**
- [ ] Prenav: Leg time fields appear after selecting NAV
- [ ] Prenav: Form submits and shows token
- [ ] Prenav: Token is 32 characters
- [ ] Prenav: Expiration is 48 hours in future
- [ ] Password: Old password fails after reset
- [ ] Password: New password works after reset

**SHOULD PASS (Quality):**
- [ ] Profile: Shows "Approved" not "Pending"  
- [ ] Pairing: Error includes user name
- [ ] Results: Single button only
- [ ] All forms work on iPhone

---

## Reporting Results

### If ALL Tests Pass
**Message:** "All v0.4.1 fixes verified. Ready for production."

### If ANY Test Fails
**Include:**
1. Test name (e.g., "Prenav submission")
2. Exact error message or screenshot
3. Steps to reproduce
4. Browser used (Safari iPhone, Chrome desktop, etc.)
5. Time/date of test

---

## Emergency Contacts

**Issue:** Prenav form won't submit
**Try:** Select different NAV, hard refresh browser

**Issue:** Login fails
**Check:** Password is exactly `pass123` (case-sensitive)

**Issue:** Any error
**Action:** Screenshot and report with test name

---

## Notes

- **Tests should take ~15-20 minutes total**
- **Don't skip the hard refresh on step 1.2 - cache is CRITICAL**
- **Password reset requires logout/login to verify**
- **If confused, follow the step-by-step exactly as written**

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.4.0   | Feb 12 | Initial release |
| 0.4.1   | Feb 13 | **5 critical fixes** |

---

**THIS IS THE OFFICIAL RELEASE - PLEASE TEST THOROUGHLY**

If all tests pass, you can confidently deploy v0.4.1 to production.
