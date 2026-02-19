-- Add PDF path column to navs table for storing NAV packet PDFs

ALTER TABLE navs ADD COLUMN pdf_path TEXT DEFAULT NULL;

-- Create indexes if needed
CREATE INDEX IF NOT EXISTS idx_navs_airport ON navs(airport_id);
