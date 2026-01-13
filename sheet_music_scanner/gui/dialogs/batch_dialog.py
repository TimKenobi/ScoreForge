"""
Batch Processing Dialog - GUI for batch operations.

Provides file selection, progress tracking, and result display.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog,
    QComboBox, QGroupBox, QFormLayout, QCheckBox, QSpinBox,
    QTabWidget, QWidget, QTextEdit, QSplitter, QMessageBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QBrush

from sheet_music_scanner.core.batch_processor import (
    BatchProcessor, BatchJobItem, BatchJobResult, BatchJobStatus
)
from sheet_music_scanner.omr.processor import OMRProcessor


class BatchProcessDialog(QDialog):
    """
    Dialog for batch processing files.
    
    Features:
    - Add/remove files
    - Select output format and directory
    - Progress tracking
    - Results summary
    """
    
    # Signals
    processing_complete = Signal(object)  # BatchJobResult
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Batch Processing")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        self._processor = BatchProcessor()
        self._output_dir: Optional[Path] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Tabs for different batch operations
        tabs = QTabWidget()
        
        # OMR Tab
        omr_tab = self._create_omr_tab()
        tabs.addTab(omr_tab, "🔍 OMR Processing")
        
        # Export Tab
        export_tab = self._create_export_tab()
        tabs.addTab(export_tab, "📤 Batch Export")
        
        layout.addWidget(tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Processing")
        self.start_btn.clicked.connect(self._on_start)
        button_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("⏹ Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_omr_tab(self) -> QWidget:
        """Create the OMR processing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # File selection
        file_group = QGroupBox("Input Files")
        file_layout = QVBoxLayout(file_group)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setAlternatingRowColors(True)
        file_layout.addWidget(self.file_list)
        
        # File buttons
        file_btn_layout = QHBoxLayout()
        
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._on_add_files)
        file_btn_layout.addWidget(add_files_btn)
        
        add_folder_btn = QPushButton("Add Folder...")
        add_folder_btn.clicked.connect(self._on_add_folder)
        file_btn_layout.addWidget(add_folder_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._on_remove_selected)
        file_btn_layout.addWidget(remove_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._on_clear_files)
        file_btn_layout.addWidget(clear_btn)
        
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        
        layout.addWidget(file_group)
        
        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        
        # Output directory
        output_dir_layout = QHBoxLayout()
        self.output_dir_label = QLabel("Not selected")
        output_dir_layout.addWidget(self.output_dir_label, 1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_output)
        output_dir_layout.addWidget(browse_btn)
        
        output_layout.addRow("Output Directory:", output_dir_layout)
        
        # Output format
        self.output_format = QComboBox()
        self.output_format.addItems(["MusicXML", "MIDI", "PDF"])
        output_layout.addRow("Export Format:", self.output_format)
        
        layout.addWidget(output_group)
        
        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setFormat("Overall: %v/%m files")
        progress_layout.addWidget(self.overall_progress)
        
        self.current_progress = QProgressBar()
        self.current_progress.setFormat("Current: %p%")
        progress_layout.addWidget(self.current_progress)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        return widget
    
    def _create_export_tab(self) -> QWidget:
        """Create the batch export tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_label = QLabel(
            "Batch export is available after processing or opening multiple scores.\n"
            "Use File → Batch Export to export all open scores."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        return widget
    
    def _connect_signals(self):
        """Connect processor signals."""
        self._processor.set_callbacks(
            on_item_started=self._on_item_started,
            on_item_progress=self._on_item_progress,
            on_item_completed=self._on_item_completed,
            on_job_completed=self._on_job_completed,
        )
    
    def _on_add_files(self):
        """Add files to the list."""
        formats = " ".join(f"*{ext}" for ext in OMRProcessor.get_supported_formats())
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            "",
            f"Image Files ({formats});;All Files (*)"
        )
        
        for filepath in files:
            self._add_file(Path(filepath))
    
    def _on_add_folder(self):
        """Add all files from a folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder"
        )
        
        if folder:
            folder_path = Path(folder)
            for ext in OMRProcessor.get_supported_formats():
                for filepath in folder_path.glob(f"*{ext}"):
                    self._add_file(filepath)
    
    def _add_file(self, filepath: Path):
        """Add a single file to the list."""
        # Check if already added
        for i in range(self.file_list.count()):
            if self.file_list.item(i).data(Qt.ItemDataRole.UserRole) == str(filepath):
                return
        
        item = QListWidgetItem(filepath.name)
        item.setData(Qt.ItemDataRole.UserRole, str(filepath))
        item.setToolTip(str(filepath))
        self.file_list.addItem(item)
        
        self._update_file_count()
    
    def _on_remove_selected(self):
        """Remove selected files."""
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self._update_file_count()
    
    def _on_clear_files(self):
        """Clear all files."""
        self.file_list.clear()
        self._update_file_count()
    
    def _on_browse_output(self):
        """Browse for output directory."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        
        if folder:
            self._output_dir = Path(folder)
            self.output_dir_label.setText(folder)
    
    def _update_file_count(self):
        """Update file count display."""
        count = self.file_list.count()
        self.overall_progress.setMaximum(max(1, count))
        self.overall_progress.setValue(0)
        self.start_btn.setEnabled(count > 0)
    
    def _on_start(self):
        """Start batch processing."""
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "No Files", "Please add files to process.")
            return
        
        if not self._output_dir:
            QMessageBox.warning(self, "No Output", "Please select an output directory.")
            return
        
        # Collect files
        self._processor.clear()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            filepath = Path(item.data(Qt.ItemDataRole.UserRole))
            self._processor.add_files([filepath])
        
        # Set output format
        format_map = {
            "MusicXML": ".musicxml",
            "MIDI": ".mid",
            "PDF": ".pdf",
        }
        ext = format_map.get(self.output_format.currentText(), ".musicxml")
        self._processor.set_output_directory(self._output_dir, ext)
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.overall_progress.setValue(0)
        self.status_label.setText("Processing...")
        
        # Reset item colors
        for i in range(self.file_list.count()):
            self.file_list.item(i).setBackground(QBrush())
        
        # Start processing
        self._processor.process_omr()
    
    def _on_cancel(self):
        """Cancel processing."""
        self._processor.cancel()
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Cancelling...")
    
    def _on_item_started(self, index: int, item: BatchJobItem):
        """Handle item started."""
        QTimer.singleShot(0, lambda: self._update_item_started(index, item))
    
    def _update_item_started(self, index: int, item: BatchJobItem):
        """Update UI for item started (main thread)."""
        self.status_label.setText(f"Processing: {item.input_path.name}")
        self.current_progress.setValue(0)
        
        if index < self.file_list.count():
            list_item = self.file_list.item(index)
            list_item.setBackground(QBrush(QColor(255, 255, 200)))  # Yellow
            self.file_list.scrollToItem(list_item)
    
    def _on_item_progress(self, index: int, progress: int):
        """Handle item progress."""
        QTimer.singleShot(0, lambda: self.current_progress.setValue(progress))
    
    def _on_item_completed(self, index: int, item: BatchJobItem):
        """Handle item completed."""
        QTimer.singleShot(0, lambda: self._update_item_completed(index, item))
    
    def _update_item_completed(self, index: int, item: BatchJobItem):
        """Update UI for item completed (main thread)."""
        self.overall_progress.setValue(index + 1)
        
        if index < self.file_list.count():
            list_item = self.file_list.item(index)
            
            if item.status == BatchJobStatus.COMPLETED:
                list_item.setBackground(QBrush(QColor(200, 255, 200)))  # Green
                list_item.setText(f"✓ {item.input_path.name}")
            elif item.status == BatchJobStatus.FAILED:
                list_item.setBackground(QBrush(QColor(255, 200, 200)))  # Red
                list_item.setText(f"✗ {item.input_path.name}")
                list_item.setToolTip(f"Error: {item.error_message}")
            elif item.status == BatchJobStatus.CANCELLED:
                list_item.setBackground(QBrush(QColor(220, 220, 220)))  # Gray
                list_item.setText(f"⊘ {item.input_path.name}")
    
    def _on_job_completed(self, result: BatchJobResult):
        """Handle job completed."""
        QTimer.singleShot(0, lambda: self._show_results(result))
    
    def _show_results(self, result: BatchJobResult):
        """Show results summary."""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Update status
        self.status_label.setText(
            f"Completed: {result.completed} | "
            f"Failed: {result.failed} | "
            f"Cancelled: {result.cancelled} | "
            f"Time: {result.total_time:.1f}s"
        )
        
        # Show summary dialog
        QMessageBox.information(
            self,
            "Batch Processing Complete",
            f"Processing complete!\n\n"
            f"✓ Completed: {result.completed}\n"
            f"✗ Failed: {result.failed}\n"
            f"⊘ Cancelled: {result.cancelled}\n\n"
            f"Total time: {result.total_time:.1f} seconds\n"
            f"Success rate: {result.success_rate * 100:.1f}%"
        )
        
        self.processing_complete.emit(result)
