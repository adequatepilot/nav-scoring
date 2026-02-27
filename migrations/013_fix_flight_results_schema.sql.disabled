-- Ensure all flight_results columns exist (fixes "Invalid justification" errors)

-- Check if columns exist, add if missing
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS leg_penalties REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS total_time_penalty REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS total_time_deviation REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS estimated_total_time REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS actual_total_time REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS total_off_course REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS fuel_error_pct REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS estimated_fuel_burn REAL DEFAULT 0;
ALTER TABLE flight_results ADD COLUMN IF NOT EXISTS checkpoint_radius REAL DEFAULT 0.25;
