# Profile Picture Display - Testing Guide (Issue 22)

## Implementation Summary

Profile picture display has been implemented on the team dashboard with the following components:

### 1. Database Migration
- **File**: `migrations/006_user_profile_pictures.sql`
- **Change**: Added `profile_picture_path` column to users table
- **Status**: Column already added to existing database

### 2. File Storage
- **Directory**: `static/profile_pictures/`
- **Note**: Created and excluded from git in .gitignore

### 3. Profile Picture Upload
- **Route**: `POST /profile/picture`
- **Features**:
  - Accepts JPG, PNG, GIF, WebP files (max 5MB)
  - Stores files as `{user_id}_{timestamp}.ext`
  - Updates user's `profile_picture_path` in database
  - Returns JSON response with success status

### 4. Profile Page
- **Route**: `GET /profile`
- **Features**:
  - Displays user's profile with current picture (or initials)
  - Upload form with drag-and-drop support
  - Live preview before upload
  - Success/error messages

### 5. Dashboard Display
- **Route**: `GET /team`
- **Changes**:
  - Shows profile pictures for pilot and observer
  - Falls back to initials in colored circles if no picture
  - Consistent color assignment per user
  - Circular avatars (90px) side-by-side layout

### 6. Helper Functions
- `get_initials(name)`: Extracts first letter of first and last name
- `get_avatar_color(name)`: Assigns consistent color based on name hash
- Colors: 6 different gradient colors for variety

## Testing Instructions

### Prerequisites
- Docker container must be restarted to pick up code changes
- Test database is available at `data/navs.db`

### Test Users
- **Pilot**: pilot1@siu.edu / pass123 (Alex Johnson)
- **Observer**: observer1@siu.edu / pass123 (Taylor Brown)
- **Pairing**: Active pairing exists between these two users

### Test Steps

1. **Restart Docker Container** (if needed)
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

2. **Login as Pilot**
   - URL: http://localhost:8000/login
   - Email: pilot1@siu.edu
   - Password: pass123
   - Should redirect to /team dashboard

3. **Verify Dashboard Display**
   - Dashboard should show pairing info: "Alex Johnson" and "Taylor Brown"
   - Two circular avatars should appear to the right
   - Avatars show initials: "AJ" and "TB"
   - Colors should be consistent

4. **Upload Profile Picture**
   - Click "Profile" link in navbar
   - Should see profile page with user info and upload form
   - Drag and drop or click to select an image
   - Click "Upload Picture" button
   - Should see success message
   - Avatar should update with the picture

5. **Verify Dashboard Update**
   - Return to dashboard (/team)
   - Pilot's avatar should show the uploaded picture
   - Observer's avatar still shows initials (no picture uploaded yet)

6. **Test Observer Profile**
   - Logout and login as observer
   - Email: observer1@siu.edu
   - Password: pass123
   - Profile page should show "TB" initials
   - Upload a different picture for observer
   - Dashboard should show both pictures side by side

7. **Verify Picture URLs**
   - Pictures stored at: `/static/profile_pictures/{user_id}_{timestamp}.ext`
   - Serve correctly from browser
   - Files persist across sessions

## Database Verification

```sql
-- Check users table has profile_picture_path
PRAGMA table_info(users);

-- Verify column exists
SELECT id, name, profile_picture_path FROM users;

-- Check for uploaded pictures
SELECT id, name, profile_picture_path FROM users WHERE profile_picture_path IS NOT NULL;
```

## File Structure

```
static/profile_pictures/
  ├── 3_1739491234.jpg    # pilot1's picture (user_id=3)
  └── 4_1739491567.png    # observer1's picture (user_id=4)
```

## CSS Features

- **Avatar Size**: 90px circular avatars
- **Colors**: 6 different gradient colors
- **Fallback**: Initials displayed when no picture
- **Layout**: Side-by-side when paired
- **Responsive**: Adapts to mobile screens

## Known Limitations

- Pictures are not deleted when user is deleted (manual cleanup recommended)
- No picture cropping/resizing on server (browser resizes)
- Pictures stored on server filesystem (not cloud storage)

## Troubleshooting

If pictures don't display:
1. Check Docker container is restarted
2. Verify `static/profile_pictures/` directory exists
3. Check file permissions (should be readable by web server)
4. Verify database has `profile_picture_path` column
5. Check browser console for 404 errors

If upload fails:
1. Verify file is valid image (JPG, PNG, GIF, WebP)
2. Check file size is < 5MB
3. Verify `static/profile_pictures/` directory is writable
4. Check Django error logs for details
