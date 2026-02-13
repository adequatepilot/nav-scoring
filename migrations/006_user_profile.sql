-- Migration: Add profile picture column to users table
-- Issue 21: User profile page with picture upload

ALTER TABLE users ADD COLUMN profile_picture_path TEXT DEFAULT NULL;
