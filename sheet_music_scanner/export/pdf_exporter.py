"""
PDF Exporter - Export scores to high-quality PDF sheet music.

Uses LilyPond (via music21 or Abjad) or MuseScore for rendering.
"""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Union, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import tempfile

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.config import get_config

logger = logging.getLogger(__name__)


class PDFRenderer(Enum):
    """Available PDF rendering backends."""
    LILYPOND = "lilypond"  # LilyPond via music21
    MUSESCORE = "musescore"  # MuseScore CLI
    VEROVIO = "verovio"  # Verovio (SVG to PDF)


@dataclass
class PDFExportOptions:
    """Options for PDF export."""
    
    renderer: PDFRenderer = PDFRenderer.LILYPOND
    paper_size: str = "letter"  # "letter", "a4", "legal"
    staff_size: int = 18  # Staff size in points
    include_title: bool = True
    include_composer: bool = True
    include_lyrics: bool = True
    page_numbers: bool = True
    
    # Layout options
    margin_top: float = 0.5  # inches
    margin_bottom: float = 0.5
    margin_left: float = 0.5
    margin_right: float = 0.5


class PDFExporter:
    """
    Export scores to high-quality PDF format.
    
    Supports multiple rendering backends:
    - LilyPond: Publication-quality engraving
    - MuseScore: Fast, good quality
    - Verovio: Web-friendly, SVG-based
    """
    
    def __init__(self, options: Optional[PDFExportOptions] = None):
        """
        Initialize PDF exporter.
        
        Args:
            options: Export options, or None for defaults
        """
        self.options = options or PDFExportOptions()
        self.config = get_config()
    
    def export(
        self,
        score: Score,
        output_path: Union[str, Path]
    ) -> Path:
        """
        Export a score to PDF format.
        
        Args:
            score: Score to export
            output_path: Output file path
            
        Returns:
            Path to created PDF file
        """
        output_path = Path(output_path)
        
        # Ensure .pdf extension
        if output_path.suffix.lower() != '.pdf':
            output_path = output_path.with_suffix('.pdf')
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try renderers in order of preference
        if self.options.renderer == PDFRenderer.LILYPOND:
            if self._has_lilypond():
                return self._export_via_lilypond(score, output_path)
            elif self._has_musescore():
                logger.warning("LilyPond not found, falling back to MuseScore")
                return self._export_via_musescore(score, output_path)
            else:
                return self._export_via_verovio(score, output_path)
        
        elif self.options.renderer == PDFRenderer.MUSESCORE:
            if self._has_musescore():
                return self._export_via_musescore(score, output_path)
            elif self._has_lilypond():
                logger.warning("MuseScore not found, falling back to LilyPond")
                return self._export_via_lilypond(score, output_path)
            else:
                return self._export_via_verovio(score, output_path)
        
        else:  # VEROVIO
            return self._export_via_verovio(score, output_path)
    
    def _has_lilypond(self) -> bool:
        """Check if LilyPond is available."""
        return self.config.has_lilypond()
    
    def _has_musescore(self) -> bool:
        """Check if MuseScore is available."""
        return self.config.has_musescore()
    
    def _export_via_lilypond(
        self,
        score: Score,
        output_path: Path
    ) -> Path:
        """
        Export using LilyPond via music21.
        
        Args:
            score: Score to export
            output_path: Output path
            
        Returns:
            Path to PDF file
        """
        try:
            # music21 can export directly to LilyPond PDF
            # Configure music21 to use our LilyPond path
            from music21 import environment
            
            env = environment.Environment()
            if self.config.lilypond_path:
                env['lilypondPath'] = self.config.lilypond_path
            
            # Export via LilyPond
            m21_score = score.music21_score
            
            # Write to temporary .ly file first for more control
            temp_dir = Path(tempfile.mkdtemp())
            ly_path = temp_dir / "score.ly"
            
            # Export as LilyPond format
            m21_score.write('lily', fp=str(ly_path))
            
            # Run LilyPond to create PDF
            result = subprocess.run(
                [
                    self.config.lilypond_path,
                    f"--output={output_path.parent / output_path.stem}",
                    f"--{self.options.paper_size}",
                    str(ly_path)
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"LilyPond error: {result.stderr}")
                # Try music21's direct export as fallback
                m21_score.write('lily.pdf', fp=str(output_path))
            
            # Clean up temp files
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info(f"Exported PDF via LilyPond to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.exception("LilyPond export failed")
            raise
    
    def _export_via_musescore(
        self,
        score: Score,
        output_path: Path
    ) -> Path:
        """
        Export using MuseScore CLI.
        
        Args:
            score: Score to export
            output_path: Output path
            
        Returns:
            Path to PDF file
        """
        try:
            # First export to MusicXML
            temp_dir = Path(tempfile.mkdtemp())
            musicxml_path = temp_dir / "score.musicxml"
            
            score.to_musicxml(musicxml_path)
            
            # Run MuseScore to convert to PDF
            result = subprocess.run(
                [
                    self.config.musescore_path,
                    "-o", str(output_path),
                    str(musicxml_path)
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"MuseScore error: {result.stderr}")
                raise RuntimeError(f"MuseScore failed: {result.stderr}")
            
            # Clean up temp files
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info(f"Exported PDF via MuseScore to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.exception("MuseScore export failed")
            raise
    
    def _export_via_verovio(
        self,
        score: Score,
        output_path: Path
    ) -> Path:
        """
        Export using Verovio (SVG to PDF).
        
        Args:
            score: Score to export
            output_path: Output path
            
        Returns:
            Path to PDF file
        """
        try:
            import verovio
        except ImportError:
            raise RuntimeError(
                "Verovio not installed. Install with: pip install verovio"
            )
        
        try:
            # Export to MusicXML first
            temp_dir = Path(tempfile.mkdtemp())
            musicxml_path = temp_dir / "score.musicxml"
            score.to_musicxml(musicxml_path)
            
            # Initialize Verovio
            toolkit = verovio.toolkit()
            toolkit.setOptions({
                "pageWidth": 2100 if self.options.paper_size == "a4" else 2159,
                "pageHeight": 2970 if self.options.paper_size == "a4" else 2794,
                "scale": 40,
                "adjustPageHeight": True,
            })
            
            # Load MusicXML
            toolkit.loadFile(str(musicxml_path))
            
            # Render all pages as SVG
            page_count = toolkit.getPageCount()
            svg_paths = []
            
            for i in range(1, page_count + 1):
                svg = toolkit.renderToSVG(i)
                svg_path = temp_dir / f"page_{i}.svg"
                svg_path.write_text(svg)
                svg_paths.append(svg_path)
            
            # Convert SVGs to PDF
            # This requires additional tools like cairosvg or rsvg-convert
            self._svgs_to_pdf(svg_paths, output_path)
            
            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info(f"Exported PDF via Verovio to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.exception("Verovio export failed")
            raise
    
    def _svgs_to_pdf(self, svg_paths: list, output_path: Path) -> None:
        """
        Convert SVG files to PDF.
        
        Args:
            svg_paths: List of SVG file paths
            output_path: Output PDF path
        """
        try:
            import cairosvg
            from PyPDF2 import PdfMerger
        except ImportError:
            # Fallback: just use first page and try simple conversion
            if svg_paths:
                try:
                    import cairosvg
                    cairosvg.svg2pdf(
                        url=str(svg_paths[0]),
                        write_to=str(output_path)
                    )
                    return
                except ImportError:
                    pass
            
            raise RuntimeError(
                "PDF conversion requires cairosvg and PyPDF2. "
                "Install with: pip install cairosvg PyPDF2"
            )
        
        # Convert each SVG to PDF
        pdf_paths = []
        for svg_path in svg_paths:
            pdf_path = svg_path.with_suffix('.pdf')
            cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
            pdf_paths.append(pdf_path)
        
        # Merge PDFs
        if len(pdf_paths) == 1:
            shutil.copy(pdf_paths[0], output_path)
        else:
            merger = PdfMerger()
            for pdf_path in pdf_paths:
                merger.append(str(pdf_path))
            merger.write(str(output_path))
            merger.close()
    
    def get_available_renderers(self) -> list:
        """
        Get list of available PDF renderers.
        
        Returns:
            List of available PDFRenderer values
        """
        available = []
        
        if self._has_lilypond():
            available.append(PDFRenderer.LILYPOND)
        
        if self._has_musescore():
            available.append(PDFRenderer.MUSESCORE)
        
        try:
            import verovio
            available.append(PDFRenderer.VEROVIO)
        except ImportError:
            pass
        
        return available
    
    @staticmethod
    def get_supported_extensions() -> list:
        """Get list of supported file extensions."""
        return [".pdf"]
