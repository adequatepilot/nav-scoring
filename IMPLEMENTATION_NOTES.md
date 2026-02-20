# NAV Assignment Workflow UX Fix - Implementation Notes

**Date:** February 19, 2026  
**Issue:** Skip NAV selection pages when NAV is already known from assignment  
**Status:** ✅ COMPLETE

## Overview

This implementation improves the user experience by skipping redundant NAV selection pages when the NAV is already known from the assignment workflow.

## Changes Made

### 1. Backend Changes (app/app.py)

#### `/prenav` GET Route (Line ~1143)
- **Added:** Query parameter support for `nav_id`
- **Purpose:** Accept pre-selected NAV from assignment workflow
- **Logic:**
  ```python
  nav_id = request.query_params.get('nav_id', None)
  # ... pass nav_id to template
  ```
- **Backward Compatible:** Works with or without `nav_id` parameter

#### `/flight/select` GET Route (Line ~1335)
- **Added:** Query parameter support for `assignment_id`
- **Added:** Auto-redirect logic to skip selection page
- **Logic:**
  - If `assignment_id` is provided:
    1. Look up assignment to get `nav_id`
    2. Query open prenav submissions filtered by that NAV
    3. If exactly one prenav exists, redirect to `/flight?prenav_id=X`
    4. If none or multiple prenavs, show selection page as normal
- **Backward Compatible:** Works with or without `assignment_id` parameter

### 2. Database Changes (app/database.py)

#### `get_open_prenav_submissions` Method (Line ~989)
- **Added:** Optional `nav_id` parameter for filtering
- **Changes:** 
  - Added `nav_id: Optional[int] = None` parameter
  - Updated SQL queries to filter by `nav_id` when provided
  - Maintains backward compatibility (nav_id defaults to None)
- **Impact:** Allows finding prenav submissions for specific NAV

### 3. Template Changes

#### assignment_workflow.html
- **Line ~181:** Pre-flight button link changed
  - OLD: `/prenav?assignment_id={{ assignment.id }}`
  - NEW: `/prenav?nav_id={{ assignment.nav_id }}`
- **Line ~199:** Post-flight button link unchanged
  - `/flight/select?assignment_id={{ assignment.id }}`
  - (Backend now processes this)

#### prenav.html
- **Coach View:** Added `selected` attribute to pre-select nav_id in dropdown if provided
- **Competitor View:** 
  - If `nav_id` is provided: Show confirmation message instead of dropdown
  - If `nav_id` is NOT provided: Show dropdown as before
  - Hidden input field to pass nav_id to form
- **JavaScript:** Added `DOMContentLoaded` event listener to auto-initialize form fields when nav_id is pre-selected

## User Experience Flows

### Pre-Flight Submission Flow
```
User clicks assignment card (e.g., "MDH 20")
  ↓
User clicks "Submit Pre-Flight"
  ↓
Browser navigates to: /prenav?nav_id=20
  ↓
Backend passes nav_id to template
  ↓
Competitor sees: NAV pre-selected with confirmation
           Coach sees: NAV selected in dropdown
  ↓
JavaScript initializes form fields for that NAV
  ↓
User fills in times and fuel estimate
  ↓
User submits form
```

### Post-Flight Submission Flow
```
User clicks assignment card
  ↓
User clicks "Submit Post-Flight"
  ↓
Browser navigates to: /flight/select?assignment_id=42
  ↓
Backend looks up assignment (nav_id=20)
  ↓
Backend queries prenavs for nav_id=20
  ↓
IF exactly 1 prenav found:
    Redirect to: /flight?prenav_id=123
    ↓
    User sees pre-flight form ready to complete with post-flight data
ELSE (0 or multiple prenavs):
    Show: Selection page with list of prenavs
    ↓
    User selects which prenav to complete
  ↓
User fills in GPX file and actual fuel/secrets
  ↓
User submits form
```

## Technical Details

### URL Parameter Flow
- **Pre-flight:** `assignment.nav_id` → URL param `?nav_id=` → Template `{{ nav_id }}`
- **Post-flight:** `assignment.id` → Backend lookup → Find prenav → Redirect with `?prenav_id=`

### Database Queries
The `get_open_prenav_submissions` method now supports filtering:
```python
# Get all submissions
get_open_prenav_submissions(user_id=123)

# Get submissions for specific NAV (for assignment workflow)
get_open_prenav_submissions(user_id=123, nav_id=20)

# Coaches can use is_coach=True to see all
get_open_prenav_submissions(is_coach=True, nav_id=20)
```

### JavaScript Initialization
When `nav_id` is pre-selected, the JavaScript automatically:
1. Gets the selected option from the nav_id field
2. Extracts the checkpoint count from that option
3. Generates leg time input fields
4. Shows time and fuel estimate fields
5. Shows route confirmation message

## Backward Compatibility

✅ **All changes are backward compatible:**
- Old URLs without parameters still work
- New parameters are optional
- Existing workflows unaffected
- Database queries degrade gracefully

## Testing Recommendations

### Test Pre-Flight Skip
1. Navigate to assignment workflow
2. Click "Submit Pre-Flight"
3. **Expected:** Go directly to form with NAV pre-selected
4. **Should NOT see:** NAV selection dropdown (for competitors)
5. Form fields should be auto-populated for selected NAV

### Test Post-Flight Auto-Redirect
1. Submit a pre-flight for an assignment
2. Navigate to assignment workflow
3. Click "Submit Post-Flight"
4. **Expected:** 
   - If one prenav exists: Auto-redirect to post-flight form
   - If multiple prenavs: Show selection page
   - If no prenavs: Show error message

### Test Legacy Workflows
1. Visit `/prenav` without `nav_id` parameter
   - Should show dropdown as before
2. Visit `/flight/select` without `assignment_id` parameter
   - Should show selection page as before
3. All existing submit buttons should still work

### Test Coaches
1. As coach, verify you can still select different pairings
2. Verify nav_id pre-selection works for coaches too
3. Verify coaches can still change NAV selection if needed

### Test Edge Cases
1. Invalid nav_id (non-existent)
   - Should still show form or error gracefully
2. Invalid assignment_id
   - Should show selection page
3. User without permission for assignment
   - Should be rejected (existing permission logic)
4. Multiple prenavs for same NAV
   - Should show selection page (not auto-redirect)

## Files Modified

1. `/home/michael/clawd/work/nav_scoring/app/app.py`
   - Modified `/prenav` GET route (~30 lines)
   - Modified `/flight/select` GET route (~50 lines)

2. `/home/michael/clawd/work/nav_scoring/app/database.py`
   - Modified `get_open_prenav_submissions` method (~100 lines)
   - Backward compatible, no breaking changes

3. `/home/michael/clawd/work/nav_scoring/templates/team/prenav.html`
   - Modified competitor section (~15 lines)
   - Added JavaScript initialization (~7 lines)
   - Coach section shows pre-selected dropdown (~3 lines)

4. `/home/michael/clawd/work/nav_scoring/templates/team/assignment_workflow.html`
   - Changed pre-flight link (~1 line)
   - Post-flight link already passes assignment_id (~0 lines)

## Known Limitations

1. **Coach can still change NAV:** Coach can select different NAV from dropdown even if pre-selected (this is intentional - coaches should have flexibility)
2. **Multiple prenavs for same NAV:** If user has multiple open prenavs for the same NAV, selection page is shown (correct behavior - user should choose which one to complete)
3. **No confirmation dialog:** User goes straight to form with nav_id (this is the feature - no extra clicks)

## Future Enhancements

1. Could add visual indicator in assignment card showing if prenav/postnav already submitted
2. Could add "quick complete" button to skip to post-flight form
3. Could add bulk submission for multiple assignments
4. Could add assignment batch operations

## Rollback Plan

If issues arise:
1. Revert app/app.py changes to original `/prenav` and `/flight/select` routes
2. Revert database.py changes to original `get_open_prenav_submissions` method
3. Revert prenav.html to show dropdown always
4. Revert assignment_workflow.html to use `assignment_id` parameter instead of `nav_id`

All changes are isolated and can be reverted independently.

---
**Implementation completed by:** Subagent (f431442d-8494-4ffe-af34-1060d70f1fa9)  
**Verified by:** Code syntax checking, file modification verification
