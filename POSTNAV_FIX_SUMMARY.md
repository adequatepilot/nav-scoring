# Post-Flight Flow Fixes - v0.4.3

## Fixes Applied

### Issue 1: Dashboard Links (FIXED ✓)
- **File**: `templates/dashboard.html`
- **Changes**: Updated 2 links from `/flight` to `/flight/select`
  - Line 15: Navbar link "Post-NAV"
  - Line 288: Quick-link button "Submit Post-Flight"
- **Result**: Dashboard now bypasses error page and goes directly to selection table

### Issue 2: Delete Button Confirmation (FIXED ✓)
- **Files**: 
  1. `templates/team/flight_select.html` - Updated delete button
  2. `app/app.py` - Added GET confirmation route and updated POST route

- **Changes**:
  - Removed inline form with `onsubmit="return confirm()"`
  - Changed to link: `<a href="/flight/delete/{{ prenav.id }}/confirm">`
  - Added GET route `/flight/delete/{prenav_id}/confirm` - shows delete_confirm.html
  - Updated POST route to redirect cleanly to `/flight/select`

- **Result**: Delete uses reliable page-based confirmation pattern (consistent with airports/gates)

## Verification

### Files Modified
- ✅ templates/dashboard.html
- ✅ templates/team/flight_select.html
- ✅ app/app.py
- ✅ VERSION (bumped to 0.4.3)
- ✅ CHANGELOG.md (added v0.4.3 entry)

### Commit
- ✅ Git commit: "fix: dashboard flow and prenav delete confirmation (v0.4.3)"

## Testing Checklist

**Dashboard Flow:**
- [ ] Click "Submit Post-Flight" on dashboard
- [ ] Should go directly to `/flight/select` (table view)
- [ ] No error page

**Delete Confirmation:**
- [ ] Login as admin
- [ ] Navigate to `/flight/select`
- [ ] Click Delete button
- [ ] Should show `/flight/delete/{id}/confirm` page with warning
- [ ] Click "Yes, Delete" → deletes, redirects to `/flight/select`
- [ ] Click "Cancel" → back to `/flight/select`, nothing deleted
- [ ] Try deleting scored submission → error message (cannot delete)

## Ready for Deployment

All changes applied successfully. Ready to:
1. Rebuild Docker image
2. Redeploy to staging/production
3. Push to GitHub
