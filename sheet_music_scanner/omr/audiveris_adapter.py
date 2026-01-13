"""
Audiveris adapter for OMR processing.

Provides integration with Audiveris via CLI for high-quality
optical music recognition.
"""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Callable
import logging
import os

logger = logging.getLogger(__name__)


class AudiverisAdapter:
    """
    Adapter for Audiveris OMR engine.
    
    Audiveris is a Java-based OMR system that provides high accuracy
    for scanned sheet music. It must be called via CLI/subprocess.
    """
    
    def __init__(
        self,
        audiveris_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ):
        """
        Initialize Audiveris adapter.
        
        Args:
            audiveris_path: Path to Audiveris JAR or executable.
                           If None, will search in common locations.
            progress_callback: Optional callback for progress updates
        """
        self.audiveris_path = audiveris_path or self._find_audiveris()
        self.progress_callback = progress_callback
    
    def _report_progress(self, message: str, percent: int) -> None:
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(message, percent)
    
    def _find_audiveris(self) -> Optional[str]:
        """
        Search for Audiveris installation.
        
        Returns:
            Path to Audiveris, or None if not found
        """
        # Check if 'audiveris' command is available
        audiveris_cmd = shutil.which("audiveris")
        if audiveris_cmd:
            return audiveris_cmd
        
        # Common installation locations
        import platform
        system = platform.system()
        
        possible_paths = []
        
        if system == "Darwin":  # macOS
            possible_paths = [
                "/Applications/Audiveris.app/Contents/MacOS/Audiveris",
                os.path.expanduser("~/Applications/Audiveris.app/Contents/MacOS/Audiveris"),
            ]
        elif system == "Linux":
            possible_paths = [
                "/usr/local/bin/audiveris",
                "/opt/audiveris/bin/Audiveris",
                os.path.expanduser("~/audiveris/bin/Audiveris"),
            ]
        elif system == "Windows":
            possible_paths = [
                r"C:\Program Files\Audiveris\Audiveris.exe",
                r"C:\Program Files (x86)\Audiveris\Audiveris.exe",
            ]
        
        # Also check for JAR file
        jar_paths = [
            os.path.expanduser("~/audiveris/audiveris.jar"),
            "/opt/audiveris/audiveris.jar",
        ]
        
        for path in possible_paths + jar_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def is_available(self) -> bool:
        """
        Check if Audiveris is available.
        
        Returns:
            True if Audiveris can be executed
        """
        if not self.audiveris_path:
            return False
        
        if not os.path.exists(self.audiveris_path):
            return False
        
        # Try running version check
        try:
            if self.audiveris_path.endswith('.jar'):
                result = subprocess.run(
                    ["java", "-jar", self.audiveris_path, "-help"],
                    capture_output=True,
                    timeout=10
                )
            else:
                result = subprocess.run(
                    [self.audiveris_path, "-help"],
                    capture_output=True,
                    timeout=10
                )
            return True
        except Exception:
            return False
    
    def process(self, image_path: Path) -> Optional[Path]:
        """
        Process an image through Audiveris.
        
        Args:
            image_path: Path to the input image
            
        Returns:
            Path to the generated MusicXML file, or None on failure
        """
        if not self.is_available():
            logger.error("Audiveris is not available")
            return None
        
        try:
            self._report_progress("Running Audiveris...", 30)
            
            # Create output directory
            output_dir = image_path.parent / "audiveris_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Build command
            if self.audiveris_path.endswith('.jar'):
                cmd = [
                    "java", "-jar", self.audiveris_path,
                    "-batch",
                    "-export",
                    "-output", str(output_dir),
                    str(image_path)
                ]
            else:
                cmd = [
                    self.audiveris_path,
                    "-batch",
                    "-export", 
                    "-output", str(output_dir),
                    str(image_path)
                ]
            
            # Run Audiveris
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            self._report_progress("Processing complete...", 70)
            
            if result.returncode != 0:
                logger.error(f"Audiveris failed: {result.stderr}")
                # Continue anyway - sometimes Audiveris returns non-zero but still produces output
            
            # Find output MusicXML file
            # Audiveris creates files like: input_name/input_name.mxl
            stem = image_path.stem
            possible_outputs = [
                output_dir / stem / f"{stem}.mxl",
                output_dir / stem / f"{stem}.musicxml",
                output_dir / f"{stem}.mxl",
                output_dir / f"{stem}.musicxml",
            ]
            
            for output_path in possible_outputs:
                if output_path.exists():
                    return output_path
            
            # Search for any MusicXML file in output directory
            for ext in ["*.mxl", "*.musicxml", "*.xml"]:
                files = list(output_dir.rglob(ext))
                if files:
                    return files[0]
            
            logger.error("Could not find Audiveris output file")
            return None
            
        except subprocess.TimeoutExpired:
            logger.error("Audiveris timed out")
            return None
        except Exception as e:
            logger.exception("Error running Audiveris")
            return None
    
    def get_model_info(self) -> dict:
        """
        Get information about Audiveris.
        
        Returns:
            Dictionary with model information
        """
        return {
            "engine": "audiveris",
            "available": self.is_available(),
            "path": self.audiveris_path,
        }
