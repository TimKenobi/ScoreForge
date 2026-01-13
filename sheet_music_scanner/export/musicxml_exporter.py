"""
MusicXML Exporter - Export scores to MusicXML format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional
from dataclasses import dataclass
import logging

from sheet_music_scanner.core.score import Score

logger = logging.getLogger(__name__)


@dataclass
class MusicXMLExportOptions:
    """Options for MusicXML export."""
    
    compressed: bool = False  # Export as .mxl (compressed) vs .musicxml
    include_defaults: bool = True  # Include default styling
    include_credits: bool = True  # Include title/composer credits
    
    
class MusicXMLExporter:
    """
    Export scores to MusicXML format.
    
    MusicXML is the standard interchange format for music notation
    software like MuseScore, Finale, and Sibelius.
    """
    
    def __init__(self, options: Optional[MusicXMLExportOptions] = None):
        """
        Initialize MusicXML exporter.
        
        Args:
            options: Export options, or None for defaults
        """
        self.options = options or MusicXMLExportOptions()
    
    def export(
        self,
        score: Score,
        output_path: Union[str, Path]
    ) -> Path:
        """
        Export a score to MusicXML format.
        
        Args:
            score: Score to export
            output_path: Output file path
            
        Returns:
            Path to created MusicXML file
        """
        output_path = Path(output_path)
        
        # Determine format based on extension or options
        if self.options.compressed or output_path.suffix.lower() == '.mxl':
            format_type = 'mxl'
            if output_path.suffix.lower() != '.mxl':
                output_path = output_path.with_suffix('.mxl')
        else:
            format_type = 'musicxml'
            if output_path.suffix.lower() not in ['.musicxml', '.xml']:
                output_path = output_path.with_suffix('.musicxml')
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get the music21 score
        m21_score = score.music21_score
        
        # Write MusicXML file
        if format_type == 'mxl':
            m21_score.write('mxl', fp=str(output_path))
        else:
            m21_score.write('musicxml', fp=str(output_path))
        
        logger.info(f"Exported MusicXML to: {output_path}")
        return output_path
    
    def export_to_string(self, score: Score) -> str:
        """
        Export score to MusicXML string.
        
        Args:
            score: Score to export
            
        Returns:
            MusicXML content as string
        """
        return score.to_musicxml_string()
    
    @staticmethod
    def get_supported_extensions() -> list:
        """Get list of supported file extensions."""
        return [".musicxml", ".xml", ".mxl"]
