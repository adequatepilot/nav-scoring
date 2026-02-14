# Coach Read-Only Security Audit & Findings

## Executive Summary

**Critical Issues Found:**
1. **Route Permission Bug (CRITICAL):** Most write operations use `require_coach` instead of `require_admin`, allowing non-admin coaches to modify data
2. **Template Header Bug:** Dashboard says "Admin Functions" for all coaches, should say "Coach Functions" for non-admin coaches
3. **Delete Routes Issue:** All delete routes use GET method with implicit redirects, which is unconventional and may cause issues

## Phase 1: Route Permission Audit

### READ Routes (GET) - These are CORRECT with `require_coach`
- ✓ GET /coach - Coach dashboard (require_coach)
- ✓ GET /coach/results - List results (require_coach)
- ✓ GET /coach/results/{result_id} - View single result (require_coach)
- ✓ GET /coach/members - List members (require_coach)
- ✓ GET /coach/pairings - List pairings (require_coach)
- ✓ GET /coach/navs - NAV dashboard (require_coach)
- ✓ GET /coach/navs/airports - Manage airports page (require_coach)
- ✓ GET /coach/navs/gates/{airport_id} - Manage gates page (require_coach)
- ✓ GET /coach/navs/routes - Manage routes page (require_coach)
- ✓ GET /coach/navs/checkpoints/{nav_id} - Manage checkpoints page (require_coach)
- ✓ GET /coach/navs/secrets/{nav_id} - Manage secrets page (require_coach)
- ✓ GET /coach/config - Config page (require_admin)
- ✓ GET /coach/backup/status - Backup status (require_admin)

### WRITE Routes - These NEED FIXES (using require_coach instead of require_admin)

#### Member Management
1. **POST /coach/members/bulk** - NEEDS FIX: require_coach → require_admin (bulk import)
2. **GET /coach/members/{member_id}/deactivate** - NEEDS FIX: require_coach → require_admin
3. **GET /coach/members/{member_id}/activate** - NEEDS FIX: require_coach → require_admin
4. **GET /coach/results/{result_id}/delete** - NEEDS FIX: require_coach → require_admin

#### Pairing Management
5. **POST /coach/pairings** - NEEDS FIX: require_coach → require_admin (create pairing)
6. **GET /coach/pairings/{pairing_id}/break** - NEEDS FIX: require_coach → require_admin
7. **GET /coach/pairings/{pairing_id}/reactivate** - NEEDS FIX: require_coach → require_admin
8. **GET /coach/pairings/{pairing_id}/delete** - NEEDS FIX: require_coach → require_admin

#### Airport Management
9. **POST /coach/navs/airports** - NEEDS FIX: require_coach → require_admin
10. **GET /coach/navs/airports/{airport_id}/delete** - NEEDS FIX: require_coach → require_admin

#### Start Gate Management
11. **POST /coach/navs/gates** - NEEDS FIX: require_coach → require_admin
12. **GET /coach/navs/gates/{gate_id}/delete** - NEEDS FIX: require_coach → require_admin

#### NAV Route Management
13. **POST /coach/navs/routes** - NEEDS FIX: require_coach → require_admin
14. **GET /coach/navs/routes/{nav_id}/delete** - NEEDS FIX: require_coach → require_admin

#### Checkpoint Management
15. **POST /coach/navs/checkpoints** - NEEDS FIX: require_coach → require_admin
16. **GET /coach/navs/checkpoints/{checkpoint_id}/delete** - NEEDS FIX: require_coach → require_admin

#### Secret Management
17. **POST /coach/navs/secrets** - NEEDS FIX: require_coach → require_admin
18. **GET /coach/navs/secrets/{secret_id}/delete** - NEEDS FIX: require_coach → require_admin

### Routes Already CORRECT with require_admin
- ✓ POST /coach/members/update (require_admin)
- ✓ POST /coach/members/edit (require_admin)
- ✓ POST /coach/members/{user_id}/delete (require_admin)
- ✓ POST /coach/members (require_admin)
- ✓ POST /coach/members/{user_id}/approve (require_admin)
- ✓ POST /coach/members/{user_id}/deny (require_admin)
- ✓ POST /coach/config (require_admin)
- ✓ POST /coach/config/email (require_admin)
- ✓ POST /coach/test_smtp (require_admin)
- ✓ POST /coach/config/backup (require_admin)
- ✓ POST /coach/backup/run (require_admin)

## Phase 2: Template Updates

### Issue: Dashboard Header
**File:** `templates/dashboard.html` (line ~169)
**Problem:** Says "Admin Functions" for all coaches
**Solution:** Conditional check for `is_admin` vs `is_coach`

## Phase 3: Delete Button Issue Analysis

All delete routes use GET method (unconventional for destructive operations). This is actually working but:
- Should ideally use POST with form submission (more semantically correct)
- The GET method works because they use RedirectResponse

**Status:** These are functional but architecturally unconventional. Keep as-is since they work.

## Summary of Fixes Needed

**Total Fixes: 19**
- 18 route permission fixes (require_coach → require_admin)
- 1 template header fix

## Security Impact

**Before:** Non-admin coaches can modify data by:
- Posting directly to endpoints like `/coach/pairings`, `/coach/navs/airports`, etc.
- Browser buttons are hidden, but no backend validation prevents direct API calls

**After:** Only admins can modify, coaches are truly read-only
