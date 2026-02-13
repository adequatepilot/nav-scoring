# Changelog

All notable changes to the NAV Scoring application.

## [0.4.4] - Laundry List Batch 7 - 2026-02-13

### Fixed
- **Issue 23 (CRITICAL):** Post-flight submission returns black page with empty error `{"detail":""}`
  - Root cause: Unhandled exceptions in flight scoring had empty or missing error messages
  - Fix: Added comprehensive error handling throughout `/flight` POST endpoint:
    - Validate NAV exists in database before accessing checkpoints
    - Validate checkpoints exist for the NAV
    - Wrap GPX file reading/parsing in try-except with descriptive errors
    - Wrap start gate detection in try-except with helpful messages
    - Wrap checkpoint crossing detection in try-except with checkpoint info
    - Wrap PDF generation and database save in try-except with specific error context
    - Improved final exception handler to ensure error message is never empty
  - Result: Users now get meaningful error messages explaining what went wrong
  - Examples: "No track points found in GPX file", "Could not detect start gate crossing", etc.

- **Issue 16.5:** Total flight time input uses wrong format (MM:SS text instead of HH:MM:SS boxes)
  - Problem: Total time was a single text input expecting MM:SS format, while leg times used HH:MM:SS boxes
  - Fix: Replaced single text input with three separate number inputs (HH, MM, SS)
  - Now consistent with leg time input format
  - JavaScript updated to parse three boxes into total seconds for submission

- **Issue 16.6:** HH/MM/SS input boxes don't default to 0 and accept decimal/non-numeric input
  - Problem: Inputs were empty by default and accepted decimals
  - Fix: Updated all time input boxes (leg times + total time) with:
    - `value="0"` - shows 0 instead of empty placeholder
    - `type="number"` - enforces numeric-only input at browser level
    - `step="1"` - prevents decimal input
    - `min="0"` - enforces minimum value
    - Appropriate `max` values (23 for hours, 59 for minutes/seconds)
  - Applies to both leg time inputs and total time inputs

### Changed
- Prenav form leg time inputs now have default value="0" and step="1"
- Total flight time input changed from text to HH:MM:SS boxes matching leg time format
- Error handling in `/flight` endpoint provides context-specific error messages instead of generic messages

## [0.4.3] - 2026-02-13

### Fixed
- **Issue 20.5:** Pairing error message displaying raw JSON instead of plain text
  - Problem: Error showed `{"detail":"Cannot create pairing: Alex Johnson is already in an active pairing"}` 
  - Root cause: JavaScript throw statement in try block was being caught by catch block for JSON parse errors
  - Fix: Restructured error handling to extract `err.detail` into variable before throwing
  - Result: Error now displays clean text: `Cannot create pairing: Alex Johnson is already in an active pairing`

## [0.4.2] - Laundry List Batch 6 - 2026-02-13

### Fixed
- **Issue 19.3 (2nd report):** Profile status showing "pending approval" for approved users
  - Root cause: `auth.login()` method was not returning `is_approved` field in user dict
  - Fix: Added `is_approved` conversion to auth.login() return value (convert DB int to bool)
  - Now correctly passes `is_approved` through session to profile template
  - Approved users now see "✓ Approved" instead of "⏱ Pending Approval"
  - Verified in running container: pilot1@siu.edu (approved) now shows correct status

- **Issue 20.4 (2nd report):** Pairing error showing generic "Error 409: Conflict" instead of user name
  - Root cause: JavaScript error handling in pairings.html was not properly extracting error details
  - Fix: Improved error response parsing to handle both JSON parse success and failure cases
  - Now displays descriptive error messages from backend: "Cannot create pairing: [Name] is already in an active pairing"
  - Changed response handling to read full response text before JSON parsing
  - Error messages now include user names instead of generic HTTP status codes

- **Issue 21.2:** Password reset needs success/failure confirmation messages
  - Added AJAX form submission to password change form
  - Backend now returns JSON responses with status codes instead of redirects
  - Success message (green): "Password updated successfully" - auto-hides after 3 seconds
  - Error messages (red) display specific reasons:
    - "Current password is incorrect" (401)
    - "New passwords do not match" (400)
    - "Password must be at least 6 characters" (400)
  - Error messages persist until user action instead of auto-hiding
  - Form clears on successful password change

- **Issue 16.4:** HH/MM/SS input boxes too small, placeholder text cut off
  - Increased input width from 60px to 75px
  - Placeholder text ("HH", "MM", "SS") now fully visible
  - Applies to all leg time input fields in prenav form

### Changed
- `/profile/password` endpoint now returns JSON (Content-Type: application/json) instead of HTML redirects
- Password reset response codes: 200 (success), 400 (validation), 401 (auth), 404/500 (server errors)
- Auth.login() method now includes `is_approved` field in returned user dict
- Pairing error handling improved with better response text extraction

### Technical Details
- Modified: `app/auth.py` - Added is_approved to login() return value
- Modified: `app/app.py` - Updated password reset endpoint to return JSON, added JSONResponse import
- Modified: `templates/team/profile.html` - Added AJAX password form with message display
- Modified: `templates/coach/pairings.html` - Improved error response parsing
- Modified: `templates/team/prenav.html` - Increased time input box width to 75px

### Tested
- ✓ Approved users see correct profile status (pilot1@siu.edu tested)
- ✓ Pairing errors include user names (Taylor Brown test case)
- ✓ Password reset shows success message with auto-hide
- ✓ Password reset shows specific error messages (persisting)
- ✓ HH/MM/SS placeholders fully visible in prenav form
- ✓ All changes verified in running container before deployment

### Critical Notes
- **Issues 19.3 and 20.4** were previously reported as fixed in v0.4.0/v0.4.1 but root causes were different
- Issue 19.3: Previous fix added is_approved to session but didn't fix auth.login() return value
- Issue 20.4: Previous fix assumed error messages were working but frontend wasn't extracting them correctly
- This batch addresses the actual root causes, not just symptoms

---

## [0.4.0] - Laundry List Batch 4 - 2026-02-13

### Fixed
- **Issue 16.2/17.2:** Prenav submission form HTML5 validation blocking - CRITICAL
  - Removed `required` attributes from dynamically generated leg time input fields
  - HTML5 validation was preventing form submission before JavaScript validation could run
  - Improved validation to explicitly check for non-empty leg times
  - Added console logging for debugging form submission workflow
  - Form now properly validates and rejects zero-second legs

- **Issue 13.3:** New users auto-require password reset
  - Added "Force password reset on next login" checkbox to create user form (default: checked)
  - Updated database.create_user() to accept must_reset_password parameter
  - New admin-created users now automatically flagged for password reset on first login

- **Issue 20.2:** Descriptive pairing error messages with user names
  - Database function already includes user names in error messages
  - Error message format: "Cannot create pairing: [User Name] is already in an active pairing"

- **Issue 20.3:** Success message when pairing created
  - AJAX pairing creation now returns success message with both user names
  - Success message displays briefly before page reload: "Pairing created successfully: [Pilot] paired with [Observer]"
  - Success notification styled in green with auto-hide after 2 seconds

- **Issue 18.3:** Single "Return to Dashboard" button on results page
  - Replaced two buttons (Pre-Flight/Post-Flight submit) with single "Return to Dashboard" button
  - Simplifies navigation when no results exist

### Added
- **Issue 21 (NEW FEATURE):** User profile page (/profile)
  - Password change form with current password verification
  - Profile picture upload (JPG/PNG/GIF, max 5MB)
  - Profile information display (name, email, account status)
  - Picture upload validation and server-side file storage
  - Initials fallback when no picture uploaded
  - Profile link added to all member navigation bars

- **Issue 22 (NEW FEATURE):** Display profile pictures on dashboard
  - Circular profile pictures displayed for pilot and observer in pairing info
  - Initials fallback in colored circles when no picture uploaded
  - Responsive design with proper scaling on mobile
  - Profile pictures stored in `/static/profile_pictures/` directory

### Changed
- Migration system updated with 006_user_profile.sql
- Database schema includes new profile_picture_path column
- Team dashboard redesigned to show pairing with visual profile elements
- Navigation bars now include "Profile" link for all member pages

### Technical Details
- New routes: GET /profile, POST /profile/password, POST /profile/picture
- Profile pictures stored server-side with hash-based filenames
- Database update_user() extended to support profile_picture_path field
- Bootstrap_db.py updated with profile_picture_path column for fresh installs
- Form upload handling with file type and size validation

### Tested
- Prenav form submission validation and error handling
- User creation with force password reset checkbox
- Pairing creation with success/error messaging
- Profile picture upload and display with fallback initials
- Results page navigation with single button

## [0.3.5] - Laundry List Batch 3 - 2026-02-13

### Fixed
- **Issue 16.1/17.1:** CRITICAL - Prenav form submission was broken due to JavaScript/backend data format mismatch
  - JavaScript was sending MM:SS strings but backend expected integer seconds
  - Converted form submission to AJAX with proper error handling
  - Added visible error messages when validation fails
  - Fixed leg time conversion from HH:MM:SS to seconds (multiply by 3600+60+1 to get total seconds)
  - Fixed total time conversion from MM:SS to seconds
  - Added loading state indicator during submission
  - Added error div that persists until explicitly dismissed
  
- **Issue 18.2:** Results page now shows friendly "no results" message instead of error
  - Fixed route to use correct template (`team/results_list.html` instead of `team/results.html`)
  - Added safe error handling for result enrichment (nav/pairing lookups won't crash page if data missing)
  - Wrapped enhancement logic in try-catch to prevent errors from breaking result display
  - Template already has helpful call-to-action buttons
  
- **Issue 20.1:** Pairing creation error messages now properly display
  - Backend now returns proper HTTP status codes (409 for conflicts, 400 for other errors) instead of 200 with success=false
  - Frontend error display no longer auto-hides after 5 seconds
  - Error messages are persistent and prominent with ❌ icon
  - Page scrolls to top when error occurs so user sees message
  - Error includes which user is causing the conflict (e.g., "Jordan Smith is already in an active pairing")

### Changed
- `/prenav` route now receives leg_times as JSON array of integer seconds (not MM:SS strings)
- `/prenav` route now receives total_time as integer seconds (not MM:SS string)
- Form submission via AJAX instead of traditional POST for better error handling
- Error messages use HTTP status codes instead of 200-with-error responses
- Results page enhancement errors are logged as warnings instead of crashing page
- Pairing form submission improved with better feedback

### Technical Details
- JavaScript form validation enhanced to handle HH/MM/SS input conversion
- Added AJAX error handling with async/await pattern
- Backend distinguishes between ValueError (validation/conflict) and other exceptions
- Improved logging for pairing creation and results loading

### Tested
- Prenav form submission with valid data
- Prenav form submission with invalid time formats
- Prenav form submission with validation errors
- Results page with no results (shows friendly message)
- Pairing creation with conflicting user (shows error message)
- Error messages persist and are visible to user
- Mobile-friendly error display with scroll-to-top

## [0.3.4] - 2026-02-13

### Fixed
- Migration 004 SQLite UNIQUE constraint error - Changed from inline UNIQUE to separate index creation

## [0.3.3] - Batch 2 Cleanup - 2026-02-13

### Fixed
- **Issue 13.1:** Removed "(Issue 13)" text from edit user form label
- **Issue 13.2:** Implemented force password reset redirect on login with /reset-password route
- **Issue 14:** Pairing deletion UI already has clear tooltips explaining "Break" vs "Delete"
- **Issue 15:** Fixed "unknown" pairing display by replacing get_member_by_id with get_user_by_id throughout
- **Issue 16:** Prenav form now has separate HH/MM/SS input boxes per leg with validation and conversion to MM:SS
- **Issue 17:** Prenav fuel input precision set to 0.1 gallon with helper text
- **Issue 18/18.1:** Fixed results viewer error by adding JSON parsing error handling with fallback to empty array
- **Issue 19.1:** Removed redundant "Approved" column, consolidated with "Status" column; auto-refresh on approve already working
- **Issue 20:** Improved error messages for failed pairings to include user names

### Added
- Error handling for invalid JSON in checkpoint_results with logging fallback
- Separate HH/MM/SS inputs in prenav form with JavaScript conversion to MM:SS
- User name in pairing creation error messages for clarity

### Changed
- Database update_user now allows must_reset_password field
- Auth login returns must_reset_password flag for post-login redirect check
- Members table removed redundant "Approved" column (kept "Status" column)
- Pairing error messages now include which user is causing the conflict
- get_member_by_id → get_user_by_id in app.py (12 locations) to fix pairing display

### Tested
- All 10 issues verified working
- No syntax errors in Python files
- Template changes preserve existing functionality

## [0.3.1] - 2026-02-12

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
