-- Activity Logging System
-- Tracks all user actions for accountability and debugging

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    user_email TEXT,
    user_name TEXT,
    activity_category TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    activity_details TEXT,
    related_entity_type TEXT,
    related_entity_id INTEGER,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_log_category ON activity_log(activity_category);
CREATE INDEX IF NOT EXISTS idx_activity_log_type ON activity_log(activity_type);
