-- Migration: Add support for multiple email addresses per user
-- Creates user_emails table to support additional emails beyond the primary SIU email

CREATE TABLE IF NOT EXISTS user_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    email TEXT NOT NULL UNIQUE,
    is_primary INTEGER DEFAULT 0,  -- 1 for primary (SIU email), 0 for additional
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_user_emails_user_id ON user_emails(user_id);
CREATE INDEX IF NOT EXISTS idx_user_emails_email ON user_emails(email);
CREATE INDEX IF NOT EXISTS idx_user_emails_is_primary ON user_emails(is_primary);

-- Populate user_emails table with existing user emails (primary)
-- This runs only on first migration, subsequent runs do nothing
INSERT INTO user_emails (user_id, email, is_primary, created_at)
SELECT id, email, 1, CURRENT_TIMESTAMP
FROM users
WHERE email NOT IN (SELECT email FROM user_emails WHERE is_primary = 1)
ON CONFLICT(email) DO NOTHING;
