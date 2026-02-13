-- Migration 005: Force Password Reset on Next Login
-- Adds a flag to users table for forcing password reset

ALTER TABLE users ADD COLUMN must_reset_password INTEGER DEFAULT 0;
