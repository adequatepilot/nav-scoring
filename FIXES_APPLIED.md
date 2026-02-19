# Post-Flight Submission Permission Fixes - v0.4.5

## Issue Fixed
Admin user (admin@siu.edu with is_coach=1, is_admin=1) was getting error "This page is for competitors only. Please use the Coach Dashboard instead." when trying to submit post-flight.

## Root Cause
The `/results/{result_id}` route (where POST /flight redirects after successful scoring) was using the `require_member` decorator, which rejects ANY user with `is_coach=1`. This was incorrect because:
1. The route's internal authorization logic already correctly allows coaches/admins to view any result
2. The POST /flight route correctly uses `require_login` and allows coaches/admins to submit

## Changes Made

### 1. Fixed /results/{result_id} Route (Line 1600)
**Before:**
```python
async def view_result(request: Request, result_id: int, user: dict = Depends(require_member)):
```

**After:**
```python
async def view_result(request: Request, result_id: int, user: dict = Depends(require_login)):
```

**Also updated authorization logic:**
```python
# Now allows coaches/admins to view any result
is_coach = user.get("is_coach", False)
is_admin = user.get("is_admin", False)

pairing = db.get_pairing(result["pairing_id"])
if not (is_coach or is_admin):  # Only enforce pairing check for competitors
    if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
        logger.warning(f"Competitor user {user['user_id']} not authorized to view result {result_id}")
        raise HTTPException(status_code=403, detail="Not authorized to view this result")
else:
    logger.info(f"Coach/admin user {user['user_id']} accessing result {result_id}")
```

### 2. Fixed /results/{result_id}/pdf Route (Line 1662)
**Before:**
```python
async def download_pdf(result_id: int, user: dict = Depends(require_member)):
```

**After:**
```python
async def download_pdf(result_id: int, user: dict = Depends(require_login)):
```

**Also updated authorization logic to allow coaches/admins:**
```python
is_coach = user.get("is_coach", False)
is_admin = user.get("is_admin", False)

if not (is_coach or is_admin):
    pairing = db.get_pairing(result["pairing_id"])
    if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
        raise HTTPException(status_code=403, detail="Not authorized")
```

### 3. Enhanced POST /flight Route with Logging (Line 1264)
Added comprehensive logging for debugging:
- **Line 1271:** Log user, is_coach, is_admin at start of submission
- **Line 1275:** Log prenav lookup result
- **Line 1302-1304:** Log authorization decision (pass/fail)
- **Line 1309-1312:** Validate leg_times count matches checkpoints
- **Line 1371:** Log checkpoint scoring details
- **Line 1525:** Log successful submission and redirect
- **Line 1533:** Log error and details

**Example log output:**
```
INFO: POST /flight: User 123 (admin@siu.edu) submitting prenav_id=456. is_coach=1, is_admin=1
DEBUG: POST /flight: prenav_id=456, found=True
INFO: Authorization passed: user 123 is coach/admin, can submit for any pairing
DEBUG: Checkpoint 0 (Checkpoint A): estimated_time=300s, distance=10.5nm, method=nearest
...
INFO: POST /flight: Successfully scored prenav_id=456, result_id=789, overall_score=950.5. Redirecting to results page.
```

## Test Scenarios

### Scenario 1: Coach/Admin Post-Flight Submission ✅ NOW FIXED
1. User: admin@siu.edu (is_coach=1, is_admin=1)
2. Navigates to /flight/select
3. Clicks "Select" on a prenav
4. Submits form with GPX file → POST /flight
5. Route processes and redirects to /results/{result_id}
6. **Previously:** Got 403 error from require_member
7. **Now:** Successfully views result page

### Scenario 2: Competitor Post-Flight Submission (Should Still Work)
1. User: pilot@siu.edu (is_coach=0, is_admin=0)
2. Only sees their own prenav submissions
3. Submits form → POST /flight
4. Route checks if user is in pairing → PASS
5. Redirects to /results/{result_id}
6. **Expected:** Works (unchanged)

### Scenario 3: Unauthorized Competitor Access (Should Still Block)
1. User: pilot1@siu.edu (is_coach=0, is_admin=0)
2. Somehow tries to view result from pilot2's pairing
3. Route checks if user is in pairing → FAIL
4. **Expected:** 403 error (unchanged)

## Validation Added
- **leg_times count validation:** Ensures prenav.leg_times has exactly as many entries as checkpoints before scoring
- **Better error messages:** All errors now logged with context for debugging

## Files Modified
1. `/home/michael/clawd/work/nav_scoring/app/app.py`
   - Line 1600: Changed require_member to require_login for /results/{result_id}
   - Line 1610-1619: Updated authorization logic for /results/{result_id}
   - Line 1662: Changed require_member to require_login for /results/{result_id}/pdf
   - Line 1671-1678: Updated authorization logic for /results/{result_id}/pdf
   - Line 1271: Added logging for user/coach/admin info
   - Line 1275: Added prenav lookup logging
   - Line 1302-1304: Added authorization logging
   - Line 1309-1312: Added leg_times validation
   - Line 1371: Added checkpoint scoring logging
   - Line 1525: Added success redirect logging
   - Line 1533: Added error logging

## Related Issue References
- TASK_FIX_POSTNAV_ERROR_HANDLING.md: Leg_times count validation implemented

## Testing the Fix

To verify the fix works:

```bash
# 1. Check logs for successful flow
# Look for these log messages in order:
# "POST /flight: User X submitting..."
# "Authorization passed: user X is coach/admin..."
# "Successfully scored prenav_id=X, result_id=Y..."

# 2. Test admin@siu.edu submission
# - Navigate to /flight/select
# - Click Select on any prenav
# - Upload GPX file
# - Submit
# - Should redirect to /results/{result_id} without error

# 3. Verify error handling
# - Check logs show detailed error info if submission fails
# - Error page should display with helpful message
```

## Backward Compatibility
✅ All changes are backward compatible
- Competitors can still only access their own results (same logic)
- Coaches/admins already had permission in the route logic, just decorator was blocking them
- Logging is non-intrusive
- No database schema changes
