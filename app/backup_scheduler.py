"""
Backup Scheduler for NAV Scoring System
Handles automated database backups and retention policies.
"""

import logging
import asyncio
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sqlite3

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages automated database backups and cleanup."""
    
    def __init__(self, config: Dict[str, Any], db_path: str):
        """
        Initialize backup scheduler.
        
        Args:
            config: Backup configuration dict with keys:
                - enabled: bool
                - frequency_hours: int
                - retention_days: int
                - backup_path: str
                - max_backups: int
            db_path: Path to the database file
        """
        self.config = config
        self.db_path = Path(db_path)
        self.backup_path = Path(config.get("backup_path", "data/backups"))
        self.state_file = self.backup_path / "backup_state.json"
        self.enabled = config.get("enabled", True)
        self.frequency_hours = config.get("frequency_hours", 24)
        self.retention_days = config.get("retention_days", 7)
        self.max_backups = config.get("max_backups", 10)
        
        # Create backup directory if it doesn't exist
        self.backup_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"BackupScheduler initialized: {self.backup_path}")
    
    def load_state(self) -> Dict[str, Any]:
        """Load backup state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading backup state: {e}")
        
        return {
            "last_backup": None,
            "last_backup_file": None,
            "next_scheduled": None,
            "total_backups": 0
        }
    
    def save_state(self, state: Dict[str, Any]):
        """Save backup state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.debug(f"Backup state saved: {state}")
        except Exception as e:
            logger.error(f"Error saving backup state: {e}")
    
    def get_backup_filename(self) -> str:
        """Generate timestamped backup filename."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"navs_{timestamp}.db"
    
    def backup_database(self) -> Optional[str]:
        """
        Perform database backup using Python sqlite3.
        
        Returns:
            Backup filename if successful, None if failed
        """
        try:
            if not self.db_path.exists():
                logger.error(f"Database file not found: {self.db_path}")
                return None
            
            backup_filename = self.get_backup_filename()
            backup_file_path = self.backup_path / backup_filename
            
            logger.info(f"Starting backup: {self.db_path} -> {backup_file_path}")
            
            # Open source database in read-only mode
            source_conn = sqlite3.connect(str(self.db_path))
            source_conn.row_factory = sqlite3.Row
            
            try:
                # Create backup database connection
                backup_conn = sqlite3.connect(str(backup_file_path))
                
                try:
                    # Use SQLite's backup API for safe copying
                    source_conn.backup(backup_conn)
                    logger.info(f"Database backup completed: {backup_filename}")
                    return backup_filename
                finally:
                    backup_conn.close()
            finally:
                source_conn.close()
        
        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            return None
    
    def cleanup_old_backups(self):
        """
        Clean up old backups based on retention_days and max_backups.
        Deletes whichever constraint is more restrictive.
        """
        try:
            backup_files = sorted(
                self.backup_path.glob("navs_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            logger.debug(f"Found {len(backup_files)} backup files")
            
            now = datetime.utcnow()
            cutoff_date = now - timedelta(days=self.retention_days)
            
            # Determine which files to keep
            files_to_keep = []
            files_to_delete = []
            
            for i, backup_file in enumerate(backup_files):
                # Check age
                file_mtime = datetime.utcfromtimestamp(backup_file.stat().st_mtime)
                is_too_old = file_mtime < cutoff_date
                
                # Check max backups
                exceeds_max = i >= self.max_backups
                
                if is_too_old or exceeds_max:
                    files_to_delete.append(backup_file)
                else:
                    files_to_keep.append(backup_file)
            
            # Delete old files
            for backup_file in files_to_delete:
                try:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file.name}")
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup_file.name}: {e}")
            
            logger.info(f"Cleanup: kept {len(files_to_keep)}, deleted {len(files_to_delete)}")
        
        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
    
    def run_backup(self) -> bool:
        """
        Run a backup and cleanup.
        
        Returns:
            True if backup was successful
        """
        if not self.enabled:
            logger.debug("Backup is disabled")
            return False
        
        try:
            # Perform backup
            backup_filename = self.backup_database()
            if not backup_filename:
                logger.error("Backup failed")
                return False
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            # Update state
            state = self.load_state()
            state["last_backup"] = datetime.utcnow().isoformat()
            state["last_backup_file"] = backup_filename
            state["next_scheduled"] = (
                datetime.utcnow() + timedelta(hours=self.frequency_hours)
            ).isoformat()
            
            # Count backups
            backup_files = list(self.backup_path.glob("navs_*.db"))
            state["total_backups"] = len(backup_files)
            
            self.save_state(state)
            logger.info(f"Backup completed successfully: {backup_filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error in run_backup: {e}", exc_info=True)
            return False
    
    async def start_background_task(self):
        """Start background backup task."""
        if not self.enabled:
            logger.info("Backup is disabled, not starting background task")
            return
        
        logger.info(f"Starting backup scheduler (every {self.frequency_hours} hours)")
        
        while True:
            try:
                # Wait for next backup time
                await asyncio.sleep(self.frequency_hours * 3600)
                
                # Run backup in a non-blocking way
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.run_backup)
                
                if result:
                    logger.info("Scheduled backup completed")
                else:
                    logger.warning("Scheduled backup failed")
            
            except asyncio.CancelledError:
                logger.info("Backup scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Backup scheduler error: {e}", exc_info=True)
                # Continue on error, don't crash the scheduler
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def get_status(self) -> Dict[str, Any]:
        """Get current backup status."""
        state = self.load_state()
        
        # Get backup file list
        backup_files = list(self.backup_path.glob("navs_*.db"))
        
        return {
            "enabled": self.enabled,
            "last_backup": state.get("last_backup"),
            "last_backup_file": state.get("last_backup_file"),
            "next_scheduled": state.get("next_scheduled"),
            "total_backups": len(backup_files),
            "frequency_hours": self.frequency_hours,
            "retention_days": self.retention_days,
            "max_backups": self.max_backups,
            "backup_path": str(self.backup_path)
        }
