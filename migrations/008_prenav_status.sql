-- Add status column to prenav_submissions (for v0.4.0 token replacement)
-- Valid statuses: 'open', 'scored', 'archived'

ALTER TABLE prenav_submissions ADD COLUMN status TEXT DEFAULT 'open';

-- Mark existing submissions as 'scored' if they have flight results
UPDATE prenav_submissions SET status = 'scored' 
WHERE id IN (SELECT prenav_id FROM flight_results);

-- All others remain 'open'
UPDATE prenav_submissions SET status = 'open' 
WHERE id NOT IN (SELECT prenav_id FROM flight_results);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_prenav_status ON prenav_submissions(status);
CREATE INDEX IF NOT EXISTS idx_prenav_pairing_status ON prenav_submissions(pairing_id, status);
