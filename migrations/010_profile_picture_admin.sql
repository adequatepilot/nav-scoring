-- Migration: Profile Picture Admin Controls
-- Adds can_modify_profile_picture flag to control user permissions

ALTER TABLE users ADD COLUMN can_modify_profile_picture INTEGER DEFAULT 1;

-- Create index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_users_can_modify_profile ON users(can_modify_profile_picture);
