-- Migration: Add admin flag to coach accounts

ALTER TABLE coach ADD COLUMN is_admin INTEGER DEFAULT 0;
