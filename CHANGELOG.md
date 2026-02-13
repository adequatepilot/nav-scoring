# Changelog

All notable changes to the NAV Scoring application.

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
