# NAV Assignment Workflow UX Fix - Test Guide

## Quick Test Checklist

### Pre-Flight Submission (Navigator Role)
```
✓ Click assignment card (e.g., "MDH 20")
✓ Click "Submit Pre-Flight" button
  Expected: Navigate to /prenav?nav_id=20
           Form shows with NAV already selected
           Form fields are immediately populated with leg time inputs
✓ Verify no NAV selection dropdown is shown
✓ Fill in times and fuel estimate
✓ Submit form
  Expected: Form posts successfully with nav_id pre-filled
```

### Post-Flight Submission (Navigator Role - Single Prenav)
```
✓ After pre-flight is submitted
✓ Click same assignment card again
✓ Click "Submit Post-Flight" button
  Expected: Navigate to /flight/select?assignment_id=42
           Backend finds prenav for that NAV
           Auto-redirects to /flight?prenav_id=123
           Lands directly on post-flight form (no selection page)
✓ Fill in GPX file, fuel, and secrets data
✓ Submit form
  Expected: Flight scores successfully
```

### Post-Flight Submission (Navigator Role - Multiple Prenavs)
```
✓ Submit multiple pre-flights for different NAVs
✓ Click assignment for first NAV
✓ Click "Submit Post-Flight"
  Expected: Shows selection page (because assignment points to ONE NAV but user has multiple prenavs total)
           OR auto-redirects if only one prenav exists for that specific NAV
✓ Select correct prenav from list
✓ Submit post-flight
```

### Coach Pre-Flight Submission
```
✓ As coach, navigate to /prenav
✓ Optionally add ?nav_id=20 to URL
  Expected: NAV selector shows with nav_id=20 selected if provided
           Otherwise shows empty dropdown
✓ Select a pairing from dropdown
✓ Select a NAV (or see it pre-selected)
✓ Fill in times and fuel
✓ Submit
  Expected: Prenav created for selected pairing and NAV
```

### Coach Post-Flight Submission
```
✓ As coach, navigate to /flight/select
✓ Optionally add ?assignment_id=42 to URL
  Expected: If one prenav for that assignment's NAV: auto-redirects
           Otherwise: shows list of all open prenavs
✓ Select a prenav or get auto-redirected
✓ Submit post-flight data
```

## Detailed Test Scenarios

### Scenario 1: Happy Path (Pre-Flight Skip)
**Setup:** Navigator with active assignment

**Steps:**
1. Visit `/team/assigned-navs`
2. Click on assignment card (e.g., "MDH 20")
3. Lands on `/team/assignment-workflow?assignment=42`
4. Click "Submit Pre-Flight" button
5. Expected: Redirects to `/prenav?nav_id=20` (NOT `/prenav?assignment_id=42`)
6. Expected: Page loads with form visible (not selection dropdown)
7. Expected: Leg time fields are visible and numbered
8. Fill in form:
   - Leg 1: 0:01:30
   - Leg 2: 0:02:15
   - Leg 3: 0:01:45
   - Total: 0:05:30
   - Fuel: 5.5 gal
9. Click "Submit Pre-Flight Plan"
10. Expected: Form posts successfully, redirects to `/prenav_confirmation`

**Pass/Fail:** ✅ PASS if steps 5-10 work as expected

### Scenario 2: Happy Path (Post-Flight Auto-Redirect)
**Setup:** Pre-flight already submitted for assignment

**Steps:**
1. From assignment workflow page, click "Submit Post-Flight"
2. Expected: Browser navigates to `/flight/select?assignment_id=42`
3. Expected: Backend finds prenav for MDH 20
4. Expected: Auto-redirects to `/flight?prenav_id=123` (no intermediate page shown)
5. Expected: Lands directly on post-flight form with prenav details shown
6. Select start gate: "Gate A"
7. Upload GPX file
8. Enter actual fuel: 5.3 gal
9. Enter secrets missed:
   - Checkpoint: 0
   - Enroute: 1
10. Click "Submit & Score Flight"
11. Expected: Flight scores successfully

**Pass/Fail:** ✅ PASS if steps 2-11 work as expected, especially the auto-redirect in step 4

### Scenario 3: Backward Compatibility (Old URL)
**Setup:** User manually types old URL

**Steps:**
1. Visit `/prenav` (without any parameters)
2. Expected: Page loads with NAV dropdown showing all NAVs
3. Select a NAV from dropdown
4. Form fields appear
5. Fill and submit
6. Expected: Works exactly as before

**Pass/Fail:** ✅ PASS if form works without nav_id parameter

### Scenario 4: Edge Case (Non-existent NAV ID)
**Setup:** User visits with invalid nav_id

**Steps:**
1. Visit `/prenav?nav_id=99999`
2. Expected: Page loads gracefully
3. Expected: Either shows dropdown or error message
4. Expected: No JavaScript errors in console

**Pass/Fail:** ✅ PASS if page handles gracefully

### Scenario 5: Coach Workflow (Pre-flight)
**Setup:** Coach user

**Steps:**
1. Visit `/prenav`
2. Expected: Pairing selector dropdown visible (not in competitor view)
3. Expected: NAV selector visible
4. Optionally add `?nav_id=20` to URL
5. Expected: NAV dropdown shows nav_id=20 as selected option
6. Select a pairing
7. Confirm NAV or change it
8. Fill form
9. Submit
10. Expected: Prenav created for selected pairing

**Pass/Fail:** ✅ PASS if coach can create prenav for any pairing

## Regression Tests

### Critical Path (Must Work)
- [ ] Competitor can submit pre-flight
- [ ] Competitor can submit post-flight after pre-flight
- [ ] Coach can submit pre-flight for any pairing
- [ ] Coach can submit post-flight for any pairing
- [ ] Form submissions validate correctly
- [ ] Scoring calculation still works
- [ ] Email notifications still sent

### Edge Cases (Should Handle)
- [ ] User with no pairing gets error message
- [ ] Invalid file uploads rejected
- [ ] Multiple prenavs for same user shows selection
- [ ] Permission checks still enforced

### Database (Must Not Break)
- [ ] Prenav submissions created with correct nav_id
- [ ] Post-flight submissions link to correct prenav
- [ ] Status transitions work (open → scored)
- [ ] No orphaned records created

## Manual Testing Checklist

### Browser Testing
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (if Mac available)
- [ ] Mobile browser (responsive design)

### JavaScript Testing
- [ ] Open browser DevTools Console
- [ ] No JavaScript errors when navigating
- [ ] Form validation works
- [ ] Time input fields only accept numbers
- [ ] Fuel estimate validates

### Network Testing
- [ ] Check Network tab in DevTools
- [ ] Verify nav_id parameter passed in URL
- [ ] Verify assignment_id parameter passed in URL
- [ ] Verify form posts with correct data

## Performance Checks
- [ ] Page loads in <2 seconds
- [ ] Form initialization is instant (no lag)
- [ ] Auto-redirect happens immediately
- [ ] No database query timeouts

## Known Test Issues

None yet - mark as you discover them during testing.

## Sign-Off

**Tester Name:** _________________  
**Date:** _________________  
**Overall Result:** ✅ PASS / ❌ FAIL  

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

