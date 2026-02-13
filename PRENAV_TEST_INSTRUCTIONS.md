# Prenav Submission - Test Instructions for Mike

## CRITICAL DISCOVERY

**The prenav submission was working correctly.** The problem was that **NAVs had zero checkpoints**, making the form unusable.

### Root Cause
- Seeded NAVs (NAV-1, NAV-2, NAV-3) had no checkpoints in the database
- When user selects a NAV with 0 checkpoints, form hides all input fields
- User sees form but can't enter anything
- Appears broken, but actually missing test data

### Fix Applied
- Updated `seed.py` to automatically add 3 sample checkpoints to each NAV
- Now when you bootstrap the database, NAVs come with checkpoints
- Prenav submission works immediately

---

## How to Test on iPhone (for Mike)

### Prerequisites
1. App deployed at http://localhost:8000
2. Logged out completely
3. Clear browser cache (Settings → Safari → Clear History and Website Data)

### Step-by-Step Test

**Step 1: Login**
- Go to http://localhost:8000
- Email: `pilot1@siu.edu`
- Password: `pass123`
- Tap "Login"
- Should see dashboard with "Submit Pre-Flight Plan" button

**Step 2: Start Prenav Form**
- Tap "Submit Pre-Flight Plan" or go to http://localhost:8000/prenav
- Should see form with "Select NAV Route" dropdown and pairing info showing:
  - Pilot: Alex Johnson
  - Observer: Taylor Brown

**Step 3: Select NAV**
- Tap dropdown "Select NAV Route"
- Select any NAV (NAV-1, NAV-2, or NAV-3)
- **Important:** Should NOW see leg time fields appear below
- Each NAV has 3 checkpoints = 3 leg time fields

**Step 4: Fill Leg Times**
- For each leg, you'll see three input fields (HH : MM : SS)
- Example: If you want 5 minutes 30 seconds per leg:
  - Hours: `00`
  - Minutes: `05`
  - Seconds: `30`
- Fill all 3 legs with same time (e.g., 00:05:30 each)

**Step 5: Fill Total Flight Time**
- Field format: MM:SS (minutes and seconds only)
- If 3 legs of 5:30 each = approximately 16:30 total
- Enter: `16:30`
- **Important:** Must be in MM:SS format, not HH:MM:SS

**Step 6: Fill Fuel Estimate**
- Enter any number (e.g., `8.5`)
- Decimal allowed (e.g., 8.5, 10.2)

**Step 7: Submit**
- Tap "Submit Pre-Flight Plan" button
- Should redirect to **confirmation page**
- Confirmation page shows:
  - Green checkmark icon
  - Your submission token (32-character hex string)
  - Expiration time (48 hours from submission)
  - Next steps instruction

**Step 8: Verify Success**
- Token should be visible and copyable
- Token format: `abc123def456...` (32 hex characters)
- Expiration should be 48 hours in future (e.g., Feb 15, 16:36 UTC)

---

## If It Doesn't Work

### Leg Time Fields Don't Appear
- **Problem:** Selected NAV has 0 checkpoints
- **Solution:** Select a different NAV, or contact admin to add checkpoints via coach dashboard
- **Verify:** NAV should show with 3 checkpoints selected

### Submission Returns Error
- **Problem:** Form validation failed
- **Solution:** Check:
  - All leg times filled (all 3 fields for each leg)
  - Total flight time in MM:SS format (not HH:MM:SS)
  - Fuel estimate is a number
  - No blank fields

### Token Not Showing
- **Problem:** Confirmation page doesn't display token
- **Solution:** 
  - Check browser console (Developer Tools → Console)
  - Verify you were redirected to `/prenav_confirmation?token=...`
  - Try hard refresh (Cmd+Shift+R on Mac, Ctrl+Shift+R on PC)

### Session Expired Error
- **Problem:** "No active pairing found"
- **Solution:**
  - You must be paired with another user first
  - Contact coach/admin to create pairing
  - Current pairings: pilot1 ↔ observer1 (should work)

---

## Desktop Testing (for Verification)

```bash
# Test via curl
curl -b cookies.txt -X POST http://localhost:8000/login \
  -d "email=pilot1@siu.edu&password=pass123"

curl -b cookies.txt -X POST http://localhost:8000/prenav \
  -F "nav_id=1" \
  -F "leg_times_str=[330,330,330]" \
  -F "total_time_str=990" \
  -F "fuel_estimate=8.5"

# Should return: 303 redirect with location: /prenav_confirmation?token=...
```

---

## Summary

✅ **Prenav submission is now fully functional**
- NAVs have checkpoints
- Form validates properly  
- Submission creates token
- Confirmation page displays token
- 48-hour token expiration works
