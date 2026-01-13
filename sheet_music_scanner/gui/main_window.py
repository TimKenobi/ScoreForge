"""
Main Window - Primary application window for ScoreForge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QFileDialog,
    QMessageBox, QSplitter, QProgressDialog, QLabel,
    QApplication, QDockWidget,
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QDragEnterEvent, QDropEvent

from sheet_music_scanner.config import get_config
from sheet_music_scanner.core.autosave import get_autosave_manager
from sheet_music_scanner.gui.undo_history_panel import UndoHistoryPanel, UndoHistoryManager
from sheet_music_scanner.core.score import Score
from sheet_music_scanner.omr.processor import OMRProcessor, OMREngine
from sheet_music_scanner.export import MidiExporter, MusicXMLExporter, PDFExporter

logger = logging.getLogger(__name__)


class OMRWorker(QThread):
    """Background worker for OMR processing."""
    
    finished = Signal(object)  # OMRResult
    progress = Signal(str, int)  # message, percent
    error = Signal(str)
    
    def __init__(self, processor: OMRProcessor, image_path: Path):
        super().__init__()
        self.processor = processor
        self.image_path = image_path
    
    def run(self):
        try:
            # Connect progress callback
            self.processor.progress_callback = self._on_progress
            
            # Process the image
            if self.image_path.suffix.lower() == '.pdf':
                result = self.processor.process_pdf(self.image_path)
            else:
                result = self.processor.process_image(self.image_path)
            
            self.finished.emit(result)
            
        except Exception as e:
            logger.exception("OMR worker error")
            self.error.emit(str(e))
    
    def _on_progress(self, message: str, percent: int):
        self.progress.emit(message, percent)


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Provides:
    - Menu bar with file, edit, and view menus
    - Toolbar with common actions
    - Central score viewer
    - Side panel for editing controls
    - Status bar with information
    """
    
    def __init__(self):
        super().__init__()
        
        self.config = get_config()
        self.current_score: Optional[Score] = None
        self.current_file_path: Optional[Path] = None
        self._omr_worker: Optional[OMRWorker] = None
        
        # New feature managers
        self._autosave = get_autosave_manager()
        self._undo_manager = UndoHistoryManager()
        self._playback_controls = None
        
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_dock_panels()
        self._setup_shortcuts()
        self._setup_autosave()
        
        # Check for crash recovery
        self._check_recovery()
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Apply saved window size
        self.resize(
            self.config.gui.window_width,
            self.config.gui.window_height
        )
    
    def _setup_ui(self):
        """Set up the main UI layout."""
        self.setWindowTitle("ScoreForge")
        self.setMinimumSize(800, 600)
        
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create main horizontal splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # Left panel: Command input (for text-based note entry)
        from sheet_music_scanner.gui.command_input import CommandInputPanel
        self.command_panel = CommandInputPanel()
        self.command_panel.setMinimumWidth(280)
        self.command_panel.setMaximumWidth(450)
        self.splitter.addWidget(self.command_panel)
        
        # Connect command panel signals
        self.command_panel.apply_requested.connect(self._on_apply_commands)
        
        # Center: Vertical splitter for score view and interactive editor
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Score viewer (top center)
        from sheet_music_scanner.gui.score_view import ScoreView
        self.score_view = ScoreView()
        center_splitter.addWidget(self.score_view)
        
        # Interactive editor (bottom center - for drag-and-drop editing)
        from sheet_music_scanner.gui.interactive_editor import InteractiveScoreEditor
        self.interactive_editor = InteractiveScoreEditor()
        self.interactive_editor.setMinimumHeight(150)
        center_splitter.addWidget(self.interactive_editor)
        
        # Connect interactive editor signals
        self.interactive_editor.note_changed.connect(self._on_interactive_note_changed)
        self.interactive_editor.score_modified.connect(self._on_score_modified)
        
        # Set center splitter sizes (70% score view, 30% interactive editor)
        center_splitter.setSizes([500, 200])
        
        self.splitter.addWidget(center_splitter)
        
        # Right panel: Editor panel (for transpose, octave shift, lyrics)
        from sheet_music_scanner.gui.editor_panel import EditorPanel
        self.editor_panel = EditorPanel()
        self.editor_panel.setMinimumWidth(250)
        self.editor_panel.setMaximumWidth(400)
        self.splitter.addWidget(self.editor_panel)
        
        # Connect editor signals
        self.editor_panel.transpose_requested.connect(self._on_transpose)
        self.editor_panel.octave_shift_requested.connect(self._on_octave_shift)
        self.editor_panel.key_change_requested.connect(self._on_key_change)
        
        # Set initial splitter sizes (25% command, 55% center, 20% editor)
        self.splitter.setSizes([280, 620, 300])
        
        # Add playback controls below the main content
        main_container = QWidget()
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Move splitter to container
        main_layout.removeWidget(self.splitter)
        container_layout.addWidget(self.splitter, 1)
        
        # Add playback toolbar
        from sheet_music_scanner.gui.playback_controls import PlaybackControls
        self._playback_controls = PlaybackControls()
        container_layout.addWidget(self._playback_controls)
        
        main_layout.addWidget(main_container)
    
    def _setup_menu_bar(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Import image action
        import_action = QAction("&Import Image...", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self._on_import_image)
        file_menu.addAction(import_action)
        
        # Open MusicXML action
        open_action = QAction("&Open MusicXML...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        # New from template
        new_template_action = QAction("📋 &New from Template...", self)
        new_template_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_template_action.triggered.connect(self._on_new_from_template)
        file_menu.addAction(new_template_action)
        
        file_menu.addSeparator()
        
        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()
        
        file_menu.addSeparator()
        
        # Save action
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)
        
        # Export submenu
        export_menu = file_menu.addMenu("&Export")
        
        export_midi_action = QAction("Export to &MIDI...", self)
        export_midi_action.triggered.connect(self._on_export_midi)
        export_menu.addAction(export_midi_action)
        
        export_xml_action = QAction("Export to Music&XML...", self)
        export_xml_action.triggered.connect(self._on_export_musicxml)
        export_menu.addAction(export_xml_action)
        
        export_pdf_action = QAction("Export to &PDF...", self)
        export_pdf_action.triggered.connect(self._on_export_pdf)
        export_menu.addAction(export_pdf_action)
        
        file_menu.addSeparator()
        
        # Batch processing
        batch_action = QAction("📦 &Batch Processing...", self)
        batch_action.triggered.connect(self._on_batch_processing)
        file_menu.addAction(batch_action)
        
        file_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)
        self._undo_action = undo_action
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)
        self._redo_action = redo_action
        
        edit_menu.addSeparator()
        
        transpose_action = QAction("&Transpose...", self)
        transpose_action.setShortcut(QKeySequence("Ctrl+T"))
        transpose_action.triggered.connect(self._on_show_transpose_dialog)
        edit_menu.addAction(transpose_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._on_zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._on_zoom_out)
        view_menu.addAction(zoom_out_action)
        
        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset_action.triggered.connect(self._on_zoom_reset)
        view_menu.addAction(zoom_reset_action)
        
        view_menu.addSeparator()
        
        # Theme submenu
        theme_menu = view_menu.addMenu("🎨 &Theme")
        
        self.theme_system_action = QAction("System Default", self)
        self.theme_system_action.setCheckable(True)
        self.theme_system_action.triggered.connect(lambda: self._on_set_theme("system"))
        theme_menu.addAction(self.theme_system_action)
        
        self.theme_light_action = QAction("☀️ Light", self)
        self.theme_light_action.setCheckable(True)
        self.theme_light_action.triggered.connect(lambda: self._on_set_theme("light"))
        theme_menu.addAction(self.theme_light_action)
        
        self.theme_dark_action = QAction("🌙 Dark", self)
        self.theme_dark_action.setCheckable(True)
        self.theme_dark_action.triggered.connect(lambda: self._on_set_theme("dark"))
        theme_menu.addAction(self.theme_dark_action)
        
        # Group theme actions
        from PySide6.QtGui import QActionGroup
        theme_group = QActionGroup(self)
        theme_group.addAction(self.theme_system_action)
        theme_group.addAction(self.theme_light_action)
        theme_group.addAction(self.theme_dark_action)
        
        # Set initial checked state
        self._update_theme_menu()
        
        # Toggle dark mode shortcut
        toggle_theme_action = QAction("Toggle Dark Mode", self)
        toggle_theme_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        toggle_theme_action.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(toggle_theme_action)
        
        view_menu.addSeparator()
        
        # Panels submenu
        panels_menu = view_menu.addMenu("📊 &Panels")
        
        self.history_panel_action = QAction("Undo History", self)
        self.history_panel_action.setCheckable(True)
        self.history_panel_action.triggered.connect(self._on_toggle_history_panel)
        panels_menu.addAction(self.history_panel_action)
        
        # Playback menu
        playback_menu = menubar.addMenu("&Playback")
        
        play_action = QAction("▶ &Play/Pause", self)
        play_action.setShortcut(QKeySequence("Space"))
        play_action.triggered.connect(self._on_play_pause)
        playback_menu.addAction(play_action)
        
        stop_action = QAction("⏹ &Stop", self)
        stop_action.setShortcut(QKeySequence("Home"))
        stop_action.triggered.connect(self._on_stop)
        playback_menu.addAction(stop_action)
        
        playback_menu.addSeparator()
        
        tempo_up_action = QAction("Tempo +10%", self)
        tempo_up_action.setShortcut(QKeySequence("]"))
        tempo_up_action.triggered.connect(lambda: self._adjust_tempo(10))
        playback_menu.addAction(tempo_up_action)
        
        tempo_down_action = QAction("Tempo -10%", self)
        tempo_down_action.setShortcut(QKeySequence("["))
        tempo_down_action.triggered.connect(lambda: self._adjust_tempo(-10))
        playback_menu.addAction(tempo_down_action)
        
        tempo_reset_action = QAction("Reset Tempo", self)
        tempo_reset_action.triggered.connect(lambda: self._set_tempo(100))
        playback_menu.addAction(tempo_reset_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # Documentation
        docs_action = QAction("📖 &Documentation", self)
        docs_action.setShortcut(QKeySequence("F1"))
        docs_action.triggered.connect(self._on_open_docs)
        help_menu.addAction(docs_action)
        
        # Keyboard shortcuts
        shortcuts_action = QAction("⌨️ &Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self._on_show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        # Support the developer
        support_action = QAction("☕ &Support the Developer", self)
        support_action.triggered.connect(self._on_support_developer)
        help_menu.addAction(support_action)
        
        # GitHub
        github_action = QAction("🐙 &GitHub Repository", self)
        github_action.triggered.connect(self._on_open_github)
        help_menu.addAction(github_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """Set up the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Import button
        import_btn = QAction("Import", self)
        import_btn.setToolTip("Import sheet music image (Ctrl+I)")
        import_btn.triggered.connect(self._on_import_image)
        toolbar.addAction(import_btn)
        
        # Open button
        open_btn = QAction("Open", self)
        open_btn.setToolTip("Open MusicXML file (Ctrl+O)")
        open_btn.triggered.connect(self._on_open_file)
        toolbar.addAction(open_btn)
        
        toolbar.addSeparator()
        
        # Undo/Redo buttons
        undo_btn = QAction("Undo", self)
        undo_btn.setToolTip("Undo (Ctrl+Z)")
        undo_btn.triggered.connect(self._on_undo)
        toolbar.addAction(undo_btn)
        
        redo_btn = QAction("Redo", self)
        redo_btn.setToolTip("Redo (Ctrl+Shift+Z)")
        redo_btn.triggered.connect(self._on_redo)
        toolbar.addAction(redo_btn)
        
        toolbar.addSeparator()
        
        # Zoom buttons
        zoom_in_btn = QAction("Zoom In", self)
        zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        zoom_in_btn.triggered.connect(self._on_zoom_in)
        toolbar.addAction(zoom_in_btn)
        
        zoom_out_btn = QAction("Zoom Out", self)
        zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_btn.triggered.connect(self._on_zoom_out)
        toolbar.addAction(zoom_out_btn)
        
        toolbar.addSeparator()
        
        # Export buttons
        export_midi_btn = QAction("MIDI", self)
        export_midi_btn.setToolTip("Export to MIDI")
        export_midi_btn.triggered.connect(self._on_export_midi)
        toolbar.addAction(export_midi_btn)
        
        export_pdf_btn = QAction("PDF", self)
        export_pdf_btn.setToolTip("Export to PDF")
        export_pdf_btn.triggered.connect(self._on_export_pdf)
        toolbar.addAction(export_pdf_btn)
    
    def _setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Permanent widgets
        self.score_info_label = QLabel("No score loaded")
        self.status_bar.addPermanentWidget(self.score_info_label)
        
        self.status_bar.showMessage("Ready")
    
    def _setup_shortcuts(self):
        """Set up additional keyboard shortcuts."""
        pass  # Most are set up in menus
    
    def _update_recent_files_menu(self):
        """Update the recent files submenu."""
        self.recent_menu.clear()
        
        for filepath in self.config.recent_files:
            path = Path(filepath)
            if path.exists():
                action = QAction(path.name, self)
                action.setData(str(path))
                action.triggered.connect(
                    lambda checked, p=str(path): self.open_file(p)
                )
                self.recent_menu.addAction(action)
        
        if not self.config.recent_files:
            action = QAction("No recent files", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
    
    def _update_ui_state(self):
        """Update UI state based on current score."""
        has_score = self.current_score is not None
        
        self._undo_action.setEnabled(
            has_score and self.current_score.can_undo()
        )
        self._redo_action.setEnabled(
            has_score and self.current_score.can_redo()
        )
        
        # Update editor panel
        self.editor_panel.setEnabled(has_score)
        
        # Update score info label
        if self.current_score:
            info = (
                f"{self.current_score.num_parts} parts, "
                f"{self.current_score.num_measures} measures"
            )
            if self.current_score.key_signature:
                info += f" | {self.current_score.key_signature}"
            if self.current_score.time_signature:
                info += f" | {self.current_score.time_signature}"
            self.score_info_label.setText(info)
        else:
            self.score_info_label.setText("No score loaded")
    
    def _update_window_title(self):
        """Update window title based on current file."""
        title = "ScoreForge"
        
        if self.current_score:
            if self.current_score.title:
                title = f"{self.current_score.title} - {title}"
            elif self.current_file_path:
                title = f"{self.current_file_path.name} - {title}"
            
            if self.current_score.is_modified:
                title = f"* {title}"
        
        self.setWindowTitle(title)
    
    # Event handlers
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = Path(urls[0].toLocalFile())
                supported = OMRProcessor.get_supported_formats() + [
                    '.musicxml', '.xml', '.mxl', '.mid', '.midi'
                ]
                if path.suffix.lower() in supported:
                    event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            self.open_file(str(path))
    
    def closeEvent(self, event):
        """Handle window close."""
        # Check for unsaved changes
        if self.current_score and self.current_score.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        # Save window size
        self.config.gui.window_width = self.width()
        self.config.gui.window_height = self.height()
        self.config.save()
        
        event.accept()
    
    # Public methods
    
    def open_file(self, filepath: str):
        """
        Open a file (image, MusicXML, or MIDI).
        
        Args:
            filepath: Path to file
        """
        path = Path(filepath)
        
        if not path.exists():
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file does not exist:\n{filepath}"
            )
            return
        
        # Determine file type
        suffix = path.suffix.lower()
        
        if suffix in ['.musicxml', '.xml', '.mxl']:
            self._load_musicxml(path)
        elif suffix in ['.mid', '.midi']:
            self._load_midi(path)
        elif suffix in OMRProcessor.get_supported_formats():
            self._process_image(path)
        else:
            QMessageBox.warning(
                self,
                "Unsupported File",
                f"Unsupported file format: {suffix}"
            )
    
    def _load_musicxml(self, path: Path):
        """Load a MusicXML file."""
        try:
            self.status_bar.showMessage("Loading MusicXML...")
            QApplication.processEvents()
            
            self.current_score = Score.from_musicxml(path)
            self.current_file_path = path
            
            self._display_score()
            self.config.add_recent_file(str(path))
            self._update_recent_files_menu()
            
            self.status_bar.showMessage(f"Loaded: {path.name}", 5000)
            
        except Exception as e:
            logger.exception("Failed to load MusicXML")
            QMessageBox.critical(
                self,
                "Error Loading File",
                f"Failed to load MusicXML file:\n{str(e)}"
            )
    
    def _load_midi(self, path: Path):
        """Load a MIDI file."""
        try:
            self.status_bar.showMessage("Loading MIDI...")
            QApplication.processEvents()
            
            self.current_score = Score.from_midi(path)
            self.current_file_path = path
            
            self._display_score()
            self.config.add_recent_file(str(path))
            self._update_recent_files_menu()
            
            self.status_bar.showMessage(f"Loaded: {path.name}", 5000)
            
        except Exception as e:
            logger.exception("Failed to load MIDI")
            QMessageBox.critical(
                self,
                "Error Loading File",
                f"Failed to load MIDI file:\n{str(e)}"
            )
    
    def _process_image(self, path: Path):
        """Process an image through OMR."""
        # Create progress dialog
        progress = QProgressDialog(
            "Processing sheet music...",
            "Cancel",
            0, 100,
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        # Create OMR processor
        processor = OMRProcessor(engine=OMREngine.OEMER)
        
        # Create worker thread
        self._omr_worker = OMRWorker(processor, path)
        
        def on_progress(message: str, percent: int):
            progress.setLabelText(message)
            progress.setValue(percent)
        
        def on_finished(result):
            progress.close()
            self._omr_worker = None
            
            if result.success and result.score:
                self.current_score = result.score
                self.current_file_path = path
                self._display_score()
                self.config.add_recent_file(str(path))
                self._update_recent_files_menu()
                self.status_bar.showMessage(
                    f"OMR completed in {result.processing_time:.1f}s",
                    5000
                )
            else:
                QMessageBox.critical(
                    self,
                    "OMR Failed",
                    f"Failed to process image:\n{result.error_message}"
                )
        
        def on_error(error_msg: str):
            progress.close()
            self._omr_worker = None
            QMessageBox.critical(
                self,
                "OMR Error",
                f"Error during OMR processing:\n{error_msg}"
            )
        
        # Connect signals
        self._omr_worker.progress.connect(on_progress)
        self._omr_worker.finished.connect(on_finished)
        self._omr_worker.error.connect(on_error)
        
        # Handle cancel
        progress.canceled.connect(lambda: self._omr_worker.terminate())
        
        # Start processing
        self._omr_worker.start()
    
    def _display_score(self):
        """Display the current score in the viewer."""
        if self.current_score:
            self.score_view.set_score(self.current_score)
            self.editor_panel.set_score(self.current_score)
            self._update_interactive_editor()
            self._update_ui_state()
            self._update_window_title()
            
            # Load score into playback controls
            if self._playback_controls:
                self._playback_controls.load_score(self.current_score)
    
    # Action handlers
    
    def _on_import_image(self):
        """Handle import image action."""
        formats = " ".join(f"*{ext}" for ext in OMRProcessor.get_supported_formats())
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Sheet Music Image",
            "",
            f"Image Files ({formats});;All Files (*)"
        )
        
        if filepath:
            self.open_file(filepath)
    
    def _on_open_file(self):
        """Handle open file action."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Music Files (*.musicxml *.xml *.mxl *.mid *.midi);;All Files (*)"
        )
        
        if filepath:
            self.open_file(filepath)
    
    def _on_save(self):
        """Handle save action."""
        if not self.current_score:
            return
        
        if self.current_file_path and self.current_file_path.suffix.lower() in ['.musicxml', '.xml']:
            # Save to existing file
            try:
                self.current_score.to_musicxml(self.current_file_path)
                self.current_score._is_modified = False
                self._update_window_title()
                self.status_bar.showMessage(f"Saved: {self.current_file_path.name}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save:\n{str(e)}")
        else:
            # Save As
            self._on_export_musicxml()
    
    def _on_export_midi(self):
        """Handle export to MIDI action."""
        if not self.current_score:
            QMessageBox.warning(self, "No Score", "No score to export.")
            return
        
        default_name = "score.mid"
        if self.current_file_path:
            default_name = self.current_file_path.stem + ".mid"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export to MIDI",
            default_name,
            "MIDI Files (*.mid *.midi)"
        )
        
        if filepath:
            try:
                exporter = MidiExporter()
                output_path = exporter.export(self.current_score, filepath)
                self.status_bar.showMessage(f"Exported: {output_path.name}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
    
    def _on_export_musicxml(self):
        """Handle export to MusicXML action."""
        if not self.current_score:
            QMessageBox.warning(self, "No Score", "No score to export.")
            return
        
        default_name = "score.musicxml"
        if self.current_file_path:
            default_name = self.current_file_path.stem + ".musicxml"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export to MusicXML",
            default_name,
            "MusicXML Files (*.musicxml *.xml);;Compressed MusicXML (*.mxl)"
        )
        
        if filepath:
            try:
                exporter = MusicXMLExporter()
                output_path = exporter.export(self.current_score, filepath)
                self.status_bar.showMessage(f"Exported: {output_path.name}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
    
    def _on_export_pdf(self):
        """Handle export to PDF action."""
        if not self.current_score:
            QMessageBox.warning(self, "No Score", "No score to export.")
            return
        
        default_name = "score.pdf"
        if self.current_file_path:
            default_name = self.current_file_path.stem + ".pdf"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export to PDF",
            default_name,
            "PDF Files (*.pdf)"
        )
        
        if filepath:
            try:
                self.status_bar.showMessage("Generating PDF...")
                QApplication.processEvents()
                
                exporter = PDFExporter()
                output_path = exporter.export(self.current_score, filepath)
                self.status_bar.showMessage(f"Exported: {output_path.name}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
    
    def _on_undo(self):
        """Handle undo action."""
        if self.current_score and self.current_score.undo():
            self._display_score()
            self.status_bar.showMessage("Undone", 2000)
    
    def _on_redo(self):
        """Handle redo action."""
        if self.current_score and self.current_score.redo():
            self._display_score()
            self.status_bar.showMessage("Redone", 2000)
    
    def _on_zoom_in(self):
        """Handle zoom in action."""
        self.score_view.zoom_in()
    
    def _on_zoom_out(self):
        """Handle zoom out action."""
        self.score_view.zoom_out()
    
    def _on_zoom_reset(self):
        """Handle zoom reset action."""
        self.score_view.zoom_reset()
    
    def _on_transpose(self, interval: str):
        """Handle transpose request from editor panel."""
        if self.current_score:
            try:
                self.current_score.transpose(interval)
                self._display_score()
                self.status_bar.showMessage(f"Transposed by {interval}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Transpose Error", str(e))
    
    def _on_octave_shift(self, octaves: int):
        """Handle octave shift request from editor panel."""
        if self.current_score:
            try:
                self.current_score.shift_octave(octaves)
                self._display_score()
                direction = "up" if octaves > 0 else "down"
                self.status_bar.showMessage(
                    f"Shifted {abs(octaves)} octave(s) {direction}", 3000
                )
            except Exception as e:
                QMessageBox.critical(self, "Octave Shift Error", str(e))
    
    def _on_key_change(self, new_key: str):
        """Handle key change request from editor panel."""
        if self.current_score:
            try:
                self.current_score.change_key(new_key)
                self._display_score()
                self.status_bar.showMessage(f"Changed key to {new_key}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Key Change Error", str(e))
    
    def _on_apply_commands(self, elements: list):
        """Handle apply commands request from command input panel."""
        from sheet_music_scanner.core.command_executor import CommandExecutor
        from sheet_music_scanner.core.command_parser import (
            ParsedNote, ParsedChord, ParsedCommand,
        )
        from sheet_music_scanner.gui.interactive_editor import NotePosition
        
        try:
            executor = CommandExecutor()
            
            if self.current_score:
                # Add to existing score
                executor.add_elements_to_score(self.current_score, elements)
                self.status_bar.showMessage(
                    f"Added {len(elements)} elements to score", 3000
                )
            else:
                # Create new score from commands
                self.current_score = executor.create_score_from_elements(
                    elements, "New Score"
                )
                self.status_bar.showMessage(
                    f"Created new score with {len(elements)} elements", 3000
                )
            
            # Update displays
            self._display_score()
            self._update_interactive_editor()
            
        except Exception as e:
            logger.exception("Error applying commands")
            QMessageBox.critical(
                self, "Command Error", 
                f"Failed to apply commands:\n{str(e)}"
            )
    
    def _on_interactive_note_changed(self, position, change_type: str, value):
        """Handle note changes from the interactive editor."""
        if not self.current_score:
            return
        
        try:
            if change_type == "pitch":
                # Value is the pitch offset in half steps
                offset = value
                if offset != 0:
                    # Find and modify the note in the score
                    part = self.current_score._score.parts[position.part_index]
                    measures = list(part.getElementsByClass('Measure'))
                    
                    if position.measure_index < len(measures):
                        measure = measures[position.measure_index]
                        notes = list(measure.notes)
                        
                        if position.note_index < len(notes):
                            note_obj = notes[position.note_index]
                            note_obj.transpose(offset, inPlace=True)
                            
                            self.status_bar.showMessage(
                                f"Changed pitch by {offset} half steps", 2000
                            )
            
            # Refresh the score display
            self._display_score()
            
        except Exception as e:
            logger.exception("Error updating note")
            self.status_bar.showMessage(f"Error: {str(e)}", 3000)
    
    def _on_score_modified(self):
        """Handle score modification from interactive editor."""
        # Mark document as modified
        self.setWindowModified(True)
        self._update_window_title()
    
    def _update_interactive_editor(self):
        """Update the interactive editor with current score notes."""
        from sheet_music_scanner.gui.interactive_editor import NotePosition
        
        if not self.current_score:
            self.interactive_editor.load_notes([])
            return
        
        positions = []
        
        try:
            for part_idx, part in enumerate(self.current_score._score.parts):
                measures = list(part.getElementsByClass('Measure'))
                
                for measure_idx, measure in enumerate(measures):
                    notes = list(measure.notes)
                    
                    for note_idx, n in enumerate(notes):
                        # Handle both notes and chords
                        if hasattr(n, 'pitch'):
                            pitch_name = n.pitch.name
                            octave = n.pitch.octave
                        elif hasattr(n, 'pitches') and n.pitches:
                            # Chord - use the first pitch for display
                            pitch_name = n.pitches[0].name
                            octave = n.pitches[0].octave
                        else:
                            continue
                        
                        lyric = n.lyric if hasattr(n, 'lyric') else None
                        
                        positions.append(NotePosition(
                            part_index=part_idx,
                            measure_index=measure_idx,
                            note_index=note_idx,
                            pitch=pitch_name,
                            octave=octave or 4,
                            duration=n.duration.quarterLength,
                            lyric=lyric,
                        ))
            
            self.interactive_editor.load_notes(positions)
            
        except Exception as e:
            logger.exception("Error updating interactive editor")
    
    def _on_show_transpose_dialog(self):
        """Show the transpose dialog."""
        from sheet_music_scanner.gui.dialogs.transpose_dialog import TransposeDialog
        
        if not self.current_score:
            QMessageBox.warning(self, "No Score", "No score to transpose.")
            return
        
        dialog = TransposeDialog(self)
        if dialog.exec():
            interval = dialog.get_interval()
            self._on_transpose(interval)
    
    def _on_settings(self):
        """Show settings dialog."""
        from sheet_music_scanner.gui.dialogs.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            dialog.apply_settings()
            self.config.save()
    
    def _on_set_theme(self, theme_name: str):
        """Set the application theme."""
        from sheet_music_scanner.gui.theme import get_theme_manager, Theme
        
        theme_map = {
            "system": Theme.SYSTEM,
            "light": Theme.LIGHT,
            "dark": Theme.DARK,
        }
        theme = theme_map.get(theme_name, Theme.SYSTEM)
        get_theme_manager().set_theme(theme)
        self._update_theme_menu()
        
        # Also update config
        self.config.gui.theme = theme_name
        self.config.save()
    
    def _on_toggle_theme(self):
        """Toggle between light and dark themes."""
        from sheet_music_scanner.gui.theme import get_theme_manager
        
        manager = get_theme_manager()
        manager.toggle_theme()
        self._update_theme_menu()
        
        # Update config
        theme_name = "dark" if manager.is_dark else "light"
        self.config.gui.theme = theme_name
        self.config.save()
        
        self.status_bar.showMessage(
            f"Switched to {'dark' if manager.is_dark else 'light'} theme", 2000
        )
    
    def _update_theme_menu(self):
        """Update theme menu checked states."""
        from sheet_music_scanner.gui.theme import get_theme_manager, Theme
        
        manager = get_theme_manager()
        current = manager.current_theme
        
        self.theme_system_action.setChecked(current == Theme.SYSTEM)
        self.theme_light_action.setChecked(current == Theme.LIGHT)
        self.theme_dark_action.setChecked(current == Theme.DARK)
    
    def _on_open_docs(self):
        """Open documentation."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        # Try local docs first, then online
        docs_path = Path(__file__).parent.parent.parent / "docs" / "index.html"
        if docs_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(docs_path)))
        else:
            # Open GitHub wiki or README
            QDesktopServices.openUrl(
                QUrl("https://github.com/yourusername/sheet-music-scanner#readme")
            )
    
    def _on_show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts = """
        <h3>Keyboard Shortcuts</h3>
        
        <h4>File</h4>
        <table>
            <tr><td><b>Ctrl+I</b></td><td>Import Image</td></tr>
            <tr><td><b>Ctrl+O</b></td><td>Open MusicXML</td></tr>
            <tr><td><b>Ctrl+S</b></td><td>Save</td></tr>
            <tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>
        </table>
        
        <h4>Edit</h4>
        <table>
            <tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
            <tr><td><b>Ctrl+Shift+Z</b></td><td>Redo</td></tr>
            <tr><td><b>Ctrl+T</b></td><td>Transpose</td></tr>
        </table>
        
        <h4>View</h4>
        <table>
            <tr><td><b>Ctrl++</b></td><td>Zoom In</td></tr>
            <tr><td><b>Ctrl+-</b></td><td>Zoom Out</td></tr>
            <tr><td><b>Ctrl+0</b></td><td>Reset Zoom</td></tr>
            <tr><td><b>Ctrl+Shift+D</b></td><td>Toggle Dark Mode</td></tr>
        </table>
        
        <h4>Interactive Editor</h4>
        <table>
            <tr><td><b>↑/↓</b></td><td>Move note pitch</td></tr>
            <tr><td><b>Delete</b></td><td>Delete selected note</td></tr>
            <tr><td><b>Click+Drag</b></td><td>Drag note to change pitch</td></tr>
        </table>
        """
        
        QMessageBox.information(
            self, "Keyboard Shortcuts", shortcuts
        )
    
    def _on_support_developer(self):
        """Open Buy Me a Coffee page."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        # You can customize this URL to your actual Buy Me a Coffee page
        QDesktopServices.openUrl(
            QUrl("https://www.buymeacoffee.com/sheetmusicscanner")
        )
        
        self.status_bar.showMessage("Thank you for your support! ☕", 3000)
    
    def _on_open_github(self):
        """Open GitHub repository."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        QDesktopServices.openUrl(
            QUrl("https://github.com/yourusername/sheet-music-scanner")
        )
    
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Sheet Music Scanner",
            """<h2>Sheet Music Scanner</h2>
            <p>Version 0.2.0</p>
            <p>Convert scanned sheet music to digital formats.</p>
            <p>Features:</p>
            <ul>
                <li>Optical Music Recognition (OMR)</li>
                <li>Command-based note entry</li>
                <li>Interactive drag-and-drop editing</li>
                <li>MIDI playback with tempo control</li>
                <li>Score templates (Lead Sheet, SATB, etc.)</li>
                <li>Batch processing</li>
                <li>Auto-save and crash recovery</li>
                <li>Export to MIDI, MusicXML, and PDF</li>
            </ul>
            <p>Built with music21, PySide6, and Verovio.</p>
            <p>
                <a href="https://www.buymeacoffee.com/sheetmusicscanner">
                    ☕ Support the Developer
                </a>
            </p>
            """
        )
    
    # ========== New Feature Methods ==========
    
    def _setup_dock_panels(self):
        """Set up dockable panels."""
        # Undo History Panel
        self._history_dock = QDockWidget("Undo History", self)
        self._history_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self._history_panel = UndoHistoryPanel()
        self._history_panel.set_manager(self._undo_manager)
        self._history_dock.setWidget(self._history_panel)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._history_dock)
        self._history_dock.hide()  # Hidden by default
    
    def _setup_autosave(self):
        """Set up auto-save functionality."""
        # Set up callbacks
        def get_state():
            if self.current_score:
                return self.current_score.to_musicxml_bytes()
            return b''
        
        def set_state(data):
            if data:
                try:
                    self.current_score = Score.from_musicxml_bytes(data)
                    self._display_score()
                except Exception as e:
                    logger.error(f"Failed to restore state: {e}")
        
        self._autosave.set_callbacks(get_state, set_state)
        self._autosave.start()
    
    def _check_recovery(self):
        """Check for and offer crash recovery."""
        if self._autosave.has_recovery_data:
            info = self._autosave.get_recovery_info()
            
            reply = QMessageBox.question(
                self,
                "Recover Unsaved Work?",
                "The application closed unexpectedly last time.\n\n"
                f"Last save: {info.get('last_save', 'Unknown')}\n\n"
                "Would you like to recover your unsaved work?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                data = self._autosave.recover()
                if data:
                    try:
                        self.current_score = Score.from_musicxml_bytes(data)
                        self._display_score()
                        self.status_bar.showMessage("Recovered unsaved work", 5000)
                    except Exception as e:
                        QMessageBox.warning(
                            self, "Recovery Failed",
                            f"Failed to recover data: {str(e)}"
                        )
            else:
                self._autosave.clear_recovery()
    
    def _on_new_from_template(self):
        """Create new score from template."""
        from sheet_music_scanner.gui.dialogs.template_dialog import TemplateDialog
        
        dialog = TemplateDialog(self, self.current_score)
        dialog.template_selected.connect(self._create_from_template)
        dialog.exec()
    
    def _create_from_template(self, template):
        """Create a score from the selected template."""
        try:
            m21_score = template.create_score()
            self.current_score = Score(m21_score)
            self.current_file_path = None
            self._display_score()
            self.status_bar.showMessage(f"Created new score from template: {template.name}", 3000)
        except Exception as e:
            QMessageBox.critical(
                self, "Template Error",
                f"Failed to create score from template:\n{str(e)}"
            )
    
    def _on_batch_processing(self):
        """Show batch processing dialog."""
        from sheet_music_scanner.gui.dialogs.batch_dialog import BatchProcessDialog
        
        dialog = BatchProcessDialog(self)
        dialog.exec()
    
    def _on_toggle_history_panel(self, checked: bool):
        """Toggle the undo history panel."""
        if checked:
            self._history_dock.show()
        else:
            self._history_dock.hide()
    
    def _on_play_pause(self):
        """Toggle play/pause."""
        if self._playback_controls:
            self._playback_controls.toggle_play_pause()
    
    def _on_stop(self):
        """Stop playback."""
        if self._playback_controls:
            self._playback_controls.stop()
    
    def _adjust_tempo(self, delta: int):
        """Adjust playback tempo by delta percent."""
        if self._playback_controls:
            current = self._playback_controls.controls.tempo_spin.value()
            self._playback_controls.controls.tempo_spin.setValue(current + delta)
    
    def _set_tempo(self, value: int):
        """Set playback tempo to specific value."""
        if self._playback_controls:
            self._playback_controls.controls.tempo_spin.setValue(value)
    
    def _mark_document_dirty(self):
        """Mark the document as modified for auto-save."""
        if self.current_score:
            self._autosave.mark_dirty()
            self._autosave.set_current_file(self.current_file_path)
    
    def closeEvent(self, event):
        """Handle window close - enhanced with cleanup."""
        # Stop auto-save
        self._autosave.stop()
        
        # Cleanup playback
        if self._playback_controls:
            self._playback_controls.cleanup()
        
        # Check for unsaved changes
        if self.current_score and self.current_score.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        # Save window size
        self.config.gui.window_width = self.width()
        self.config.gui.window_height = self.height()
        self.config.save()
        
        event.accept()
