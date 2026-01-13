"""
Oemer adapter for OMR processing.

Provides integration with the oemer library for end-to-end
optical music recognition.
"""

from __future__ import annotations

import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable
import logging
import shutil

logger = logging.getLogger(__name__)


class OemerAdapter:
    """
    Adapter for oemer OMR engine.
    
    Oemer is an end-to-end OMR system that uses deep learning
    (UNet segmentation + classifiers) to convert sheet music
    images to MusicXML.
    """
    
    def __init__(
        self,
        use_gpu: bool = True,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ):
        """
        Initialize oemer adapter.
        
        Args:
            use_gpu: Whether to use GPU acceleration if available
            progress_callback: Optional callback for progress updates
        """
        self.use_gpu = use_gpu
        self.progress_callback = progress_callback
        self._oemer_available: Optional[bool] = None
    
    def _report_progress(self, message: str, percent: int) -> None:
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(message, percent)
    
    def is_available(self) -> bool:
        """
        Check if oemer is available.
        
        Returns:
            True if oemer can be imported
        """
        if self._oemer_available is not None:
            return self._oemer_available
        
        try:
            import oemer
            self._oemer_available = True
        except ImportError:
            self._oemer_available = False
            logger.warning("oemer is not installed. Install with: pip install oemer")
        
        return self._oemer_available
    
    def process(self, image_path: Path) -> Optional[Path]:
        """
        Process an image through oemer.
        
        Args:
            image_path: Path to the input image
            
        Returns:
            Path to the generated MusicXML file, or None on failure
        """
        if not self.is_available():
            # Try running as subprocess command
            return self._process_via_cli(image_path)
        
        return self._process_via_library(image_path)
    
    def _process_via_library(self, image_path: Path) -> Optional[Path]:
        """
        Process using oemer Python library directly.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to MusicXML output
        """
        try:
            self._report_progress("Loading oemer model...", 25)
            
            # Import oemer modules
            from oemer import MODULE_PATH
            from oemer.ete import generate
            
            # Set output directory
            output_dir = image_path.parent
            
            self._report_progress("Running OMR recognition...", 40)
            
            # Run oemer
            # oemer.ete.generate returns path to MusicXML
            result = generate(
                str(image_path),
                output_dir=str(output_dir),
                use_tf=False,  # Use ONNX backend
            )
            
            self._report_progress("OMR recognition complete", 75)
            
            # Find the output MusicXML file
            if result and Path(result).exists():
                return Path(result)
            
            # Try to find output file by name convention
            expected_output = output_dir / f"{image_path.stem}.musicxml"
            if expected_output.exists():
                return expected_output
            
            # Check for .xml extension
            expected_output = output_dir / f"{image_path.stem}.xml"
            if expected_output.exists():
                return expected_output
            
            logger.error("Could not find oemer output file")
            return None
            
        except Exception as e:
            logger.exception("Error running oemer via library")
            # Fall back to CLI
            return self._process_via_cli(image_path)
    
    def _process_via_cli(self, image_path: Path) -> Optional[Path]:
        """
        Process using oemer CLI command.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to MusicXML output
        """
        try:
            self._report_progress("Running oemer CLI...", 30)
            
            # Run oemer as command
            result = subprocess.run(
                [sys.executable, "-m", "oemer", str(image_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"oemer CLI failed: {result.stderr}")
                return None
            
            self._report_progress("Parsing output...", 70)
            
            # Find output file - oemer outputs to same directory as input
            output_dir = image_path.parent
            
            # Check various possible output names
            possible_outputs = [
                output_dir / f"{image_path.stem}.musicxml",
                output_dir / f"{image_path.stem}.xml",
                output_dir / f"{image_path.stem}_oemer.musicxml",
            ]
            
            for output_path in possible_outputs:
                if output_path.exists():
                    return output_path
            
            # Search for any recently created musicxml file
            import glob
            musicxml_files = list(output_dir.glob("*.musicxml")) + list(output_dir.glob("*.xml"))
            
            if musicxml_files:
                # Return most recently modified
                return max(musicxml_files, key=lambda p: p.stat().st_mtime)
            
            logger.error("Could not find oemer output file")
            return None
            
        except subprocess.TimeoutExpired:
            logger.error("oemer CLI timed out")
            return None
        except FileNotFoundError:
            logger.error("oemer CLI not found")
            return None
        except Exception as e:
            logger.exception("Error running oemer CLI")
            return None
    
    def get_model_info(self) -> dict:
        """
        Get information about the oemer model.
        
        Returns:
            Dictionary with model information
        """
        info = {
            "engine": "oemer",
            "available": self.is_available(),
            "gpu_enabled": self.use_gpu,
        }
        
        if self.is_available():
            try:
                import oemer
                info["version"] = getattr(oemer, "__version__", "unknown")
            except Exception:
                pass
        
        return info


class OemerMockAdapter:
    """
    Mock adapter for testing when oemer is not installed.
    
    Returns a simple placeholder score for development/testing.
    """
    
    def __init__(self, **kwargs):
        self.progress_callback = kwargs.get('progress_callback')
    
    def is_available(self) -> bool:
        return True
    
    def process(self, image_path: Path) -> Optional[Path]:
        """Generate a placeholder MusicXML file for testing."""
        from sheet_music_scanner.utils.image_processing import create_placeholder_musicxml
        
        output_path = image_path.parent / f"{image_path.stem}_placeholder.musicxml"
        create_placeholder_musicxml(output_path)
        return output_path
