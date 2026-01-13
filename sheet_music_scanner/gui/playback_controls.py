"""
Playback Controls Widget - Transport controls for MIDI playback.

Provides play/pause/stop buttons, position slider, tempo control,
and time display.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSlider,
    QLabel, QSpinBox, QFrame, QToolButton, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QFont

from sheet_music_scanner.core.midi_player import (
    get_midi_player, PlaybackState, PlaybackPosition
)


class PlaybackControls(QWidget):
    """
    Transport controls for MIDI playback.
    
    Features:
    - Play/Pause/Stop buttons
    - Position slider with time display
    - Tempo control (50% - 200%)
    - Current measure display
    """
    
    # Signals
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    position_changed = Signal(float)  # 0.0 to 1.0
    tempo_changed = Signal(int)  # BPM
    measure_changed = Signal(int)  # Current measure number
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._player = get_midi_player()
        self._score_loaded = False
        self._updating_slider = False
        
        self._setup_ui()
        self._connect_signals()
        
        # Set up position callback
        self._player.set_position_callback(self._on_position_update)
        
        # Initially disable play controls until a score is loaded
        self._set_controls_enabled(False)
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Main controls row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        # Transport buttons
        transport_layout = QHBoxLayout()
        transport_layout.setSpacing(2)
        
        # Stop button
        self.stop_btn = QToolButton()
        self.stop_btn.setText("⏹")
        self.stop_btn.setToolTip("Stop (Home)")
        self.stop_btn.setFixedSize(36, 36)
        self.stop_btn.clicked.connect(self._on_stop)
        transport_layout.addWidget(self.stop_btn)
        
        # Play/Pause button
        self.play_btn = QToolButton()
        self.play_btn.setText("▶")
        self.play_btn.setToolTip("Play/Pause (Space)")
        self.play_btn.setFixedSize(44, 36)
        self.play_btn.clicked.connect(self._on_play_pause)
        transport_layout.addWidget(self.play_btn)
        
        controls_layout.addLayout(transport_layout)
        
        # Time display
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setFixedWidth(110)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Menlo")  # macOS default monospace
        if not font.exactMatch():
            font = QFont("Consolas")  # Windows fallback
        if not font.exactMatch():
            font.setStyleHint(QFont.StyleHint.Monospace)
        self.time_label.setFont(font)
        controls_layout.addWidget(self.time_label)
        
        # Position slider
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(1000)
        self.position_slider.setValue(0)
        self.position_slider.setToolTip("Seek position")
        self.position_slider.sliderPressed.connect(self._on_slider_pressed)
        self.position_slider.sliderReleased.connect(self._on_slider_released)
        self.position_slider.valueChanged.connect(self._on_slider_changed)
        controls_layout.addWidget(self.position_slider, 1)
        
        # Measure display
        self.measure_label = QLabel("M: 0/0")
        self.measure_label.setFixedWidth(80)
        self.measure_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.measure_label.setToolTip("Current measure / Total measures")
        controls_layout.addWidget(self.measure_label)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        controls_layout.addWidget(sep)
        
        # Tempo control
        tempo_layout = QHBoxLayout()
        tempo_layout.setSpacing(4)
        
        tempo_label = QLabel("Tempo:")
        tempo_layout.addWidget(tempo_label)
        
        self.tempo_spin = QSpinBox()
        self.tempo_spin.setMinimum(25)
        self.tempo_spin.setMaximum(400)
        self.tempo_spin.setValue(100)
        self.tempo_spin.setSuffix("%")
        self.tempo_spin.setToolTip("Playback speed (100% = normal)")
        self.tempo_spin.setFixedWidth(80)
        self.tempo_spin.valueChanged.connect(self._on_tempo_changed)
        tempo_layout.addWidget(self.tempo_spin)
        
        controls_layout.addLayout(tempo_layout)
        
        layout.addLayout(controls_layout)
        
        # Check if playback is available
        if not self._player.available:
            self._show_unavailable_message()
    
    def _show_unavailable_message(self):
        """Show message when playback is unavailable."""
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.position_slider.setEnabled(False)
        self.tempo_spin.setEnabled(False)
        self.time_label.setText("No playback")
        self.time_label.setToolTip(
            "Install pygame for MIDI playback:\npip install pygame"
        )
        self.measure_label.setText("Install pygame")
        self.measure_label.setToolTip("pip install pygame")
    
    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable playback controls."""
        self.play_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.position_slider.setEnabled(enabled)
        # Keep tempo always enabled for viewing
        if not enabled:
            self.time_label.setText("Load a score")
            self.measure_label.setText("--")
    
    def _connect_signals(self):
        """Connect internal signals."""
        pass
    
    def load_score(self, score) -> bool:
        """
        Load a score for playback.
        
        Args:
            score: Score object to load
            
        Returns:
            True if loading succeeded
        """
        if not self._player.available:
            return False
        
        success = self._player.load_score(score)
        self._score_loaded = success
        
        if success:
            self._set_controls_enabled(True)
            pos = self._player.get_position()
            self._update_display(pos)
        else:
            self._set_controls_enabled(False)
        
        return success
    
    def play(self):
        """Start playback."""
        if self._score_loaded:
            self._player.play()
            self._update_button_state()
            self.playback_started.emit()
    
    def pause(self):
        """Pause playback."""
        self._player.pause()
        self._update_button_state()
        self.playback_paused.emit()
    
    def stop(self):
        """Stop playback."""
        self._player.stop()
        self._update_button_state()
        self.playback_stopped.emit()
    
    def toggle_play_pause(self):
        """Toggle play/pause state."""
        if self._player.is_playing:
            self.pause()
        else:
            self.play()
    
    def _on_play_pause(self):
        """Handle play/pause button click."""
        self.toggle_play_pause()
    
    def _on_stop(self):
        """Handle stop button click."""
        self.stop()
    
    def _on_slider_pressed(self):
        """Handle slider press - pause updates."""
        self._updating_slider = True
    
    def _on_slider_released(self):
        """Handle slider release - seek to position."""
        self._updating_slider = False
        position = self.position_slider.value() / 1000.0
        self._player.seek(position)
        self.position_changed.emit(position)
    
    def _on_slider_changed(self, value):
        """Handle slider value change during drag."""
        if self._updating_slider:
            # Update time display during drag
            position = value / 1000.0
            total = self._player.get_position().total_time
            current = position * total
            self._update_time_label(current, total)
    
    def _on_tempo_changed(self, value):
        """Handle tempo spinbox change."""
        multiplier = value / 100.0
        self._player.set_tempo(multiplier)
        self.tempo_changed.emit(int(120 * multiplier))  # Assuming base tempo 120
    
    def _on_position_update(self, position: PlaybackPosition):
        """Handle position update from player (called from thread)."""
        # Must use QTimer to update UI from main thread
        QTimer.singleShot(0, lambda: self._update_display(position))
    
    def _update_display(self, pos: PlaybackPosition):
        """Update all display elements."""
        self._update_time_label(pos.current_time, pos.total_time)
        self._update_measure_label(pos.current_measure, pos.total_measures)
        
        if not self._updating_slider:
            self.position_slider.setValue(int(pos.progress * 1000))
        
        # Check if playback finished
        if pos.progress >= 0.99 and self._player.state == PlaybackState.STOPPED:
            self._update_button_state()
    
    def _update_time_label(self, current: float, total: float):
        """Update time display."""
        def fmt(t):
            mins = int(t // 60)
            secs = int(t % 60)
            return f"{mins}:{secs:02d}"
        self.time_label.setText(f"{fmt(current)} / {fmt(total)}")
    
    def _update_measure_label(self, current: int, total: int):
        """Update measure display."""
        self.measure_label.setText(f"M: {current + 1}/{total}")
        self.measure_changed.emit(current)
    
    def _update_button_state(self):
        """Update button appearance based on state."""
        if self._player.is_playing:
            self.play_btn.setText("⏸")
            self.play_btn.setToolTip("Pause (Space)")
        else:
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play (Space)")
    
    def cleanup(self):
        """Clean up resources."""
        self._player.cleanup()


class PlaybackToolbar(QWidget):
    """
    Compact playback toolbar for embedding in main window.
    
    Provides minimal transport controls in a horizontal bar.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controls = PlaybackControls(self)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.controls)
    
    def load_score(self, score) -> bool:
        return self.controls.load_score(score)
    
    def play(self):
        self.controls.play()
    
    def pause(self):
        self.controls.pause()
    
    def stop(self):
        self.controls.stop()
    
    def toggle_play_pause(self):
        self.controls.toggle_play_pause()
