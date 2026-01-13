"""
MIDI Exporter - Export scores to MIDI format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional
from dataclasses import dataclass
import logging

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class MidiExportOptions:
    """Options for MIDI export."""
    
    velocity: int = 80  # Note velocity (0-127)
    tempo: Optional[int] = None  # Override tempo (BPM), None = use score tempo
    quantize: bool = False  # Quantize note timings
    include_metadata: bool = True  # Include track names, etc.
    
    def __post_init__(self):
        # Validate velocity
        self.velocity = max(0, min(127, self.velocity))


class MidiExporter:
    """
    Export scores to MIDI format.
    
    Uses music21's built-in MIDI export capabilities with
    configurable options.
    """
    
    def __init__(self, options: Optional[MidiExportOptions] = None):
        """
        Initialize MIDI exporter.
        
        Args:
            options: Export options, or None for defaults
        """
        self.options = options or MidiExportOptions()
        self.config = get_config()
    
    def export(
        self,
        score: Score,
        output_path: Union[str, Path]
    ) -> Path:
        """
        Export a score to MIDI format.
        
        Args:
            score: Score to export
            output_path: Output file path (.mid or .midi)
            
        Returns:
            Path to created MIDI file
        """
        output_path = Path(output_path)
        
        # Ensure .mid extension
        if output_path.suffix.lower() not in ['.mid', '.midi']:
            output_path = output_path.with_suffix('.mid')
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get the music21 score
        m21_score = score.music21_score
        
        # Apply tempo override if specified
        if self.options.tempo:
            from music21 import tempo
            
            # Remove existing tempo marks
            for t in m21_score.flatten().getElementsByClass(tempo.MetronomeMark):
                m21_score.remove(t, recurse=True)
            
            # Add new tempo
            mm = tempo.MetronomeMark(number=self.options.tempo)
            m21_score.insert(0, mm)
        
        # Apply velocity if specified (non-default)
        if self.options.velocity != 80:
            for n in m21_score.recurse().notes:
                n.volume.velocity = self.options.velocity
        
        # Write MIDI file
        m21_score.write('midi', fp=str(output_path))
        
        logger.info(f"Exported MIDI to: {output_path}")
        return output_path
    
    def export_with_mido(
        self,
        score: Score,
        output_path: Union[str, Path]
    ) -> Path:
        """
        Export using mido for more control over MIDI output.
        
        This method provides finer control over MIDI parameters
        but may lose some music21 features.
        
        Args:
            score: Score to export
            output_path: Output file path
            
        Returns:
            Path to created MIDI file
        """
        try:
            import mido
        except ImportError:
            logger.warning("mido not installed, falling back to music21 export")
            return self.export(score, output_path)
        
        output_path = Path(output_path)
        if output_path.suffix.lower() not in ['.mid', '.midi']:
            output_path = output_path.with_suffix('.mid')
        
        # First export with music21 to temp file
        temp_path = self.config.temp_dir / "temp_export.mid"
        score.music21_score.write('midi', fp=str(temp_path))
        
        # Read with mido and apply modifications
        mid = mido.MidiFile(str(temp_path))
        
        # Modify velocities if needed
        if self.options.velocity != 80:
            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'note_on' and msg.velocity > 0:
                        msg.velocity = self.options.velocity
        
        # Save modified file
        mid.save(str(output_path))
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        logger.info(f"Exported MIDI (mido) to: {output_path}")
        return output_path
    
    @staticmethod
    def get_supported_extensions() -> list:
        """Get list of supported file extensions."""
        return [".mid", ".midi"]
