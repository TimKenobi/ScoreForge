"""
Auto-Save and Recovery Module.

Provides automatic periodic saving and crash recovery.
"""

from __future__ import annotations

import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, List
import logging

logger = logging.getLogger(__name__)


class AutoSaveManager:
    """
    Manages automatic saving and crash recovery.
    
    Features:
    - Periodic auto-save to backup location
    - Crash recovery detection
    - Multiple backup generations
    - Configurable save interval
    """
    
    def __init__(
        self,
        backup_dir: Path,
        save_interval: int = 60,  # seconds
        max_backups: int = 5,
    ):
        """
        Initialize auto-save manager.
        
        Args:
            backup_dir: Directory for backup files
            save_interval: Seconds between auto-saves
            max_backups: Maximum number of backup generations to keep
        """
        self.backup_dir = Path(backup_dir)
        self.save_interval = save_interval
        self.max_backups = max_backups
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Recovery info file
        self._recovery_file = self.backup_dir / "recovery_info.json"
        
        # Auto-save state
        self._save_callback: Optional[Callable[[], bytes]] = None
        self._load_callback: Optional[Callable[[bytes], None]] = None
        self._enabled = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._dirty = False
        self._current_file: Optional[Path] = None
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Check for crash recovery on init
        self._has_recovery = self._check_for_recovery()
    
    @property
    def has_recovery_data(self) -> bool:
        """Check if there's data to recover from a crash."""
        return self._has_recovery
    
    def set_callbacks(
        self,
        save_callback: Callable[[], bytes],
        load_callback: Callable[[bytes], None]
    ) -> None:
        """
        Set callbacks for saving and loading.
        
        Args:
            save_callback: Function that returns current document as bytes
            load_callback: Function that loads document from bytes
        """
        self._save_callback = save_callback
        self._load_callback = load_callback
    
    def start(self) -> None:
        """Start auto-save timer."""
        if self._enabled:
            return
        
        self._enabled = True
        self._stop_event.clear()
        self._write_recovery_info(active=True)
        
        def auto_save_loop():
            while not self._stop_event.wait(timeout=self.save_interval):
                if self._dirty and self._save_callback:
                    try:
                        self._perform_auto_save()
                    except Exception as e:
                        logger.error(f"Auto-save failed: {e}")
        
        self._thread = threading.Thread(target=auto_save_loop, daemon=True)
        self._thread.start()
        logger.info(f"Auto-save started (interval: {self.save_interval}s)")
    
    def stop(self) -> None:
        """Stop auto-save timer."""
        self._enabled = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        
        # Clean exit - remove recovery marker
        self._write_recovery_info(active=False)
        logger.info("Auto-save stopped")
    
    def mark_dirty(self) -> None:
        """Mark document as modified (needs saving)."""
        self._dirty = True
    
    def mark_clean(self) -> None:
        """Mark document as clean (saved)."""
        self._dirty = False
    
    def set_current_file(self, filepath: Optional[Path]) -> None:
        """Set the current file being edited."""
        self._current_file = filepath
    
    def force_save(self) -> bool:
        """
        Force an immediate auto-save.
        
        Returns:
            True if save succeeded
        """
        if self._save_callback:
            try:
                self._perform_auto_save()
                return True
            except Exception as e:
                logger.error(f"Force save failed: {e}")
        return False
    
    def _perform_auto_save(self) -> None:
        """Perform the actual auto-save."""
        if not self._save_callback:
            return
        
        # Get document data
        data = self._save_callback()
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"autosave_{self._session_id}_{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        # Save to backup
        with open(backup_path, 'wb') as f:
            f.write(data)
        
        # Update recovery info
        self._write_recovery_info(
            active=True,
            last_save=timestamp,
            backup_file=str(backup_path),
            original_file=str(self._current_file) if self._current_file else None
        )
        
        # Rotate old backups
        self._rotate_backups()
        
        self._dirty = False
        logger.debug(f"Auto-saved to {backup_path}")
    
    def _rotate_backups(self) -> None:
        """Remove old backup files beyond max_backups."""
        pattern = f"autosave_{self._session_id}_*.backup"
        backups = sorted(self.backup_dir.glob(pattern), reverse=True)
        
        for old_backup in backups[self.max_backups:]:
            try:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
            except Exception as e:
                logger.warning(f"Failed to remove old backup: {e}")
    
    def _write_recovery_info(
        self,
        active: bool,
        last_save: Optional[str] = None,
        backup_file: Optional[str] = None,
        original_file: Optional[str] = None
    ) -> None:
        """Write recovery info file."""
        info = {
            "active": active,
            "session_id": self._session_id,
            "last_save": last_save,
            "backup_file": backup_file,
            "original_file": original_file,
            "timestamp": datetime.now().isoformat(),
        }
        
        with open(self._recovery_file, 'w') as f:
            json.dump(info, f, indent=2)
    
    def _check_for_recovery(self) -> bool:
        """Check if there's recovery data from a crash."""
        if not self._recovery_file.exists():
            return False
        
        try:
            with open(self._recovery_file, 'r') as f:
                info = json.load(f)
            
            # If previous session was active (didn't clean exit), we have recovery
            if info.get("active", False):
                backup_file = info.get("backup_file")
                if backup_file and Path(backup_file).exists():
                    logger.info(f"Found recovery data from session {info.get('session_id')}")
                    return True
        
        except Exception as e:
            logger.warning(f"Error checking recovery info: {e}")
        
        return False
    
    def get_recovery_info(self) -> Optional[dict]:
        """Get information about available recovery data."""
        if not self._recovery_file.exists():
            return None
        
        try:
            with open(self._recovery_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def recover(self) -> Optional[bytes]:
        """
        Recover data from last crash.
        
        Returns:
            Recovered document data, or None if recovery failed
        """
        info = self.get_recovery_info()
        if not info:
            return None
        
        backup_file = info.get("backup_file")
        if not backup_file or not Path(backup_file).exists():
            return None
        
        try:
            with open(backup_file, 'rb') as f:
                data = f.read()
            
            logger.info(f"Recovered data from {backup_file}")
            return data
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return None
    
    def clear_recovery(self) -> None:
        """Clear recovery data (user chose not to recover)."""
        self._has_recovery = False
        
        # Clean up backup files from previous session
        info = self.get_recovery_info()
        if info:
            old_session = info.get("session_id", "")
            pattern = f"autosave_{old_session}_*.backup"
            for backup in self.backup_dir.glob(pattern):
                try:
                    backup.unlink()
                except Exception:
                    pass
        
        # Clear recovery info
        self._write_recovery_info(active=False)
    
    def get_backup_list(self) -> List[dict]:
        """
        Get list of all available backups.
        
        Returns:
            List of backup info dicts with path, timestamp, size
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("autosave_*.backup"):
            try:
                stat = backup_file.stat()
                backups.append({
                    "path": backup_file,
                    "name": backup_file.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                })
            except Exception:
                pass
        
        return sorted(backups, key=lambda x: x["modified"], reverse=True)
    
    def restore_backup(self, backup_path: Path) -> Optional[bytes]:
        """
        Restore a specific backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Restored document data, or None if failed
        """
        try:
            with open(backup_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return None


# Singleton instance
_autosave_manager: Optional[AutoSaveManager] = None


def get_autosave_manager() -> AutoSaveManager:
    """Get the global auto-save manager."""
    global _autosave_manager
    if _autosave_manager is None:
        from sheet_music_scanner.config import get_config
        config = get_config()
        _autosave_manager = AutoSaveManager(
            backup_dir=config.cache_dir / "autosave",
            save_interval=60,
            max_backups=5
        )
    return _autosave_manager
