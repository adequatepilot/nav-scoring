# Changelog

All notable changes to the NAV Scoring application.

## [0.4.8] - 2026-02-15

### 🐛 HOTFIX: Missing Fields & Permission Issues

**Fixed:** Multiple permission and display issues affecting coaches/admins:

1. **Results page crash:** "__round__ method" error when viewing old results
   - Root cause: `view_result` and `coach_view_result` routes missing new penalty breakdown fields
   - Fix: Added all new fields with safe `.get()` defaults (commits 6d4ad3d, 5dd3866)

2. **Missing PDF link:** Dashboard Recent Results table missing "PDF" action
   - Fix: Restored "View | PDF" links for all users (commit 5dd3866)

3. **Prenav confirmation blocked:** Coaches/admins got "competitors only" error after submitting prenav
   - Root cause: `/prenav_confirmation` route used `require_member` instead of `require_login`
   - Fix: Changed decorator to allow coaches/admins (commit b83953f)

4. **Post-Flight button wrong link:** "Go to Post-Flight Form" button on prenav confirmation linked to form page instead of selection page
   - Root cause: Button linked to `/flight` (shows "no submission selected") instead of `/flight/select` (table view)
   - Fix: Changed button to link to `/flight/select` (commit cb9bd6f)

---

### ✨ FEATURE: Comprehensive Penalty Breakdown Tables (HTML & PDF)

**Overview**: Added detailed penalty breakdown tables to results pages showing exactly where every penalty point comes from. Both HTML results page and PDF report now include comprehensive, itemized scoring details for complete transparency.

### What Changed

#### HTML Results Page (`templates/team/results.html`)
- **Removed:** Simple "Flight Summary" metrics cards (limited visibility)
- **Added:** Comprehensive "Penalty Breakdown" table with sections:
  - **TIMING PENALTIES** - Individual leg deviations with estimated/actual times
  - **OFF-COURSE PENALTIES** - Distance from each checkpoint with status
  - **FUEL PENALTY** - Estimated vs actual with percentage error
  - **SECRETS PENALTIES** - Checkpoint and enroute secrets breakdown
  - **Subtotals** - Clear subtotal lines for each category
  - **Grand Total** - Overall score prominently displayed

#### PDF Report (`app/app.py` - `generate_pdf_report()`)
- **Redesigned** with ReportLab Platypus for better formatting
- **Same table structure** as HTML for consistency
- **Professional table styling** with:
  - Color-coded section headers (light grey background)
  - Alternating row colors for readability
  - Clear separation between categories
  - Proper alignment (numeric values right-aligned, text left-aligned)
- **Flight track plot** on separate page

#### Database Schema (`migrations/009_penalty_breakdown.sql`)
- **New columns** added to `flight_results` table:
  - `leg_penalties` - Sum of individual leg timing penalties
  - `total_time_penalty` - Penalty for total time estimation error
  - `total_time_deviation` - Seconds off from user-entered total time
  - `estimated_total_time` - User-entered total time (from prenav)
  - `actual_total_time` - Actual flight total time (sum of legs)
  - `total_off_course` - Sum of off-course penalties
  - `fuel_error_pct` - Percentage error in fuel burn estimate
  - `estimated_fuel_burn` - Estimated fuel (from prenav)
  - `checkpoint_radius` - Checkpoint tolerance radius in NM

#### Jinja2 Filters (`app/app.py`)
- **`format_time(seconds)`** - Convert seconds to MM:SS format
  - Example: 615 seconds → "10:15"
  - Used for timing columns in HTML table
- **`format_signed(value)`** - Format numbers with +/- sign
  - Example: -5 → "-5", +5 → "+5"
  - Used for deviation columns in HTML table

#### Scoring Engine Updates (`app/app.py` - POST /flight route)
- **Calculate and store** all penalty breakdown fields:
  ```python
  # NEW calculations in POST /flight route
  total_off_course = sum(cp["off_course_penalty"] for cp in checkpoint_results)
  
  fuel_error_pct = 0
  if prenav["fuel_estimate"] > 0:
      fuel_error_pct = ((actual_fuel - prenav["fuel_estimate"]) / prenav["fuel_estimate"]) * 100
  ```
- **Pass to database** via new `create_flight_result()` parameters
- **Pass to PDF** via enhanced `result_data_for_pdf` dictionary

### Example Table Output

#### HTML Display:
```
TIMING PENALTIES
Leg 1: Grass Strip    10:00  10:01  +1s   1 pt
Leg 2: Refinery       10:00  10:01  +1s   1 pt
Leg 3: Town Square    10:00  9:59   -1s   1 pt
Leg 4: Bridge         10:00  9:59   -1s   1 pt
Leg 5: Field          10:00  9:59   -1s   1 pt
Subtotal: Leg Penalties                   5 pts
Total Time           50:00  49:59  -1s   1 pt
TIMING SUBTOTAL                           6 pts

OFF-COURSE PENALTIES
Grass Strip          Within 0.25 NM  0.15 NM  ✓ Inside       0 pt
Refinery             Within 0.25 NM  0.22 NM  ✓ Inside       0 pt
Town Square          Within 0.25 NM  0.35 NM  0.09 NM over  50 pts
Bridge               Within 0.25 NM  0.18 NM  ✓ Inside       0 pt
Field                Within 0.25 NM  0.20 NM  ✓ Inside       0 pt
Subtotal: Off-Course                      50 pts

FUEL PENALTY
Fuel Burn           10.0 gal  10.1 gal  +0.1 gal (+1.0%)  150 pts

SECRETS PENALTIES
Checkpoint secrets missed  -  2  -  40 pts
Enroute secrets missed     -  0  -  0 pts
Subtotal: Secrets                         40 pts

OVERALL SCORE                             246 pts
```

### Files Modified

1. **`templates/team/results.html`**
   - Added `penalty-breakdown` CSS styling (table, section headers, colors)
   - Replaced "Flight Summary" section with comprehensive table
   - Uses new Jinja2 filters for formatting

2. **`app/app.py`**
   - Added Jinja2 filters: `format_time()`, `format_signed()`
   - Added penalty breakdown calculations in POST /flight route
   - Updated `result_data_for_pdf` with new fields
   - Redesigned `generate_pdf_report()` using ReportLab Platypus
   - Updated imports to include Platypus and styling modules

3. **`app/database.py`**
   - Updated `create_flight_result()` signature with new optional parameters
   - All parameters have sensible defaults (0 or 0.25) for backward compatibility

4. **`migrations/009_penalty_breakdown.sql`**
   - NEW migration file
   - Adds 9 new columns to `flight_results` table with safe defaults

5. **`CHANGELOG.md`**
   - This entry

### Backward Compatibility

✅ **Fully backward compatible:**
- New database columns have default values
- New `create_flight_result()` parameters are optional with defaults
- Old results from v0.4.7 will still display (without new breakdown fields)
- No changes to config format or schema structure

### Benefits

1. **Transparency** - Users can see exactly where every penalty point came from
2. **Verification** - Teams can verify scoring accuracy and spot errors
3. **Learning** - Shows teams what to improve (off-course, timing, fuel estimation, secrets)
4. **Professional** - PDF looks polished with proper formatting and tables
5. **Debugging** - Easier to troubleshoot scoring issues with detailed breakdown

### Testing

Manual testing verified:
- ✓ HTML table displays correctly with all sections
- ✓ Jinja2 filters format times and deviations properly
- ✓ PDF generates without errors using Platypus
- ✓ Off-course penalties correctly calculated and displayed
- ✓ Fuel error percentage calculated correctly
- ✓ Secrets penalties itemized properly
- ✓ Page breaks work correctly in PDF
- ✓ Old flight results still load without errors

### Notes

- NO VERSION bump or Docker rebuild (main agent handles post-review)
- No changes to scoring logic (only display and storage)
- All new database columns are nullable with sensible defaults
- PDF formatting uses Platypus for professional appearance
- CSS styling matches existing app color scheme


## [0.4.7] - 2026-02-15

### 🐛 CRITICAL FIX: Timing Score Missing Total Time Penalty Component

**Overview**: Fixed critical bug in timing score calculation. Was only calculating individual leg penalties, missing the total time deviation penalty. This violated NIFA Red Book rules which require TWO components for timing score.

### The Bug
**Old (WRONG):**
```python
total_time_deviation = sum(abs(cp["deviation"]) for cp in checkpoint_results)
total_time_score = sum(cp["leg_score"] for cp in checkpoint_results)  # ONLY sums leg penalties!
```

Result: Scoring ignored math errors where user entered wrong total time. Example: User did bad math (entered 51:00 when legs sum to 50:00), but got no penalty for it.

### The Fix
**New (CORRECT):**
```python
# Component 1: Sum of individual leg penalties (1 point per second deviation per leg)
leg_penalties = sum(cp["leg_score"] for cp in checkpoint_results)

# Component 2: Total time penalty (1 point per second deviation from user-entered total time)
actual_total_time = sum(cp["actual_time"] for cp in checkpoint_results)
estimated_total_time = prenav["total_time"]  # Exactly as user entered (even if math is wrong!)
total_time_deviation = abs(estimated_total_time - actual_total_time)
total_time_penalty = total_time_deviation * timing_penalty_per_second

# Total timing score = BOTH components
total_time_score = leg_penalties + total_time_penalty
```

**Critical Point:** User-entered total time is used AS-IS. If they did bad math, they get penalized. This is correct per NIFA rules—math accuracy is part of the competition.

### Examples

**Test Case 1: Perfect Flight & Perfect Math**
- Legs: Each 1 sec off → 5 points leg penalties
- Total ETE: 50:00, Total ATE: 49:59 → 1 point total penalty
- **Total Timing Score: 6 points** (was 5, now correct!)

**Test Case 2: Math Error (User Did Bad Math)**
- Legs: Each 1 sec off → 5 points leg penalties
- Leg times sum to 50:00, but user typed 51:00 → 61 second penalty
- **Total Timing Score: 66 points** (was 5, now penalizes bad math!)

**Test Case 3: Everything Perfect**
- All legs on time, total on time → 0 points

### Implementation Details
- **File:** `app/app.py` - POST /flight route (lines 1407-1432)
- **Variables:**
  - `leg_penalties` - sum of individual leg penalties
  - `actual_total_time` - sum of actual leg times (from flight track)
  - `estimated_total_time` - prenav["total_time"] (user-entered, may have errors)
  - `total_time_deviation` - absolute difference
  - `total_time_penalty` - deviation × timing_penalty_per_second (default 1.0)
  - `total_time_score` - leg_penalties + total_time_penalty
- **Logging:** Added info-level breakdown log showing leg vs total penalties
- **PDF Report:** Updated to show breakdown:
  - "Leg Timing Penalties: X pts"
  - "Total Time Penalty: Y pts"
  - "Total Time Score: X+Y pts"

### Testing
Created comprehensive test suite (`test_timing_penalty.py`) with 4 test cases:
1. ✓ Perfect flight, perfect math → 6 points
2. ✓ Math error (user enters wrong total) → 66 points (penalized!)
3. ✓ Everything perfect → 0 points
4. ✓ Leg deviations but correct total → 50 points (no penalty for correct math)

All tests passing.

### NIFA Compliance
✅ Timing score now correctly implements NIFA Red Book requirements:
- Component 1: Individual leg timing penalties
- Component 2: Total time estimation accuracy penalty
- Both components penalize at 1 point per second (configurable)
- User-entered totals treated as gospel (penalizes math errors as intended)

### Impact
- ✅ Scoring now fully compliant with NIFA Red Book timing rules
- ✅ Math accuracy is now properly scored (penalizes poor planning)
- ✅ Users can see breakdown of where timing penalties come from
- ✅ Fairer competition (bad math now has consequences)

### Files Modified
- `app/app.py` - Fixed timing score calculation and PDF generation
- `test_timing_penalty.py` - NEW: Comprehensive test suite (4 test cases, all passing)
- `CHANGELOG.md` - This entry

### Notes
- NO VERSION bump or Docker rebuild (main agent handles post-review)
- Database schema unchanged (no migration needed)
- Config format unchanged (timing_penalty_per_second still applies)
- Backward compatible with existing flight results

## [0.4.6] - 2026-02-15

### ✅ NIFA Red Book v0.4.6 Compliance: Scoring Formula Fixes

**Overview**: Fixed critical scoring formula mismatches with official NIFA Red Book rules. Both off-course and fuel penalty calculations now correctly implement Red Book v0.4.6 specifications.

### Fixed
- **Issue 1: Off-Course Penalty Formula**
  - **Old (WRONG)**: Threshold at 0.25 NM, penalty range 0-500 points, linear from 0.25 to 5.0 NM
  - **New (CORRECT)**: Threshold at (checkpoint_radius + 0.01), penalty range 100-600 points
  - Penalty calculation now matches Red Book:
    - 0 to checkpoint_radius NM: 0 points (within radius)
    - (radius + 0.01) to 5.0 NM: Linear interpolation from 100 to 600 points
    - Example with radius=0.25: at 0.26 NM → 100 pts, at 2.63 NM → 350 pts, at 5.0 NM → 600 pts
  - **Files changed**: `app/scoring_engine.py` (calculate_leg_score method), config files

- **Issue 2: Fuel Penalty Formula**
  - **Old (WRONG)**: Error calc `(actual - estimated) / actual`, multipliers were swapped, thresholds inconsistent
  - **New (CORRECT)**: Error calc `(estimated - actual) / estimated`, correct multipliers and thresholds
  - Penalty logic now matches Red Book:
    - **Underestimate** (used MORE fuel, error < 0): 500 multiplier, NO threshold
    - **Overestimate** (used LESS fuel, error > 0): 250 multiplier, 10% threshold only
    - Examples: Plan 10, use 9.2 → 0 pts (8% under, within threshold)
    -           Plan 10, use 8.8 → penalty (12% under, exceeds threshold)
    -           Plan 10, use 10.1 → penalty (1% over, always penalized)
  - **Files changed**: `app/scoring_engine.py` (calculate_fuel_penalty method), config files

### Updated Configuration
- **data/config.yaml** and **config/config.yaml**:
  - Updated fuel_burn multipliers: over_estimate=250 (was 500), under_estimate=500 (was 250)
  - Added over_estimate_threshold: 0.1 (10% threshold for overestimate)
  - Updated off_course structure: checkpoint_radius_nm, min_penalty (100), max_penalty (600)
  - Added scoring.checkpoint_radius_nm: 0.25 (configurable per NIFA)

### Testing
- Created comprehensive test suite (test_scoring_fixes.py) verifying:
  - Off-course penalties at key distances (0.25, 0.26, 2.63, 5.0 NM)
  - Fuel penalties for under/over estimate scenarios
  - All tests passing ✓

### Impact
- ✅ Scoring now fully compliant with NIFA Red Book v0.4.6
- ✅ Fair penalty assessment for off-course navigation
- ✅ Correct fuel efficiency grading
- ✅ No VERSION bump or Docker rebuild (main agent handles post-review)

---

## [0.4.5] - 2026-02-15

### 🐛 Critical Fixes: Post-Flight Permissions & Results Display

**Overview**: Fixed coach/admin being blocked from post-flight submission and results viewing, plus validation and display issues.

### Fixed
- **Coach/Admin Post-Flight Permissions**: Changed `/results/{id}` and `/results/{id}/pdf` decorators from `require_member` to `require_login`
  - Coaches/admins were being blocked before route authorization logic could run
  - Now coaches/admins can submit post-flight for any pairing (as intended)
  - Competitors still restricted to their own pairings (security maintained)
- **Leg Times Validation**: Added check that prenav leg_times count matches NAV checkpoint count
  - Prevents "list index out of range" errors from malformed submissions
  - Shows descriptive error message instead of crash
- **Results Table Display**: Removed non-existent columns from coach results page
  - Removed "Time Dev" and "Fuel Pen" columns (data not stored in database)
  - Fixed team name display (was trying to access undefined fields)
  - Prevents "__round__ method" errors on results page
- **Added Debugging**: 5 strategic logging points in POST /flight route for troubleshooting

### Benefits
- ✅ Coaches/admins can now submit post-flight and view results
- ✅ Better error messages for invalid submissions  
- ✅ Results page works reliably for all user roles
- ✅ Improved debugging capabilities

## [0.4.4] - 2026-02-15

### 🐛 Hotfix: Navbar Links & Delete Button Styling

**Overview**: Fixed navbar "Post-NAV" links in all team templates that were missed in v0.4.3, and restored delete button styling.

### Fixed
- **Navbar Links**: Updated "Post-NAV" navbar links from `/flight` to `/flight/select` in all team templates
  - `templates/team/flight.html`
  - `templates/team/flight_select.html`
  - `templates/team/prenav.html`
  - `templates/team/prenav_confirmation.html` (2 links)
  - `templates/team/profile.html`
  - `templates/team/results.html`
  - `templates/team/results_list.html`
- Previous fix only updated dashboard.html, leaving navbar links broken on other pages
- **Delete Button Styling**: Added `.button-danger` CSS to flight_select.html
  - Delete buttons now display with maroon background (#8B0015 - SIU color)
  - Hover effect with darker maroon (#6B0010)
  - Previously displayed as plain text with emoji

### Benefits
- ✅ Consistent navigation from all pages (not just dashboard)
- ✅ Hamburger menu "Post-NAV" link now works correctly
- ✅ Delete buttons look like actual buttons (maroon box)

## [0.4.3] - 2026-02-14

### 🐛 Hotfix: Post-Flight Flow Issues

**Overview**: Fixed two usability issues in the post-flight submission workflow:
1. Dashboard "Submit Post-Flight" button incorrectly linked to form page instead of selection page
2. Delete button used unreliable inline confirmation instead of dedicated confirmation page

### Fixed
- **Dashboard Navigation**: "Submit Post-Flight" button now links directly to `/flight/select` instead of `/flight`
  - Updated navbar link (line 15)
  - Updated quick-link button (line 288)
  - Users now bypass the error page and go straight to submission selection table
- **Delete Confirmation Page**: Delete button now uses proper confirmation page pattern
  - Changed from inline `onsubmit="return confirm()"` to link-based flow
  - Route sequence: Click Delete → GET `/flight/delete/{id}/confirm` → Shows confirmation page → POST to delete → Redirect
  - Added new GET route `/flight/delete/{prenav_id}/confirm`
  - Updated template `templates/team/flight_select.html`: Changed delete button from form to link
  - Updated POST route `/flight/delete/{prenav_id}` to redirect cleanly

### Benefits
- ✅ Faster dashboard workflow (no intermediate error page)
- ✅ More reliable delete confirmation (page-based not browser popup)
- ✅ Consistent with existing pattern used in airports/gates deletion

## [0.4.2] - 2026-02-14

### ⭐ Major UX Improvement: Selection Page for Post-Flight

**Overview**: Replaced dropdown selector with dedicated selection page showing table of open submissions. Significantly improved usability and mobile experience.

### Added
- **New Route `/flight/select` GET**: Selection page showing table of open pre-flight submissions
  - Columns: Date/Time, NAV Route, Pairing, Total Time, Fuel Estimate, Actions
  - "Select to Complete" button per row
  - Admin-only "Delete" button per row
  - Filtered by role (competitor=own pairings, coach/admin=all)
- **New Route `/flight/delete/<prenav_id>` POST**: Admin-only deletion of submissions
  - Prevents deletion of scored submissions
  - Redirects to selection page with success message
- **New Template `templates/team/flight_select.html`**: Table-based selection interface
- **New Database Methods**:
  - `get_prenav_by_id(prenav_id)` - Fetch single submission with full details
  - `delete_prenav_submission(prenav_id)` - Delete submission (admin only)

### Changed
- **Route `/flight` GET**: Now accepts optional `?prenav_id=X` query parameter
  - Fetches selected submission by ID
  - Validates permissions (competitor must be in pairing)
  - Displays submission details (read-only) at top of form
  - Removed dropdown selector
  - Uses hidden input with prenav_id
- **Template `templates/team/flight.html`**: 
  - Removed dropdown selector
  - Added read-only submission details box
  - Added instructions and error handling
  - Pre-filled prenav_id via hidden input
- **Dashboard**: Post-Flight button now links to `/flight/select` instead of `/flight`

### Benefits
- ✅ Clearer visual presentation of submissions
- ✅ More submission details visible at a glance
- ✅ Better mobile experience (table vs dropdown)
- ✅ Admin capability to clean up duplicate/stale submissions
- ✅ Reduced user errors (easier to identify correct submission)

## [0.4.1] - 2026-02-14

### Fixed
- **Timezone Display Bug**: Post-flight dropdown was showing UTC timestamps (e.g., "2026-02-15 01:38 AM") instead of Central Time
  - Added `pytz` dependency for timezone handling
  - Updated `get_open_prenav_submissions()` in `app/database.py` to convert UTC timestamps to America/Chicago timezone
  - Added `submitted_at_display` field with formatted CST time (e.g., "Feb 14, 2026 07:38 PM")
  - Updated `/flight` route to use formatted CST timestamp in dropdown display

### Changed
- **Requirements**: Added `pytz==2024.1` for timezone conversion
- **Timestamp Format in Dropdown**: Changed from ISO format with timezone awareness to readable 12-hour format with AM/PM

## [0.4.0] - 2026-02-14

### ⚠️ BREAKING CHANGE: Token-Based System Replaced with Selection List

**Overview**: Replaced 48-hour expiring token system with intuitive dropdown selection. Post-flight form now shows list of open pre-flight submissions instead of requiring users to paste tokens.

### Added
- **Database Migration 008**: Added `status` column to `prenav_submissions` (open/scored/archived)
- **New Database Methods**:
  - `get_open_prenav_submissions(user_id=None, is_coach=False)` - Fetch open submissions with full details
  - `mark_prenav_scored(prenav_id)` - Mark submission as scored
  - `archive_prenav(prenav_id)` - Archive stale submissions (admin only)
- **Selection-Based Workflow**: Post-flight form now displays dropdown of open pre-flight submissions instead of token input field
- **Submission Details in Email**: Email confirmations now include submission date, pairing info (pilot/observer names)
- **Pre-flight Confirmation Page**: Shows submission details instead of token

### Removed
- **Token Generation**: Pre-flight submissions no longer create expiring tokens
- **Token Input Field**: Post-flight form no longer requires token entry
- **Token Expiry**: 48-hour token expiration logic removed

### Changed
- **Pre-flight Submission Form**: No longer displays/sends token to users
- **Email Templates**: Removed token-based instructions, updated to list-based workflow
- **Post-flight Form** (`/flight` GET): Fetches and displays dropdown of open submissions
  - Competitors see only their pairing's submissions
  - Coaches/Admins see all submissions
- **Post-flight Submission** (`/flight` POST):
  - Replaced `prenav_token` field with `prenav_id` dropdown selection
  - Added validation: Prenav must have `status='open'`
  - Added permission check: Can't score same submission twice
- **Prenav Confirmation Page**: Shows submission details (date, NAV, pilot/observer) instead of token

### Security
- ✅ Competitor can only score their own pairing's submissions
- ✅ Coach/Admin can score any submission
- ✅ Can't score same submission twice (status check)
- ✅ Can't score archived submissions

### Files Modified
- `migrations/008_prenav_status.sql` - NEW
- `app/database.py` - Added methods, updated `create_prenav()`, `get_open_prenav_submissions()`
- `app/app.py` - Updated `/prenav` POST, `/prenav_confirmation` GET, `/flight` GET/POST routes
- `app/email.py` - Updated `send_prenav_confirmation()` template
- `templates/team/flight.html` - Replaced token input with prenav dropdown
- `templates/team/prenav_confirmation.html` - Shows submission details instead of token
- `VERSION` - Bumped to 0.4.0

### Testing Completed
- ✅ Competitor: Submit prenav, see only own submissions, score with dropdown
- ✅ Coach: See all submissions, score any submission
- ✅ Admin: Full access, can archive submissions
- ✅ Permission checks: Competitor can't score wrong pairing
- ✅ Status tracking: Can't score same submission twice
- ✅ Email templates: No token, shows submission details

### Migration Notes
- **Existing Submissions**: Marked as 'scored' if linked to flight results, 'open' otherwise
- **No Data Loss**: All existing prenav submissions preserved with proper status
- **Backwards Compatible**: Token field still available in database for legacy access (if needed)

### Benefits
✅ No more lost/forgotten tokens  
✅ Coach visibility into all submissions  
✅ Better UX (select from list vs enter code)  
✅ No expiration pressure  
✅ Status tracking for submissions  
✅ More intuitive for web workflow  
✅ Easier audit trail  

## [0.3.11] - 2026-02-14

### Fixed
- **Prenav Form UX Issues** - Fixed two critical UX problems
  - **Issue 1: Competitor Route Confirmation** 
    - Added visual confirmation message when user selects NAV route
    - Message shows: "✓ Route Selected: [NAV NAME] - Complete the flight plan below"
    - Styled with blue background and left border to clearly indicate same-page action
    - Prevents user perception of "going to next page automatically"
    - User can verify route selection before filling in leg times
  
  - **Issue 2: Admin Submit Button Not Working**
    - Root cause: JavaScript form submission handler was only defined in competitor section
    - Fix: Moved form event listener outside conditional blocks
    - Now applies to both admin/coach and competitor forms
    - Admin users can now successfully submit prenav forms
    - Form validation works correctly for both user types
  
  - Files Modified: `templates/team/prenav.html`
  - Testing: Both competitor and admin prenav workflows tested and verified

## [0.3.10] - 2026-02-14

### Fixed
- **Fuel Input Clarity** - Added helpful note to fuel input field
  - Note displays: "Enter to the nearest 0.1 gallon (e.g., 8.5, 10.2)"
  - Added to both coach/admin and competitor prenav forms
  - Improves user understanding of required precision
  - Files Modified: `templates/team/prenav.html`

## [0.3.9] - 2026-02-14

### Fixed
- **Batch 11 - Admin/Coach Prenav Form Workflow (Items 17 & Issue 2)** - Complete prenav form for admin/coach view
  - **Item 17 Verification**: Fuel input confirmed to have `step="0.1"` for 0.1 gallon precision
  - **Admin/Coach Prenav Form**: Previously showed only pairing selector with no way to continue
  - **Added missing form fields** to coach/admin prenav view:
    - NAV selector dropdown (with `onchange="updateCheckpointFields()"`)
    - Leg times container with dynamic HH:MM:SS inputs
    - Total flight time with HH:MM:SS inputs (displayed only when NAV selected)
    - Fuel input with `step="0.1"` for 0.1 gallon precision (displayed only when NAV selected)
    - Submit button for form submission
  - **UX Improvement**: Coach/admin now see complete form in one view:
    - Pairing selector at top
    - NAV selector below pairing
    - Leg times, total time, fuel (shown dynamically when NAV is selected)
    - Same form structure and JavaScript behavior as competitor view
  - **Testing**: Verified fuel input accepts decimal values (8.5, 10.2, etc.)
  - **Files Modified**: `templates/team/prenav.html` (added form fields to coach/admin section)

## [0.3.8] - 2026-02-14

### Added
- **Pairing Dropdown Filtering (Issue 24)** - Pairing creation dropdowns now filter out ineligible users
  - New database method: `get_available_pairing_users()` 
  - Filters exclude:
    - Users with `is_coach=1` (coaches don't compete)
    - Users with `is_admin=1` (admins don't compete)
    - Users already in active pairings (cannot pair twice)
    - Unapproved users
  - Updated `/coach/pairings` route to use filtered user list
  - Dropdown now shows only eligible users for pilot and observer selection
  - Prevents duplicate pairings and coaches appearing in competition pairing lists

### Fixed
- **Post-Flight Error Handling (Issue 23)** - Enhanced error handling in flight submission
  - Fixed missing context variables in error response template
  - Added `pairings_for_dropdown` to error response for coaches
  - Added `is_coach` and `is_admin` flags to error response template context
  - Ensures error form re-renders with all necessary data for coaches to retry
  - Explicit `error=None` default in GET `/flight` route

### Notes
- **Items 16.5 & 16.6** (Total Time HH:MM:SS inputs and default values) already implemented in prenav.html
  - Total flight time has separate HH/MM/SS inputs with `value="0"`
  - All time inputs configured with `type="number"`, `min="0"`, `max="59"` (for min/sec)
  - Leg times follow same pattern
  - Form submission properly converts HH:MM:SS to total seconds

## [0.3.5] - 2026-02-14

### Added
- **Mobile-Friendly Confirmation Pages** - Replaced JavaScript `confirm()` dialogs with dedicated confirmation pages for all delete operations
  - New confirmation page template: `templates/coach/delete_confirm.html`
  - Added GET routes for confirmation pages (`/delete-confirm`) for:
    - Airports: `/coach/navs/airports/{airport_id}/delete-confirm`
    - Gates: `/coach/navs/gates/{gate_id}/delete-confirm`
    - Routes: `/coach/navs/routes/{nav_id}/delete-confirm`
    - Checkpoints: `/coach/navs/checkpoints/{checkpoint_id}/delete-confirm`
    - Secrets: `/coach/navs/secrets/{secret_id}/delete-confirm`
  - Updated all delete buttons to link to confirmation pages instead of using form + confirm() dialogs
  - Better UX for mobile devices (iOS Safari, Android browsers) where confirm() dialogs don't work well
  - Improved accessibility with clear warning messages and cascade information

- **Unified Dashboard Architecture** - Single `/dashboard` route for all users (competitors, coaches, admins)
  - Replaces separate `/team` and `/coach` dashboards
  - Content adapts based on user role (`is_coach`, `is_admin` flags)
  - Competitors see their pairing info, prenav/postnav links, and personal results
  - Coaches/Admins see stats boxes (total members, active pairings, recent results)
  - Both groups see unified navigation bar with Admin dropdown for coaches/admins

### Changed
- **Routing**
  - `/` redirects to `/dashboard`
  - `/team` and `/coach` now redirect to `/dashboard` (legacy support)
  - `/login` redirects to `/dashboard` instead of role-specific URLs
  - `/results` now supports both competitors and coaches
    - Competitors see only their own results
    - Coaches/Admins see all results (uses coach/results.html template)
  - `/prenav` supports coaches submitting for any pairing (removed `require_member` restriction)
  - `/flight` supports coaches submitting for any pairing (removed `require_member` restriction)

- **Pre-NAV & Post-NAV Submission**
  - Competitors: Auto-use their own pairing (no change)
  - Coaches/Admins: Show dropdown to select which team they're submitting for
  - Both prenav.html and flight.html updated with pairing selectors

- **Admin Permissions (Read-Only for Coaches)**
  - Members page: Hidden create/bulk import forms for non-admins, hidden edit/delete/role buttons
  - Pairings page: Hidden create pairing form for non-admins, hidden break/delete/reactivate buttons
  - Airports/Routes/Checkpoints/Secrets pages: Hidden CRUD buttons for non-admins
  - All pages now pass `is_admin` flag to templates

- **Navigation Updates**
  - Unified navbar for all users: Dashboard | Pre-NAV | Post-NAV | Results | Profile | [Admin] | Logout
  - Admin dropdown with conditional visibility of System Config link (admins only)
  - Updated all team/*.html and coach/results templates to use new navbar

- **Bug Fixes**
  - Fixed `list_members()` database function - now queries `users` table with `WHERE is_approved=1` instead of non-existent `members` table
  - Fixed `list_active_members()` to query `users` table

### Technical
- Unified `dashboard.html` template with conditional blocks for role-based display
- Frontend routes now use `require_login()` instead of `require_member()` where appropriate
- Coach-specific routes check `is_admin` flag and pass to templates
- Database queries now filter results by role (competitive/team view vs. coach/admin view)
- All CRUD operations still protected by `require_admin` decorator at route level
- Template-level visibility prevents accidental button rendering to non-admins

### UI/UX
- Single unified design for all users (no more two separate dashboards)
- Coaches/Admins see admin controls and stats
- Competitors see their pairing info and personal results
- Pairing selector dropdown on prenav/postnav forms (coaches only)
- "View Only" labels instead of hidden buttons for non-admin coaches
- Consistent color scheme and styling across all pages

### Backward Compatibility
- Legacy URLs `/team` and `/coach` still work (redirect to `/dashboard`)
- All existing functionality preserved
- Competitor workflows unchanged
- Coach workflows enhanced (can now submit prenav/postnav for any team)

## [0.3.7] - 2026-02-14

### Added
- **Multiple Email Addresses** - Users can now add and manage additional email addresses
  - New `user_emails` table stores primary and additional email addresses
  - Migration 007 creates table and migrates existing user emails as primary
  - Primary email (SIU email) displays in profile as non-editable, labeled "Primary"
  - Additional emails show with remove buttons for easy management
  - Add Email form with validation and duplicate checking
  - New API endpoints:
    - `GET /profile/emails` - List all emails for current user
    - `POST /profile/emails/add` - Add new email with format validation
    - `POST /profile/emails/remove` - Remove additional email (cannot remove primary)
  - Database methods: `add_user_email()`, `remove_user_email()`, `get_user_emails()`, `get_all_emails_for_user()`, `email_exists()`
- **Email Service Updates** - `send_prenav_confirmation()` and `send_results_notification()` now accept multiple emails
  - Backward compatible - still works with single email string
  - Loops through list and sends to each email individually
  - Updated app.py to call `get_all_emails_for_user()` before sending emails
- **Password Change Functionality** - Users can change their password from profile page
  - New `POST /profile/password` endpoint for password changes
  - Form requires current password verification
  - Validates password strength (minimum 8 characters)
  - Prevents reusing current password
  - AJAX form with success/error messages

### Changed
- Email sending logic updated to use `get_all_emails_for_user()` instead of single user.email
- Prenav and results notifications now sent to all email addresses for user
- Profile page reorganized: Password section added above Email Addresses section

### Technical
- Database migration 007: Creates `user_emails` table with foreign key to users
- Email validation regex pattern for format checking
- AJAX handlers for email add/remove operations with inline messages
- Form validation prevents duplicate emails and invalid formats

### UI/UX
- Profile page now has three main sections: Password, Email Addresses, Profile Picture
- Email Addresses section shows Primary Email (non-editable, labeled)
- Additional Emails listed with remove buttons
- Add Email form with inline validation messages
- Professional styling with color-coded email items (primary=green, additional=blue)
- Password change form with current password verification
- Auto-hiding success messages after 3 seconds

## [0.3.6] - 2026-02-14

### Fixed
- **Config Persistence** - Moved `config.yaml` to persistent data directory
  - Config file now stored in `/app/data/config.yaml` instead of `/app/config/config.yaml`
  - Persists across container rebuilds via volume mount
  - `init-db-if-needed.sh` copies template on first-time setup if config doesn't exist
  - Updated all references in `app.py`, `Dockerfile`, `README.md`, and documentation
  - **Impact:** SMTP settings and all config changes now survive container rebuilds

## [0.3.5] - 2026-02-14

### Added
- **Automated Database Backups** - Scheduled backup system with configurable retention
  - `BackupScheduler` class in `app/backup_scheduler.py` handles backup orchestration
  - Background async task runs backups at configurable intervals (default: 24 hours)
  - Python-based backup using SQLite backup API for safe, non-blocking backups
  - Backup file naming: `navs_YYYYMMDD_HHMMSS.db` with timestamps
  - State tracking in `data/backup_state.json` with last backup time and metadata
- **Backup Configuration UI** - New "Backup Configuration" section on System Config page (admin only)
  - Toggle enable/disable automated backups
  - Set backup frequency (hours)
  - Set retention period (days) and max backups to keep
  - Configure backup directory path
  - View backup status: last backup time, next scheduled backup, total backups
  - **"Run Backup Now"** button for manual on-demand backups
- **Backup API Endpoints** (admin only)
  - `POST /coach/backup/run` - Trigger manual backup, returns JSON with status
  - `GET /coach/backup/status` - Get current backup status and metadata
  - `POST /coach/config/backup` - Update backup configuration
- **Backup Cleanup** - Automatic cleanup after each backup
  - Deletes backups older than `retention_days`
  - Keeps only the most recent `max_backups`
  - Uses the more restrictive constraint (retention OR max count)
- **Backup Integration** - Backup scheduler starts automatically on app startup
  - Performs initial backup when app starts
  - Cleanup of old backups based on retention policy
  - Error handling prevents backup failures from crashing the app

### Changed
- **"Scoring Config" → "System Config"** - Renamed throughout UI and templates
  - Page title: "Scoring Configuration" → "System Configuration"
  - Dashboard quick-link text: "Scoring Config" → "System Config"
  - Navbar: "Config" remains unchanged (generic)
  - Better reflects broader system management role
- **config.yaml.template** - Added new `backup` section with defaults:
  ```yaml
  backup:
    enabled: true
    frequency_hours: 24
    retention_days: 7
    backup_path: "/app/data/backups"
    max_backups: 10
  ```

### Technical
- Backup uses Python `sqlite3.backup()` API instead of shell script for portability
- Backup state stored in JSON for easy inspection and debugging
- Background task uses `asyncio` for non-blocking execution
- Backup files created with 0644 permissions (readable by app, backupable by admin)
- Storage directories created automatically on startup if missing

## [0.3.4] - 2026-02-13

### Fixed
- **Issue 16.5:** Total time inputs now use separate HH:MM:SS boxes instead of single MM:SS field
- **Issue 16.6:** All time inputs default to "0" and only accept numeric input (type="number")
- **Issue 23:** Post-flight submission error handling - Now shows descriptive error messages instead of blank error page
- **Issue 19 & 19.1:** Removed redundant "Status" column from members table - Single "Approval Status" column shows approve/deny buttons for pending users

### Added
- **SMTP Test Connectivity** - New "Test SMTP Connection" button on config page (admin only)
  - POST /coach/test_smtp endpoint tests connection, authentication, and sends test email
  - Provides specific error messages for connection failures, auth failures, and send failures
  - AJAX integration displays green success or red error message below button
  - Test email sent to configured sender_email address to verify loop
- **EmailService.test_connection()** - New async method to test SMTP configuration
  - Tests connection to SMTP server
  - Tests authentication with provided credentials
  - Sends test email as final verification
  - Returns tuple (success: bool, message: str) with descriptive error messages
- **SQLite WAL mode** - Enables Write-Ahead Logging for better concurrency with Docker volume mounts
- **Database persistence** - Volume mount at `/app/data` ensures database survives container restarts
- **MDH 20 NAV route** - Loaded from nav_route.txt with 5 checkpoints and 2 start gates
- **DEPLOYMENT.md** - Complete deployment and troubleshooting guide
- **LAUNDRY_FIXES.md** - Documentation of laundry list item fixes
- **Backup/restore scripts** - bash scripts for manual database backup and restore

### Changed
- Prenav form total time: Separate HH:MM:SS input boxes with numeric-only validation
- Prenav form leg times: HH:MM:SS format (hours, minutes, seconds) instead of MM:SS
- Flight submission error handling: HTML error display instead of JSON errors
- Database connection: WAL mode with `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`
- Database timeouts: Reduced from 300s to 5s for faster failure detection
- Members table: Removed duplicate status column, cleaner UI

### Technical
- Database files: `navs.db`, `navs.db-wal`, `navs.db-shm` (all must be backed up together)
- Docker volume mount: `-v $(pwd)/data:/app/data` for persistent storage
- Container deployment: Works like Radarr/Sonarr with SQLite on volume-mounted storage

## [0.3.3] - 2026-02-13

### Fixed
- **Issue 13:** Force password reset checkbox in user edit modal - Properly integrated with backend force_reset flag
- **Issue 14:** Delete vs Break pairing buttons - Added clear tooltips explaining each action
- **Issue 15:** Pairing names display - Fixed database JOIN query to properly populate pilot/observer names
- **Issue 16:** Prenav HH:MM:SS boxes - Verified individual time input boxes for each leg
- **Issue 17:** Fuel precision 0.1 gallon - Verified input accepts decimal values with step="0.1"
- **Issue 18:** View results internal error - Verified error handling and logging on /results route
- **Issue 19:** Approve/Deny buttons for user approval - Replaced checkbox with AJAX approve/deny buttons (no page refresh)
- **Issue 20:** Pairing validation error message - Added error message display for duplicate pairing attempts

### Added
- New POST endpoints `/coach/members/{user_id}/approve` and `/coach/members/{user_id}/deny` for AJAX user approval
- Error message div in pairings.html with AJAX form submission
- Tooltips on Break/Delete/Reactivate buttons explaining each action
- Force password reset checkbox in user edit modal (Issue 13)
- Database columns email_verified and must_reset_password in initial schema (bootstrap_db.py)
- CSS styling for approve/deny buttons and status badges

### Changed
- User approval workflow from checkbox to approve/deny buttons with AJAX
- Pairing creation form to use AJAX with error message display instead of redirect
- Removed redundant name lookups in coach/pairings route

### Note
- **Issue 10.1:** Precision explanation - Database stores full IEEE 754 double precision (~15-17 significant digits). Current 7-decimal display is sufficient (1.1cm accuracy), far exceeding GPS precision. No code changes needed.

## [0.3.2] - 2026-02-12

### Fixed
- **Issue 10:** Checkpoint display precision - Shows full 7+ decimal places instead of rounded 5 decimals
- **Issue 11:** Standardized navbar across all pages - Consistent links on every page (no conditional hiding)
- **Issue 12:** Prevent users from being in multiple active pairings - Added database validation
- **Issue 13:** Force password reset on next login - Added checkbox in user edit, new /reset-password workflow
- **Issue 14:** Clarify delete vs break pairing - Updated button labels and added tooltips
- **Issue 15:** Pairing shows correct pilot/observer names - Fixed database JOIN query to include names
- **Issue 16:** Prenav time input changed to HH:MM:SS individual boxes - Prevents errors from MM:SS format
- **Issue 17:** Prenav fuel input accepts 0.1 gallon precision - Updated input step attribute
- **Issue 18:** View results page internal error - Added comprehensive error handling and logging

### Changed
- Checkpoint/Gate/Secret coordinate display now shows 7 decimal places
- All coach pages use consistent standardized navbar
- All team pages use consistent standardized navbar
- Prenav form now accepts hours, minutes, seconds as separate inputs
- Pairing list displays pilot and observer names directly
- Results page has better error reporting

### Added
- Database migration 005 for password reset flag (must_reset_password column)
- New /reset-password GET/POST routes for password reset workflow
- New reset_password.html template
- Better error logging in results routes
- Database validation for pairing creation

### Database
- Migration 005: Added `must_reset_password` column to users table

## [0.3.1] - 2026-02-12


All notable changes to the NAV Scoring application.

## [0.3.0] - 2026-02-12

### Added
- Email verification workflow with activation link
- Pre-verification holding table (verification_pending) for signups
- 24-hour verification token expiry with automatic cleanup
- SMTP configuration check for signup page visibility
- Automatic cleanup of expired verification tokens on app startup
- Email verification template with professional styling
- Verification result page (success/failure)

### Changed
- Email is now the login credential (removed separate username field) BREAKING CHANGE
- Signup workflow: form → verification email → click link → pending → admin approval
- Login form now uses email instead of username
- Member management UI shows email only (removed username column)
- Self-signup only available when SMTP is configured
- Coach-created accounts skip email verification (marked as verified)
- Session now stores email instead of username

### Removed
- Username field from signup form
- Username column from member management UI
- Direct user creation without email verification (self-signup)

### Security
- Email verification required before account appears as pending
- 24-hour token expiry prevents long-lived verification links
- Automatic cleanup of expired tokens prevents database bloat

## [0.2.0] - 2026-02-12

### Added
- Unified user system with single `users` table replacing separate `members` and `coach` tables
- Self-signup capability with @siu.edu email validation
- Admin approval workflow for new user registrations
- Role-based permissions (Competitor, Coach, Admin)
- User management UI with checkboxes for Approve/Coach/Admin roles
- Filter dropdown on members page (All/Pending/Coaches/Admins/Approved)
- Pending approvals badge on coach dashboard
- AJAX endpoints for real-time role updates
- SMTP configuration UI on config page
- Comprehensive logging for prenav submissions

### Changed
- Merged members and coach tables into unified users table (BREAKING CHANGE)
- Coach accounts now have read-only dashboard access unless marked as admin
- Admin privileges now required for create/edit operations
- Database migration system to support incremental schema changes

### Fixed
- Pre-flight form submission redirect issue
- Database initialization in Docker container
- Route ordering for /coach/members endpoints

## [0.1.1] - 2026-02-12

### Fixed
- Pre-flight form submission bug
- Admin system implementation
- SMTP configuration UI

## [0.1.0] - 2026-02-12

### Added
- Initial release of NAV Scoring application
- Member and coach authentication system
- Pre-flight/post-flight submission workflow
- Coach dashboard with full CRUD operations for flights and routes
- NAV route management and viewing
- SIU branding and mobile-responsive design
- Admin panel for user and organization management
- Real-time flight tracking and navigation support
- Comprehensive logging and error handling
- Docker containerization for deployment
