"""
OMR Processor - Orchestrates the OMR pipeline.

Handles image preprocessing, OMR engine selection,
and post-processing of results.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, List, Callable, Union
from dataclasses import dataclass
from enum import Enum
import logging

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.config import get_config


logger = logging.getLogger(__name__)


class OMREngine(Enum):
    """Available OMR engines."""
    OEMER = "oemer"
    AUDIVERIS = "audiveris"


@dataclass
class OMRResult:
    """Result from OMR processing."""
    
    success: bool
    score: Optional[Score] = None
    musicxml_path: Optional[Path] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class OMRProcessor:
    """
    Main OMR processor that orchestrates the recognition pipeline.
    
    Workflow:
    1. Preprocess image (deskew, enhance contrast)
    2. Run OMR engine to produce MusicXML
    3. Parse MusicXML into Score object
    4. Apply post-processing corrections
    """
    
    def __init__(
        self,
        engine: OMREngine = OMREngine.OEMER,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ):
        """
        Initialize OMR processor.
        
        Args:
            engine: OMR engine to use
            progress_callback: Optional callback for progress updates
                              Signature: (message: str, percent: int) -> None
        """
        self.engine = engine
        self.progress_callback = progress_callback
        self.config = get_config()
        
        # Initialize the appropriate adapter
        self._adapter = self._create_adapter()
    
    def _create_adapter(self):
        """Create the appropriate OMR adapter."""
        if self.engine == OMREngine.OEMER:
            from sheet_music_scanner.omr.oemer_adapter import OemerAdapter
            return OemerAdapter(
                use_gpu=self.config.omr.use_gpu,
                progress_callback=self.progress_callback
            )
        elif self.engine == OMREngine.AUDIVERIS:
            from sheet_music_scanner.omr.audiveris_adapter import AudiverisAdapter
            return AudiverisAdapter(
                progress_callback=self.progress_callback
            )
        else:
            raise ValueError(f"Unknown OMR engine: {self.engine}")
    
    def _report_progress(self, message: str, percent: int) -> None:
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(message, percent)
        logger.info(f"OMR Progress: {percent}% - {message}")
    
    def process_image(
        self,
        image_path: Union[str, Path],
        preprocess: bool = True
    ) -> OMRResult:
        """
        Process a single image through OMR.
        
        Args:
            image_path: Path to the image file
            preprocess: Whether to apply image preprocessing
            
        Returns:
            OMRResult with Score object or error information
        """
        import time
        start_time = time.time()
        
        image_path = Path(image_path)
        
        if not image_path.exists():
            return OMRResult(
                success=False,
                error_message=f"Image file not found: {image_path}"
            )
        
        try:
            self._report_progress("Starting OMR processing...", 0)
            
            # Step 1: Preprocess image if enabled
            if preprocess and self.config.omr.deskew_enabled:
                self._report_progress("Preprocessing image...", 10)
                processed_path = self._preprocess_image(image_path)
            else:
                processed_path = image_path
            
            # Step 2: Run OMR engine
            self._report_progress("Running OMR recognition...", 20)
            musicxml_path = self._adapter.process(processed_path)
            
            if musicxml_path is None:
                return OMRResult(
                    success=False,
                    error_message="OMR engine failed to produce output"
                )
            
            self._report_progress("Parsing MusicXML...", 80)
            
            # Step 3: Parse MusicXML into Score
            score = Score.from_musicxml(musicxml_path)
            
            self._report_progress("Completed!", 100)
            
            processing_time = time.time() - start_time
            
            return OMRResult(
                success=True,
                score=score,
                musicxml_path=musicxml_path,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.exception("OMR processing failed")
            return OMRResult(
                success=False,
                error_message=str(e)
            )
    
    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        pages: Optional[List[int]] = None
    ) -> OMRResult:
        """
        Process a PDF document through OMR.
        
        Args:
            pdf_path: Path to PDF file
            pages: Optional list of page numbers to process (0-indexed).
                   If None, processes all pages.
                   
        Returns:
            OMRResult with combined Score
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return OMRResult(
                success=False,
                error_message=f"PDF file not found: {pdf_path}"
            )
        
        try:
            # Extract images from PDF
            self._report_progress("Extracting pages from PDF...", 5)
            image_paths = self._extract_pdf_pages(pdf_path, pages)
            
            if not image_paths:
                return OMRResult(
                    success=False,
                    error_message="No pages extracted from PDF"
                )
            
            # Process each page
            scores = []
            total_pages = len(image_paths)
            
            for i, img_path in enumerate(image_paths):
                progress = 10 + int((i / total_pages) * 80)
                self._report_progress(
                    f"Processing page {i + 1} of {total_pages}...", 
                    progress
                )
                
                result = self.process_image(img_path, preprocess=True)
                
                if result.success and result.score:
                    scores.append(result.score)
            
            if not scores:
                return OMRResult(
                    success=False,
                    error_message="No pages successfully processed"
                )
            
            # Combine scores (for multi-page documents)
            self._report_progress("Combining pages...", 95)
            combined_score = self._combine_scores(scores)
            
            self._report_progress("Completed!", 100)
            
            return OMRResult(
                success=True,
                score=combined_score
            )
            
        except Exception as e:
            logger.exception("PDF processing failed")
            return OMRResult(
                success=False,
                error_message=str(e)
            )
    
    def _preprocess_image(self, image_path: Path) -> Path:
        """
        Apply image preprocessing for better OMR results.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to preprocessed image
        """
        from sheet_music_scanner.utils.image_processing import (
            preprocess_for_omr
        )
        
        output_path = self.config.temp_dir / f"preprocessed_{image_path.name}"
        preprocess_for_omr(image_path, output_path)
        return output_path
    
    def _extract_pdf_pages(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None
    ) -> List[Path]:
        """
        Extract pages from PDF as images.
        
        Args:
            pdf_path: Path to PDF
            pages: Page numbers to extract (0-indexed), or None for all
            
        Returns:
            List of paths to extracted images
        """
        from sheet_music_scanner.utils.image_processing import extract_pdf_pages
        
        output_dir = self.config.temp_dir / pdf_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return extract_pdf_pages(pdf_path, output_dir, pages)
    
    def _combine_scores(self, scores: List[Score]) -> Score:
        """
        Combine multiple scores into one (for multi-page documents).
        
        Args:
            scores: List of Score objects
            
        Returns:
            Combined Score
        """
        if len(scores) == 1:
            return scores[0]
        
        # For now, just return the first score
        # TODO: Implement proper score concatenation
        from music21 import stream
        
        combined = stream.Score()
        
        # Get parts from first score as template
        first_score = scores[0].music21_score
        
        for part_idx, part in enumerate(first_score.parts):
            new_part = stream.Part()
            new_part.id = part.id
            
            # Copy measures from all scores
            for score in scores:
                if part_idx < len(score.music21_score.parts):
                    source_part = score.music21_score.parts[part_idx]
                    for measure in source_part.getElementsByClass(stream.Measure):
                        new_part.append(measure)
            
            combined.append(new_part)
        
        return Score.from_music21(combined)
    
    @staticmethod
    def get_supported_image_formats() -> List[str]:
        """Get list of supported image formats."""
        return [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of all supported input formats."""
        return [
            ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp",
            ".pdf"
        ]
