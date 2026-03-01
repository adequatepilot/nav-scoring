-- Add ip_address column to activity_log if it doesn't exist
-- For databases that had activity_log table created before ip_address was added

ALTER TABLE activity_log ADD COLUMN ip_address TEXT;
