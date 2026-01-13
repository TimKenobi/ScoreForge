"""
Configuration module for ScoreForge.

Handles application settings, paths to external tools,
and user preferences.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
import platform


def get_default_lilypond_path() -> Optional[str]:
    """Attempt to find LilyPond installation."""
    system = platform.system()
    
    common_paths = []
    if system == "Darwin":  # macOS
        common_paths = [
            "/usr/local/bin/lilypond",
            "/opt/homebrew/bin/lilypond",
            "/Applications/LilyPond.app/Contents/Resources/bin/lilypond",
        ]
    elif system == "Linux":
        common_paths = [
            "/usr/bin/lilypond",
            "/usr/local/bin/lilypond",
        ]
    elif system == "Windows":
        common_paths = [
            r"C:\Program Files\LilyPond\usr\bin\lilypond.exe",
            r"C:\Program Files (x86)\LilyPond\usr\bin\lilypond.exe",
        ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def get_default_musescore_path() -> Optional[str]:
    """Attempt to find MuseScore installation."""
    system = platform.system()
    
    common_paths = []
    if system == "Darwin":  # macOS
        common_paths = [
            "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
            "/Applications/MuseScore 3.app/Contents/MacOS/mscore",
        ]
    elif system == "Linux":
        common_paths = [
            "/usr/bin/mscore",
            "/usr/bin/musescore",
            "/usr/local/bin/mscore",
        ]
    elif system == "Windows":
        common_paths = [
            r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
            r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe",
        ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


@dataclass
class OMRConfig:
    """Configuration for OMR processing."""
    engine: str = "oemer"  # "oemer" or "audiveris"
    use_gpu: bool = True
    deskew_enabled: bool = True
    contrast_enhancement: bool = True


@dataclass
class ExportConfig:
    """Configuration for export settings."""
    midi_velocity: int = 80
    midi_tempo: int = 120
    pdf_paper_size: str = "letter"  # "letter", "a4"
    pdf_staff_size: int = 18
    include_lyrics_in_pdf: bool = True


@dataclass
class GUIConfig:
    """Configuration for GUI settings."""
    theme: str = "system"  # "light", "dark", "system"
    notation_zoom: float = 1.0
    recent_files_max: int = 10
    window_width: int = 1400
    window_height: int = 900
    show_toolbar: bool = True
    show_statusbar: bool = True


@dataclass
class Config:
    """
    Main configuration class for Sheet Music Scanner.
    
    Handles loading/saving settings and manages paths to external tools.
    """
    
    # Paths to external tools
    lilypond_path: Optional[str] = field(default_factory=get_default_lilypond_path)
    musescore_path: Optional[str] = field(default_factory=get_default_musescore_path)
    
    # Sub-configurations
    omr: OMRConfig = field(default_factory=OMRConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)
    
    # Recent files
    recent_files: list = field(default_factory=list)
    
    # Application directories
    _config_dir: Path = field(default_factory=lambda: Path.home() / ".sheet_music_scanner")
    _config_file: Path = field(default=None)
    
    def __post_init__(self):
        """Initialize configuration paths."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.json"
        
        # Create temp directory for processing
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def temp_dir(self) -> Path:
        """Get temporary directory for processing files."""
        return self._config_dir / "temp"
    
    @property
    def cache_dir(self) -> Path:
        """Get cache directory."""
        cache = self._config_dir / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        return cache
    
    def save(self) -> None:
        """Save configuration to disk."""
        data = {
            "lilypond_path": self.lilypond_path,
            "musescore_path": self.musescore_path,
            "omr": asdict(self.omr),
            "export": asdict(self.export),
            "gui": asdict(self.gui),
            "recent_files": self.recent_files[-self.gui.recent_files_max:],
        }
        
        with open(self._config_file, "w") as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from disk or create default."""
        config = cls()
        
        if config._config_file.exists():
            try:
                with open(config._config_file, "r") as f:
                    data = json.load(f)
                
                config.lilypond_path = data.get("lilypond_path", config.lilypond_path)
                config.musescore_path = data.get("musescore_path", config.musescore_path)
                
                if "omr" in data:
                    config.omr = OMRConfig(**data["omr"])
                if "export" in data:
                    config.export = ExportConfig(**data["export"])
                if "gui" in data:
                    config.gui = GUIConfig(**data["gui"])
                
                config.recent_files = data.get("recent_files", [])
                
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Warning: Could not load config file: {e}")
        
        return config
    
    def add_recent_file(self, filepath: str) -> None:
        """Add a file to recent files list."""
        filepath = str(filepath)
        
        # Remove if already exists
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        # Add to front
        self.recent_files.insert(0, filepath)
        
        # Trim to max length
        self.recent_files = self.recent_files[:self.gui.recent_files_max]
        
        self.save()
    
    def has_lilypond(self) -> bool:
        """Check if LilyPond is available."""
        return self.lilypond_path is not None and os.path.exists(self.lilypond_path)
    
    def has_musescore(self) -> bool:
        """Check if MuseScore is available."""
        return self.musescore_path is not None and os.path.exists(self.musescore_path)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reset_config() -> None:
    """Reset the global configuration to defaults."""
    global _config
    _config = Config()
    _config.save()
