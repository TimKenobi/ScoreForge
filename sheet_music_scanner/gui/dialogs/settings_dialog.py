"""
Settings Dialog - Application settings configuration.
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QCheckBox, QSpinBox,
    QFormLayout, QDialogButtonBox, QTabWidget, QWidget,
    QLineEdit, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from sheet_music_scanner.config import Config


class SettingsDialog(QDialog):
    """
    Settings dialog for configuring application options.
    
    Provides configuration for:
    - OMR settings
    - Export settings
    - GUI preferences
    - External tool paths
    """
    
    def __init__(self, config: Config, parent: Optional[QDialog] = None):
        super().__init__(parent)
        
        self.config = config
        
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Tab widget for different settings categories
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # General tab
        general_tab = self._create_general_tab()
        self.tabs.addTab(general_tab, "General")
        
        # OMR tab
        omr_tab = self._create_omr_tab()
        self.tabs.addTab(omr_tab, "OMR")
        
        # Export tab
        export_tab = self._create_export_tab()
        self.tabs.addTab(export_tab, "Export")
        
        # Tools tab
        tools_tab = self._create_tools_tab()
        self.tabs.addTab(tools_tab, "External Tools")
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.apply_settings
        )
        layout.addWidget(button_box)
    
    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        appearance_layout.addRow("Theme:", self.theme_combo)
        
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setMinimum(50)
        self.zoom_spin.setMaximum(200)
        self.zoom_spin.setSuffix("%")
        appearance_layout.addRow("Default Zoom:", self.zoom_spin)
        
        layout.addWidget(appearance_group)
        
        # Interface group
        interface_group = QGroupBox("Interface")
        interface_layout = QVBoxLayout(interface_group)
        
        self.show_toolbar_check = QCheckBox("Show toolbar")
        interface_layout.addWidget(self.show_toolbar_check)
        
        self.show_statusbar_check = QCheckBox("Show status bar")
        interface_layout.addWidget(self.show_statusbar_check)
        
        layout.addWidget(interface_group)
        
        # Recent files group
        recent_group = QGroupBox("Recent Files")
        recent_layout = QFormLayout(recent_group)
        
        self.recent_max_spin = QSpinBox()
        self.recent_max_spin.setMinimum(1)
        self.recent_max_spin.setMaximum(20)
        recent_layout.addRow("Maximum entries:", self.recent_max_spin)
        
        clear_recent_btn = QPushButton("Clear Recent Files")
        clear_recent_btn.clicked.connect(self._on_clear_recent)
        recent_layout.addRow(clear_recent_btn)
        
        layout.addWidget(recent_group)
        
        layout.addStretch()
        return widget
    
    def _create_omr_tab(self) -> QWidget:
        """Create the OMR settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Engine group
        engine_group = QGroupBox("OMR Engine")
        engine_layout = QFormLayout(engine_group)
        
        self.omr_engine_combo = QComboBox()
        self.omr_engine_combo.addItem("oemer (Deep Learning)", "oemer")
        self.omr_engine_combo.addItem("Audiveris (External)", "audiveris")
        engine_layout.addRow("Engine:", self.omr_engine_combo)
        
        layout.addWidget(engine_group)
        
        # Processing group
        processing_group = QGroupBox("Image Processing")
        processing_layout = QVBoxLayout(processing_group)
        
        self.use_gpu_check = QCheckBox("Use GPU acceleration (if available)")
        processing_layout.addWidget(self.use_gpu_check)
        
        self.deskew_check = QCheckBox("Auto-deskew images")
        processing_layout.addWidget(self.deskew_check)
        
        self.contrast_check = QCheckBox("Enhance contrast")
        processing_layout.addWidget(self.contrast_check)
        
        layout.addWidget(processing_group)
        
        layout.addStretch()
        return widget
    
    def _create_export_tab(self) -> QWidget:
        """Create the export settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # MIDI group
        midi_group = QGroupBox("MIDI Export")
        midi_layout = QFormLayout(midi_group)
        
        self.midi_velocity_spin = QSpinBox()
        self.midi_velocity_spin.setMinimum(1)
        self.midi_velocity_spin.setMaximum(127)
        midi_layout.addRow("Default velocity:", self.midi_velocity_spin)
        
        self.midi_tempo_spin = QSpinBox()
        self.midi_tempo_spin.setMinimum(20)
        self.midi_tempo_spin.setMaximum(300)
        midi_layout.addRow("Default tempo (BPM):", self.midi_tempo_spin)
        
        layout.addWidget(midi_group)
        
        # PDF group
        pdf_group = QGroupBox("PDF Export")
        pdf_layout = QFormLayout(pdf_group)
        
        self.paper_size_combo = QComboBox()
        self.paper_size_combo.addItems(["Letter", "A4", "Legal"])
        pdf_layout.addRow("Paper size:", self.paper_size_combo)
        
        self.staff_size_spin = QSpinBox()
        self.staff_size_spin.setMinimum(12)
        self.staff_size_spin.setMaximum(26)
        pdf_layout.addRow("Staff size (pt):", self.staff_size_spin)
        
        self.include_lyrics_check = QCheckBox("Include lyrics in PDF")
        pdf_layout.addRow(self.include_lyrics_check)
        
        layout.addWidget(pdf_group)
        
        layout.addStretch()
        return widget
    
    def _create_tools_tab(self) -> QWidget:
        """Create the external tools settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # LilyPond group
        lilypond_group = QGroupBox("LilyPond")
        lilypond_layout = QVBoxLayout(lilypond_group)
        
        path_layout = QHBoxLayout()
        self.lilypond_path_edit = QLineEdit()
        self.lilypond_path_edit.setPlaceholderText("Path to LilyPond executable...")
        path_layout.addWidget(self.lilypond_path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_lilypond)
        path_layout.addWidget(browse_btn)
        
        lilypond_layout.addLayout(path_layout)
        
        self.lilypond_status = QLabel()
        lilypond_layout.addWidget(self.lilypond_status)
        
        layout.addWidget(lilypond_group)
        
        # MuseScore group
        musescore_group = QGroupBox("MuseScore")
        musescore_layout = QVBoxLayout(musescore_group)
        
        ms_path_layout = QHBoxLayout()
        self.musescore_path_edit = QLineEdit()
        self.musescore_path_edit.setPlaceholderText("Path to MuseScore executable...")
        ms_path_layout.addWidget(self.musescore_path_edit)
        
        ms_browse_btn = QPushButton("Browse...")
        ms_browse_btn.clicked.connect(self._on_browse_musescore)
        ms_path_layout.addWidget(ms_browse_btn)
        
        musescore_layout.addLayout(ms_path_layout)
        
        self.musescore_status = QLabel()
        musescore_layout.addWidget(self.musescore_status)
        
        layout.addWidget(musescore_group)
        
        # Info
        info_label = QLabel(
            "These tools are optional but enable additional features:\n"
            "• LilyPond: High-quality PDF export\n"
            "• MuseScore: Alternative PDF export"
        )
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        return widget
    
    def _load_settings(self):
        """Load current settings into the dialog."""
        # General
        theme_index = ["system", "light", "dark"].index(
            self.config.gui.theme.lower()
        )
        self.theme_combo.setCurrentIndex(theme_index)
        self.zoom_spin.setValue(int(self.config.gui.notation_zoom * 100))
        self.show_toolbar_check.setChecked(self.config.gui.show_toolbar)
        self.show_statusbar_check.setChecked(self.config.gui.show_statusbar)
        self.recent_max_spin.setValue(self.config.gui.recent_files_max)
        
        # OMR
        engine_index = 0 if self.config.omr.engine == "oemer" else 1
        self.omr_engine_combo.setCurrentIndex(engine_index)
        self.use_gpu_check.setChecked(self.config.omr.use_gpu)
        self.deskew_check.setChecked(self.config.omr.deskew_enabled)
        self.contrast_check.setChecked(self.config.omr.contrast_enhancement)
        
        # Export
        self.midi_velocity_spin.setValue(self.config.export.midi_velocity)
        self.midi_tempo_spin.setValue(self.config.export.midi_tempo)
        paper_index = ["letter", "a4", "legal"].index(
            self.config.export.pdf_paper_size.lower()
        )
        self.paper_size_combo.setCurrentIndex(paper_index)
        self.staff_size_spin.setValue(self.config.export.pdf_staff_size)
        self.include_lyrics_check.setChecked(self.config.export.include_lyrics_in_pdf)
        
        # Tools
        self.lilypond_path_edit.setText(self.config.lilypond_path or "")
        self.musescore_path_edit.setText(self.config.musescore_path or "")
        
        self._update_tool_status()
    
    def _update_tool_status(self):
        """Update the status of external tools."""
        lilypond_path = self.lilypond_path_edit.text()
        if lilypond_path and Path(lilypond_path).exists():
            self.lilypond_status.setText("✅ Found")
            self.lilypond_status.setStyleSheet("color: green;")
        elif lilypond_path:
            self.lilypond_status.setText("❌ Not found at specified path")
            self.lilypond_status.setStyleSheet("color: red;")
        else:
            self.lilypond_status.setText("⚠️ Not configured")
            self.lilypond_status.setStyleSheet("color: orange;")
        
        musescore_path = self.musescore_path_edit.text()
        if musescore_path and Path(musescore_path).exists():
            self.musescore_status.setText("✅ Found")
            self.musescore_status.setStyleSheet("color: green;")
        elif musescore_path:
            self.musescore_status.setText("❌ Not found at specified path")
            self.musescore_status.setStyleSheet("color: red;")
        else:
            self.musescore_status.setText("⚠️ Not configured")
            self.musescore_status.setStyleSheet("color: orange;")
    
    def apply_settings(self):
        """Apply settings to config."""
        # General
        self.config.gui.theme = ["system", "light", "dark"][
            self.theme_combo.currentIndex()
        ]
        self.config.gui.notation_zoom = self.zoom_spin.value() / 100.0
        self.config.gui.show_toolbar = self.show_toolbar_check.isChecked()
        self.config.gui.show_statusbar = self.show_statusbar_check.isChecked()
        self.config.gui.recent_files_max = self.recent_max_spin.value()
        
        # OMR
        self.config.omr.engine = self.omr_engine_combo.currentData()
        self.config.omr.use_gpu = self.use_gpu_check.isChecked()
        self.config.omr.deskew_enabled = self.deskew_check.isChecked()
        self.config.omr.contrast_enhancement = self.contrast_check.isChecked()
        
        # Export
        self.config.export.midi_velocity = self.midi_velocity_spin.value()
        self.config.export.midi_tempo = self.midi_tempo_spin.value()
        self.config.export.pdf_paper_size = ["letter", "a4", "legal"][
            self.paper_size_combo.currentIndex()
        ]
        self.config.export.pdf_staff_size = self.staff_size_spin.value()
        self.config.export.include_lyrics_in_pdf = self.include_lyrics_check.isChecked()
        
        # Tools
        lilypond_path = self.lilypond_path_edit.text().strip()
        self.config.lilypond_path = lilypond_path if lilypond_path else None
        
        musescore_path = self.musescore_path_edit.text().strip()
        self.config.musescore_path = musescore_path if musescore_path else None
    
    def _on_browse_lilypond(self):
        """Browse for LilyPond executable."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select LilyPond Executable",
            "",
            "Executables (*);;All Files (*)"
        )
        if filepath:
            self.lilypond_path_edit.setText(filepath)
            self._update_tool_status()
    
    def _on_browse_musescore(self):
        """Browse for MuseScore executable."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select MuseScore Executable",
            "",
            "Executables (*);;All Files (*)"
        )
        if filepath:
            self.musescore_path_edit.setText(filepath)
            self._update_tool_status()
    
    def _on_clear_recent(self):
        """Clear recent files list."""
        reply = QMessageBox.question(
            self,
            "Clear Recent Files",
            "Are you sure you want to clear the recent files list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config.recent_files.clear()
            self.config.save()
