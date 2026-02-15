-- Migration 009: Add penalty breakdown columns to flight_results
-- Adds detailed penalty calculation fields for comprehensive breakdown display

-- Add new columns to flight_results table
ALTER TABLE flight_results ADD COLUMN leg_penalties REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN total_time_penalty REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN total_time_deviation REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN estimated_total_time REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN actual_total_time REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN total_off_course REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN fuel_error_pct REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN estimated_fuel_burn REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN checkpoint_radius REAL DEFAULT 0.25;
