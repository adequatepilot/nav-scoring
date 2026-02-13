# Task: NAV Scoring Laundry List Batch 7

## Context
Three new issues after v0.4.3 deployment. One is CRITICAL - post-flight submission is completely broken.

## Project Location
`/home/michael/clawd/work/nav_scoring/`

**Current version:** v0.4.3  
**Deployed at:** http://localhost:8000 (Docker container)  
**Admin login:** admin@siu.edu / admin123  
**Test users:** pilot1@siu.edu / pass123, observer1@siu.edu / pass123  
**GitHub repo:** https://github.com/adequatepilot/nav-scoring

## Issues to Fix

### 23: Submit & Score Flight gives black page with error (CRITICAL)
**Mike's report:** `{"detail":""}`

**Problem:** Post-flight submission workflow is completely broken. User submits GPX file and gets blank error message.

**This blocks the entire scoring workflow** - you can't test any of the core functionality without being able to submit flights.

**Debug steps:**
1. First, generate a prenav token:
   - Login as pilot1@siu.edu / pass123
   - Submit pre-flight plan for NAV-1
   - Note the token
2. Then test post-flight submission:
   - Click "Submit Post-Flight" (or navigate to /flight)
   - Enter the token from step 1
   - Upload a GPX file (you may need to create a dummy one)
   - Click "Submit & Score Flight"
   - Check what error appears
3. Check backend logs for actual error
4. Check browser console/network tab for full error response

**Likely causes:**
- GPX file validation failing
- Secrets scoring logic crashing
- Missing checkpoint data
- Database query error
- File upload path issue
- Empty error message being returned instead of actual error

**Files to check:**
- Post-flight submission route in `app/app.py`
- GPX parsing/scoring logic in `app/scoring_engine.py`
- Flight results template (error display)

**Expected behavior:**
1. User enters valid prenav token
2. Uploads GPX file
3. Reports fuel used and secrets found
4. Gets scored results with PDF report
5. Receives email with results

**Test:**
You'll need to create a minimal test GPX file or find the expected format. Might be in references or test data.

### 16.5: Total time should use HH:MM:SS boxes (not MM:SS text input)
**Current:** Total flight time is a single text input expecting MM:SS format  
**Required:** Three separate boxes (HH, MM, SS) like the leg times

**Why:** Consistency - all time inputs should use the same format. Also prevents input errors.

**Implementation:**
1. Replace total time text input with 3 number inputs (HH, MM, SS)
2. JavaScript combines them into total seconds before submission
3. Same styling as leg time inputs
4. Same validation rules

**Files:**
- `templates/team/prenav.html` - Replace total time input, update JavaScript

**Test:**
1. Login as pilot1@siu.edu / pass123
2. Go to prenav form
3. Select NAV-1
4. Verify total time has HH:MM:SS boxes (not single MM:SS field)
5. Enter values, submit, verify they're combined correctly

### 16.6: HH/MM/SS boxes should default to 0 and only accept numbers
**Current:** Boxes are empty by default, may accept non-numeric input  
**Required:** 
- Default value: 0 (so box shows "0" not empty)
- Input type: number (browser enforces numeric-only)
- Min value: 0
- No decimals allowed

**Implementation:**
All HH/MM/SS inputs (leg times + total time) should have:
```html
<input type="number" min="0" step="1" value="0" ... />
```

**Files:**
- `templates/team/prenav.html` - Update all time input fields

**Test:**
1. Login as pilot1@siu.edu / pass123
2. Go to prenav form
3. Select NAV-1
4. Verify all HH/MM/SS boxes show "0" by default (not empty)
5. Try entering letters - should be prevented by browser
6. Try entering decimals - should be prevented or rounded

## Testing Checklist
- [ ] **CRITICAL:** Post-flight submission works (no blank error)
- [ ] Post-flight submission completes full workflow with dummy GPX
- [ ] Total time uses HH:MM:SS boxes (not MM:SS text input)
- [ ] All time input boxes default to 0
- [ ] All time input boxes only accept integers (no letters, no decimals)
- [ ] Prenav submission still works after time input changes

## Workflow
1. **Fix issue 23 FIRST** - it's blocking all testing
2. Fix 16.5 and 16.6 (related to each other)
3. Test thoroughly (especially full prenav → post-flight workflow)
4. Update CHANGELOG.md
5. Run: `bash scripts/release.sh patch` (bumps to v0.4.4)
6. Docker rebuild + redeploy
7. Test deployed version
8. Report back

## Priority Order
1. **23** - Post-flight submission (CRITICAL - completely broken)
2. **16.5** - Total time HH:MM:SS boxes (UX improvement)
3. **16.6** - Default to 0, numbers only (UX improvement)

## Git Commit Style
```
Fix laundry list batch 7 (post-flight + time input improvements)

- Fix post-flight submission black page error (issue 23)
- Change total time to HH:MM:SS boxes for consistency (16.5)
- Set time inputs to default 0, numbers only (16.6)

Issue 23 was blocking all scoring workflow testing.

Closes issues 16.5, 16.6, 23
```

## Notes
- Issue 23 is CRITICAL - blocks all workflow testing
- You may need to create a test GPX file to properly test issue 23
- Issues 16.5 and 16.6 are closely related (both about time inputs)
- Test the FULL workflow: prenav → get token → post-flight → see results

**GET ISSUE 23 WORKING FIRST - everything else depends on it.**
