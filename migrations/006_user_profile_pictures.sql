-- Migration: Add profile picture support to users table
-- Adds profile_picture_path column to store the filename/path of uploaded profile pictures

ALTER TABLE users ADD COLUMN profile_picture_path TEXT;

-- Create index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_users_profile_picture ON users(profile_picture_path);
