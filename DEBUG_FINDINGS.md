# Post-Flight Submission Permission Debug - v0.4.5

## Root Cause Found ✓

**The Issue:** Admin user (admin@siu.edu with is_coach=1, is_admin=1) gets error "This page is for competitors only" when submitting post-flight.

**Why This Happens:**

1. User hits GET /flight (OK - uses require_login)
2. User submits form POST /flight (OK - uses require_login) 
3. POST /flight route successfully processes the flight and redirects to `/results/{result_id}` (line 1499)
4. **BUG:** `/results/{result_id}` route (line 1600) uses `Depends(require_member)` decorator
5. `require_member` decorator rejects ANY user with `is_coach=1` (line 200)
6. Admin user has is_coach=1, so they get blocked with the error message

**The Code Path:**
- Line 200: `require_member` checks `if user.get("is_coach")` and raises the error
- Line 1600: `/results/{result_id}` uses `require_member` 
- But the actual authorization logic inside the route (lines 1610-1614) IS correct:
  ```python
  if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
      # Only reject if NOT a coach/admin
      raise HTTPException(status_code=403, detail="Not authorized to view this result")
  ```

**Note:** The same issue exists at line 1662 for `/results/{result_id}/pdf` - it also uses `require_member`.

## The Fix

Change the decorators on these routes from `require_member` to `require_login`, and let the route's internal authorization logic handle the checks (which it already does correctly).

**Files to Change:**
1. `/results/{result_id}` - line 1600
2. `/results/{result_id}/pdf` - line 1662

## Additional Issues to Fix

### 1. Missing Logging in POST /flight
Added comprehensive logging to POST /flight route to show:
- User attempting submission (user_id, is_coach, is_admin)
- Prenav and pairing info
- Authorization decision
- GPX file processing steps
- Any errors

### 2. Missing Validation for leg_times Count
The code at line 1368 loops through checkpoints and accesses `prenav["leg_times"][i]`, but doesn't validate that leg_times has the right count. Need to add validation before scoring.

## Sessions State Verification
The session state is being stored correctly:
- `user.get("is_coach")` and `user.get("is_admin")` are properly populated
- They're being used correctly in /flight/select (line 1181) and /flight GET (line 1208)
- The problem is NOT with session storage, it's the decorator mismatch

## Form Posting
The form correctly posts to `/flight` (templates/team/flight.html line 64) ✓
