"""
Batch Processing Module - Process multiple files at once.

Provides batch OMR processing, batch export, and progress tracking.
"""

from __future__ import annotations

import threading
import queue
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BatchJobStatus(Enum):
    """Status of a batch job item."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJobItem:
    """A single item in a batch job."""
    input_path: Path
    output_path: Optional[Path] = None
    status: BatchJobStatus = BatchJobStatus.PENDING
    progress: int = 0  # 0-100
    error_message: Optional[str] = None
    result: Any = None
    processing_time: float = 0.0


@dataclass
class BatchJobResult:
    """Result of a complete batch job."""
    total_items: int
    completed: int
    failed: int
    cancelled: int
    total_time: float
    items: List[BatchJobItem] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.completed / self.total_items


class BatchProcessor:
    """
    Process multiple files in batch.
    
    Features:
    - Batch OMR processing
    - Batch export to multiple formats
    - Progress tracking per item and overall
    - Cancellation support
    - Parallel processing option
    """
    
    def __init__(self, max_workers: int = 1):
        """
        Initialize batch processor.
        
        Args:
            max_workers: Maximum parallel workers (1 = sequential)
        """
        self.max_workers = max_workers
        
        self._items: List[BatchJobItem] = []
        self._is_running = False
        self._cancel_requested = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._item_started_callback: Optional[Callable[[int, BatchJobItem], None]] = None
        self._item_progress_callback: Optional[Callable[[int, int], None]] = None
        self._item_completed_callback: Optional[Callable[[int, BatchJobItem], None]] = None
        self._job_completed_callback: Optional[Callable[[BatchJobResult], None]] = None
    
    def set_callbacks(
        self,
        on_item_started: Optional[Callable[[int, BatchJobItem], None]] = None,
        on_item_progress: Optional[Callable[[int, int], None]] = None,
        on_item_completed: Optional[Callable[[int, BatchJobItem], None]] = None,
        on_job_completed: Optional[Callable[[BatchJobResult], None]] = None,
    ) -> None:
        """
        Set progress callbacks.
        
        Args:
            on_item_started: Called when item starts (index, item)
            on_item_progress: Called on progress update (index, progress)
            on_item_completed: Called when item completes (index, item)
            on_job_completed: Called when entire job completes (result)
        """
        self._item_started_callback = on_item_started
        self._item_progress_callback = on_item_progress
        self._item_completed_callback = on_item_completed
        self._job_completed_callback = on_job_completed
    
    def add_files(self, files: List[Path]) -> None:
        """
        Add files to process.
        
        Args:
            files: List of file paths
        """
        for f in files:
            self._items.append(BatchJobItem(input_path=f))
    
    def set_output_directory(self, output_dir: Path, format_ext: str = ".musicxml") -> None:
        """
        Set output directory for all items.
        
        Args:
            output_dir: Output directory
            format_ext: Output format extension
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for item in self._items:
            output_name = item.input_path.stem + format_ext
            item.output_path = output_dir / output_name
    
    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()
    
    @property
    def items(self) -> List[BatchJobItem]:
        """Get all items."""
        return self._items.copy()
    
    @property
    def is_running(self) -> bool:
        """Check if batch is currently running."""
        return self._is_running
    
    def process_omr(self) -> None:
        """Start batch OMR processing in background."""
        if self._is_running:
            return
        
        self._is_running = True
        self._cancel_requested = False
        
        def run():
            start_time = time.time()
            completed = 0
            failed = 0
            cancelled = 0
            
            from sheet_music_scanner.omr.processor import OMRProcessor, OMREngine
            
            processor = OMRProcessor(engine=OMREngine.OEMER)
            
            for i, item in enumerate(self._items):
                if self._cancel_requested:
                    item.status = BatchJobStatus.CANCELLED
                    cancelled += 1
                    continue
                
                item.status = BatchJobStatus.PROCESSING
                item_start = time.time()
                
                if self._item_started_callback:
                    self._item_started_callback(i, item)
                
                try:
                    # Set up progress callback
                    def on_progress(msg, pct):
                        item.progress = pct
                        if self._item_progress_callback:
                            self._item_progress_callback(i, pct)
                    
                    processor.progress_callback = on_progress
                    
                    # Process the image
                    if item.input_path.suffix.lower() == '.pdf':
                        result = processor.process_pdf(item.input_path)
                    else:
                        result = processor.process_image(item.input_path)
                    
                    if result.success and result.score:
                        item.result = result.score
                        item.status = BatchJobStatus.COMPLETED
                        
                        # Export if output path set
                        if item.output_path:
                            result.score.to_musicxml(item.output_path)
                        
                        completed += 1
                    else:
                        item.status = BatchJobStatus.FAILED
                        item.error_message = result.error_message
                        failed += 1
                
                except Exception as e:
                    item.status = BatchJobStatus.FAILED
                    item.error_message = str(e)
                    failed += 1
                    logger.exception(f"Batch OMR failed for {item.input_path}")
                
                item.processing_time = time.time() - item_start
                item.progress = 100
                
                if self._item_completed_callback:
                    self._item_completed_callback(i, item)
            
            # Create result
            result = BatchJobResult(
                total_items=len(self._items),
                completed=completed,
                failed=failed,
                cancelled=cancelled,
                total_time=time.time() - start_time,
                items=self._items.copy(),
            )
            
            self._is_running = False
            
            if self._job_completed_callback:
                self._job_completed_callback(result)
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def process_export(
        self,
        scores: List[Any],
        output_dir: Path,
        format_type: str = "musicxml"
    ) -> None:
        """
        Batch export scores.
        
        Args:
            scores: List of Score objects
            output_dir: Output directory
            format_type: Export format (musicxml, midi, pdf)
        """
        if self._is_running:
            return
        
        self._is_running = True
        self._cancel_requested = False
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up items from scores
        self._items.clear()
        for i, score in enumerate(scores):
            ext = {
                "musicxml": ".musicxml",
                "midi": ".mid",
                "pdf": ".pdf",
            }.get(format_type, ".musicxml")
            
            name = score.title or f"score_{i + 1}"
            output_path = output_dir / f"{name}{ext}"
            
            item = BatchJobItem(
                input_path=Path(name),
                output_path=output_path,
            )
            item.result = score
            self._items.append(item)
        
        def run():
            start_time = time.time()
            completed = 0
            failed = 0
            cancelled = 0
            
            from sheet_music_scanner.export import (
                MidiExporter, MusicXMLExporter, PDFExporter
            )
            
            exporter_map = {
                "musicxml": MusicXMLExporter,
                "midi": MidiExporter,
                "pdf": PDFExporter,
            }
            
            ExporterClass = exporter_map.get(format_type, MusicXMLExporter)
            exporter = ExporterClass()
            
            for i, item in enumerate(self._items):
                if self._cancel_requested:
                    item.status = BatchJobStatus.CANCELLED
                    cancelled += 1
                    continue
                
                item.status = BatchJobStatus.PROCESSING
                item_start = time.time()
                
                if self._item_started_callback:
                    self._item_started_callback(i, item)
                
                try:
                    exporter.export(item.result, str(item.output_path))
                    item.status = BatchJobStatus.COMPLETED
                    completed += 1
                    
                except Exception as e:
                    item.status = BatchJobStatus.FAILED
                    item.error_message = str(e)
                    failed += 1
                
                item.processing_time = time.time() - item_start
                item.progress = 100
                
                if self._item_completed_callback:
                    self._item_completed_callback(i, item)
            
            result = BatchJobResult(
                total_items=len(self._items),
                completed=completed,
                failed=failed,
                cancelled=cancelled,
                total_time=time.time() - start_time,
                items=self._items.copy(),
            )
            
            self._is_running = False
            
            if self._job_completed_callback:
                self._job_completed_callback(result)
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def cancel(self) -> None:
        """Request cancellation of current job."""
        self._cancel_requested = True
    
    def wait(self, timeout: Optional[float] = None) -> None:
        """Wait for current job to complete."""
        if self._thread:
            self._thread.join(timeout=timeout)
