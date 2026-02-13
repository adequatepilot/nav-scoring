-- Migration 004: Email Verification System
-- Adds email verification workflow before account becomes pending
-- BREAKING CHANGE: Username removed entirely, email is now the login credential

-- Add email verification columns to users table
ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN verification_token TEXT;
ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP;

-- Add unique index for verification_token (SQLite doesn't allow UNIQUE on ALTER TABLE ADD COLUMN)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);

-- Create verification_pending table for pre-signup verification
CREATE TABLE IF NOT EXISTS verification_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    verification_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_verification_pending_token ON verification_pending(verification_token);
CREATE INDEX IF NOT EXISTS idx_verification_pending_email ON verification_pending(email);
CREATE INDEX IF NOT EXISTS idx_verification_pending_expires_at ON verification_pending(expires_at);
