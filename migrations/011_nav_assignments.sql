-- Migration: NAV Assignment System
-- Tracks NAV assignments for practice throughout semester

CREATE TABLE IF NOT EXISTS nav_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nav_id INTEGER NOT NULL,
    pairing_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER NOT NULL,
    completed_at TIMESTAMP,
    semester TEXT,
    notes TEXT,
    FOREIGN KEY (nav_id) REFERENCES navs(id) ON DELETE CASCADE,
    FOREIGN KEY (pairing_id) REFERENCES pairings(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(nav_id, pairing_id, semester)
);

CREATE INDEX IF NOT EXISTS idx_nav_assignments_nav ON nav_assignments(nav_id);
CREATE INDEX IF NOT EXISTS idx_nav_assignments_pairing ON nav_assignments(pairing_id);
CREATE INDEX IF NOT EXISTS idx_nav_assignments_status ON nav_assignments(completed_at);
CREATE INDEX IF NOT EXISTS idx_nav_assignments_semester ON nav_assignments(semester);
