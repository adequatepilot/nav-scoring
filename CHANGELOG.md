# Changelog

All notable changes to the NAV Scoring application.

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
