-- Migration: Unified User System
-- Merges members and coach tables into a single users table with role flags
-- BREAKING CHANGE: This migration restructures user management

-- Create new unified users table IF NOT EXISTS
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_coach INTEGER DEFAULT 0,  -- Can access coach dashboard
    is_admin INTEGER DEFAULT 0,  -- Full permissions (create/edit everything)
    is_approved INTEGER DEFAULT 0,  -- For self-signup approval
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_coach ON users(is_coach);
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users(is_admin);
CREATE INDEX IF NOT EXISTS idx_users_is_approved ON users(is_approved);
