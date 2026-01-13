"""
Editor Panel - Side panel for editing score properties.
"""

from __future__ import annotations

from typing import Optional
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QTabWidget, QScrollArea,
    QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.core.operations import (
    get_available_keys,
    get_interval_options,
)

logger = logging.getLogger(__name__)


class EditorPanel(QWidget):
    """
    Side panel for editing score properties.
    
    Provides controls for:
    - Transposition
    - Octave shifting
    - Key changes
    - Lyrics editing
    - Score metadata
    """
    
    # Signals
    transpose_requested = Signal(str)  # interval
    octave_shift_requested = Signal(int)  # octaves
    key_change_requested = Signal(str)  # new key
    lyric_changed = Signal(int, int, float, str)  # part, measure, beat, text
    metadata_changed = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._score: Optional[Score] = None
        self._setup_ui()
        self.setEnabled(False)  # Disabled until score is loaded
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Create tab widget for different editing modes
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Transform tab
        transform_tab = self._create_transform_tab()
        self.tabs.addTab(transform_tab, "Transform")
        
        # Lyrics tab
        lyrics_tab = self._create_lyrics_tab()
        self.tabs.addTab(lyrics_tab, "Lyrics")
        
        # Info tab
        info_tab = self._create_info_tab()
        self.tabs.addTab(info_tab, "Info")
        
        # Stretch to fill remaining space
        layout.addStretch()
    
    def _create_transform_tab(self) -> QWidget:
        """Create the transform/transposition tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        
        # Transpose group
        transpose_group = QGroupBox("Transpose")
        transpose_layout = QVBoxLayout(transpose_group)
        
        # Interval selection
        interval_layout = QFormLayout()
        self.interval_combo = QComboBox()
        for code, name in get_interval_options():
            self.interval_combo.addItem(name, code)
        interval_layout.addRow("Interval:", self.interval_combo)
        transpose_layout.addLayout(interval_layout)
        
        # Transpose button
        self.transpose_btn = QPushButton("Transpose")
        self.transpose_btn.clicked.connect(self._on_transpose_clicked)
        transpose_layout.addWidget(self.transpose_btn)
        
        layout.addWidget(transpose_group)
        
        # Octave shift group
        octave_group = QGroupBox("Octave Shift")
        octave_layout = QVBoxLayout(octave_group)
        
        octave_btn_layout = QHBoxLayout()
        
        self.octave_down_btn = QPushButton("▼ Down")
        self.octave_down_btn.clicked.connect(lambda: self._on_octave_shift(-1))
        octave_btn_layout.addWidget(self.octave_down_btn)
        
        self.octave_up_btn = QPushButton("▲ Up")
        self.octave_up_btn.clicked.connect(lambda: self._on_octave_shift(1))
        octave_btn_layout.addWidget(self.octave_up_btn)
        
        octave_layout.addLayout(octave_btn_layout)
        
        # Multi-octave shift
        multi_octave_layout = QHBoxLayout()
        multi_octave_layout.addWidget(QLabel("Shift by:"))
        
        self.octave_spin = QSpinBox()
        self.octave_spin.setMinimum(-4)
        self.octave_spin.setMaximum(4)
        self.octave_spin.setValue(0)
        multi_octave_layout.addWidget(self.octave_spin)
        
        multi_octave_layout.addWidget(QLabel("octaves"))
        
        self.octave_apply_btn = QPushButton("Apply")
        self.octave_apply_btn.clicked.connect(self._on_octave_apply)
        multi_octave_layout.addWidget(self.octave_apply_btn)
        
        octave_layout.addLayout(multi_octave_layout)
        
        layout.addWidget(octave_group)
        
        # Key change group
        key_group = QGroupBox("Change Key")
        key_layout = QVBoxLayout(key_group)
        
        # Current key display
        current_key_layout = QHBoxLayout()
        current_key_layout.addWidget(QLabel("Current:"))
        self.current_key_label = QLabel("—")
        self.current_key_label.setStyleSheet("font-weight: bold;")
        current_key_layout.addWidget(self.current_key_label)
        current_key_layout.addStretch()
        key_layout.addLayout(current_key_layout)
        
        # New key selection
        new_key_layout = QFormLayout()
        self.key_combo = QComboBox()
        for key_name in get_available_keys():
            self.key_combo.addItem(key_name)
        new_key_layout.addRow("New key:", self.key_combo)
        key_layout.addLayout(new_key_layout)
        
        # Change key button
        self.change_key_btn = QPushButton("Change Key")
        self.change_key_btn.clicked.connect(self._on_key_change_clicked)
        key_layout.addWidget(self.change_key_btn)
        
        layout.addWidget(key_group)
        
        layout.addStretch()
        return widget
    
    def _create_lyrics_tab(self) -> QWidget:
        """Create the lyrics editing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        
        # Instructions
        instructions = QLabel(
            "Select a note in the score to edit its lyric, "
            "or use the bulk editor below."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(instructions)
        
        # Note selection
        note_group = QGroupBox("Selected Note")
        note_layout = QFormLayout(note_group)
        
        # Part selector
        self.lyric_part_spin = QSpinBox()
        self.lyric_part_spin.setMinimum(1)
        self.lyric_part_spin.setMaximum(1)
        note_layout.addRow("Part:", self.lyric_part_spin)
        
        # Measure selector
        self.lyric_measure_spin = QSpinBox()
        self.lyric_measure_spin.setMinimum(1)
        self.lyric_measure_spin.setMaximum(1)
        note_layout.addRow("Measure:", self.lyric_measure_spin)
        
        # Beat selector
        self.lyric_beat_spin = QSpinBox()
        self.lyric_beat_spin.setMinimum(1)
        self.lyric_beat_spin.setMaximum(16)
        note_layout.addRow("Beat:", self.lyric_beat_spin)
        
        # Lyric input
        self.lyric_input = QLineEdit()
        self.lyric_input.setPlaceholderText("Enter lyric text...")
        note_layout.addRow("Lyric:", self.lyric_input)
        
        # Apply button
        self.apply_lyric_btn = QPushButton("Apply Lyric")
        self.apply_lyric_btn.clicked.connect(self._on_apply_lyric)
        note_layout.addRow(self.apply_lyric_btn)
        
        layout.addWidget(note_group)
        
        # Bulk lyrics group
        bulk_group = QGroupBox("Bulk Lyrics")
        bulk_layout = QVBoxLayout(bulk_group)
        
        bulk_instructions = QLabel(
            "Enter lyrics separated by spaces or newlines. "
            "Each word will be assigned to consecutive notes."
        )
        bulk_instructions.setWordWrap(True)
        bulk_instructions.setStyleSheet("color: #666; font-size: 11px;")
        bulk_layout.addWidget(bulk_instructions)
        
        self.bulk_lyrics_text = QTextEdit()
        self.bulk_lyrics_text.setPlaceholderText("Enter lyrics here...")
        self.bulk_lyrics_text.setMaximumHeight(100)
        bulk_layout.addWidget(self.bulk_lyrics_text)
        
        bulk_btn_layout = QHBoxLayout()
        
        self.apply_bulk_btn = QPushButton("Apply to Score")
        self.apply_bulk_btn.clicked.connect(self._on_apply_bulk_lyrics)
        bulk_btn_layout.addWidget(self.apply_bulk_btn)
        
        self.clear_lyrics_btn = QPushButton("Clear All")
        self.clear_lyrics_btn.clicked.connect(self._on_clear_lyrics)
        bulk_btn_layout.addWidget(self.clear_lyrics_btn)
        
        bulk_layout.addLayout(bulk_btn_layout)
        
        layout.addWidget(bulk_group)
        
        layout.addStretch()
        return widget
    
    def _create_info_tab(self) -> QWidget:
        """Create the score information/metadata tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        
        # Metadata group
        metadata_group = QGroupBox("Score Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Score title...")
        self.title_input.textChanged.connect(self._on_title_changed)
        metadata_layout.addRow("Title:", self.title_input)
        
        self.composer_input = QLineEdit()
        self.composer_input.setPlaceholderText("Composer name...")
        self.composer_input.textChanged.connect(self._on_composer_changed)
        metadata_layout.addRow("Composer:", self.composer_input)
        
        layout.addWidget(metadata_group)
        
        # Score info group (read-only)
        info_group = QGroupBox("Score Information")
        info_layout = QFormLayout(info_group)
        
        self.parts_label = QLabel("—")
        info_layout.addRow("Parts:", self.parts_label)
        
        self.measures_label = QLabel("—")
        info_layout.addRow("Measures:", self.measures_label)
        
        self.key_label = QLabel("—")
        info_layout.addRow("Key:", self.key_label)
        
        self.time_sig_label = QLabel("—")
        info_layout.addRow("Time Sig:", self.time_sig_label)
        
        self.tempo_label = QLabel("—")
        info_layout.addRow("Tempo:", self.tempo_label)
        
        self.duration_label = QLabel("—")
        info_layout.addRow("Duration:", self.duration_label)
        
        layout.addWidget(info_group)
        
        # Tempo adjustment
        tempo_group = QGroupBox("Tempo")
        tempo_layout = QHBoxLayout(tempo_group)
        
        self.tempo_spin = QSpinBox()
        self.tempo_spin.setMinimum(20)
        self.tempo_spin.setMaximum(300)
        self.tempo_spin.setValue(120)
        tempo_layout.addWidget(self.tempo_spin)
        
        tempo_layout.addWidget(QLabel("BPM"))
        
        self.apply_tempo_btn = QPushButton("Apply")
        self.apply_tempo_btn.clicked.connect(self._on_apply_tempo)
        tempo_layout.addWidget(self.apply_tempo_btn)
        
        layout.addWidget(tempo_group)
        
        layout.addStretch()
        return widget
    
    def set_score(self, score: Score):
        """
        Set the score to edit.
        
        Args:
            score: Score object to edit
        """
        self._score = score
        self.setEnabled(True)
        self._update_display()
    
    def _update_display(self):
        """Update the display with current score info."""
        if not self._score:
            return
        
        # Update info labels
        self.parts_label.setText(str(self._score.num_parts))
        self.measures_label.setText(str(self._score.num_measures))
        
        key = self._score.key_signature
        self.key_label.setText(key if key else "—")
        self.current_key_label.setText(key if key else "—")
        
        time_sig = self._score.time_signature
        self.time_sig_label.setText(time_sig if time_sig else "—")
        
        tempo = self._score.tempo_bpm
        if tempo:
            self.tempo_label.setText(f"{tempo} BPM")
            self.tempo_spin.setValue(tempo)
        else:
            self.tempo_label.setText("—")
        
        duration = self._score.get_duration_seconds()
        if duration > 0:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            self.duration_label.setText(f"{minutes}:{seconds:02d}")
        else:
            self.duration_label.setText("—")
        
        # Update metadata fields
        self.title_input.setText(self._score.title or "")
        self.composer_input.setText(self._score.composer or "")
        
        # Update lyric selectors
        self.lyric_part_spin.setMaximum(max(1, self._score.num_parts))
        self.lyric_measure_spin.setMaximum(max(1, self._score.num_measures))
    
    # Event handlers
    
    def _on_transpose_clicked(self):
        """Handle transpose button click."""
        interval = self.interval_combo.currentData()
        if interval and interval != "P1":
            self.transpose_requested.emit(interval)
    
    def _on_octave_shift(self, direction: int):
        """Handle octave shift button click."""
        self.octave_shift_requested.emit(direction)
    
    def _on_octave_apply(self):
        """Handle octave apply button click."""
        octaves = self.octave_spin.value()
        if octaves != 0:
            self.octave_shift_requested.emit(octaves)
            self.octave_spin.setValue(0)
    
    def _on_key_change_clicked(self):
        """Handle key change button click."""
        new_key = self.key_combo.currentText()
        self.key_change_requested.emit(new_key)
    
    def _on_apply_lyric(self):
        """Handle apply lyric button click."""
        if not self._score:
            return
        
        part = self.lyric_part_spin.value() - 1  # 0-indexed
        measure = self.lyric_measure_spin.value()
        beat = float(self.lyric_beat_spin.value())
        text = self.lyric_input.text()
        
        success = self._score.add_lyric_to_note(part, measure, beat, text)
        if success:
            self.lyric_changed.emit(part, measure, beat, text)
    
    def _on_apply_bulk_lyrics(self):
        """Handle bulk lyrics application."""
        if not self._score:
            return
        
        text = self.bulk_lyrics_text.toPlainText()
        words = text.split()
        
        if not words:
            return
        
        # Apply to notes in order
        word_index = 0
        for note_info in self._score.iter_notes():
            if note_info.is_rest:
                continue
            
            if word_index >= len(words):
                break
            
            self._score.add_lyric_to_note(
                note_info.part_index,
                note_info.measure_number,
                note_info.beat,
                words[word_index]
            )
            word_index += 1
        
        self.lyric_changed.emit(-1, -1, 0, "bulk")
    
    def _on_clear_lyrics(self):
        """Handle clear all lyrics."""
        if not self._score:
            return
        
        for note_info in self._score.iter_notes():
            if note_info.lyric:
                self._score.add_lyric_to_note(
                    note_info.part_index,
                    note_info.measure_number,
                    note_info.beat,
                    ""
                )
        
        self.lyric_changed.emit(-1, -1, 0, "clear")
    
    def _on_title_changed(self, text: str):
        """Handle title change."""
        if self._score and text != self._score.title:
            self._score.title = text
            self.metadata_changed.emit()
    
    def _on_composer_changed(self, text: str):
        """Handle composer change."""
        if self._score and text != self._score.composer:
            self._score.composer = text
            self.metadata_changed.emit()
    
    def _on_apply_tempo(self):
        """Handle tempo change."""
        if self._score:
            tempo = self.tempo_spin.value()
            self._score.tempo_bpm = tempo
            self.tempo_label.setText(f"{tempo} BPM")
            self.metadata_changed.emit()
