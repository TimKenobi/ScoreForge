"""
MIDI Playback Module - Real-time MIDI playback with transport controls.

Provides audio playback of Score objects using pygame or FluidSynth.
"""

from __future__ import annotations

import tempfile
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """Playback state enumeration."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class PlaybackPosition:
    """Current playback position."""
    current_time: float  # seconds
    total_time: float  # seconds
    current_measure: int
    total_measures: int
    current_beat: float
    tempo: int
    
    @property
    def progress(self) -> float:
        """Progress as 0.0-1.0."""
        if self.total_time <= 0:
            return 0.0
        return min(1.0, self.current_time / self.total_time)
    
    @property
    def time_str(self) -> str:
        """Format as MM:SS / MM:SS."""
        def fmt(t):
            mins = int(t // 60)
            secs = int(t % 60)
            return f"{mins}:{secs:02d}"
        return f"{fmt(self.current_time)} / {fmt(self.total_time)}"


class MidiPlayerBackend:
    """Abstract backend for MIDI playback."""
    
    def load(self, midi_path: Path) -> bool:
        """Load a MIDI file. Return True on success."""
        raise NotImplementedError
    
    def play(self) -> None:
        """Start or resume playback."""
        raise NotImplementedError
    
    def pause(self) -> None:
        """Pause playback."""
        raise NotImplementedError
    
    def stop(self) -> None:
        """Stop playback and reset position."""
        raise NotImplementedError
    
    def seek(self, position: float) -> None:
        """Seek to position (0.0 to 1.0)."""
        raise NotImplementedError
    
    def set_tempo(self, multiplier: float) -> None:
        """Set tempo multiplier (0.5 = half speed, 2.0 = double)."""
        raise NotImplementedError
    
    def get_position(self) -> float:
        """Get current position in seconds."""
        raise NotImplementedError
    
    def get_duration(self) -> float:
        """Get total duration in seconds."""
        raise NotImplementedError
    
    def is_playing(self) -> bool:
        """Check if currently playing."""
        raise NotImplementedError
    
    def cleanup(self) -> None:
        """Release resources."""
        pass


class PygameMidiBackend(MidiPlayerBackend):
    """MIDI playback using pygame.mixer.music."""
    
    def __init__(self):
        self._initialized = False
        self._playing = False
        self._paused = False
        self._duration = 0.0
        self._start_time = 0.0
        self._pause_time = 0.0
        self._position_offset = 0.0
        
        try:
            import os
            os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            self._pygame = pygame
            self._initialized = True
            logger.info("Pygame MIDI backend initialized")
        except ImportError:
            logger.warning("pygame not available for MIDI playback")
        except Exception as e:
            logger.warning(f"Failed to initialize pygame: {e}")
    
    @property
    def available(self) -> bool:
        return self._initialized
    
    def load(self, midi_path: Path) -> bool:
        if not self._initialized:
            return False
        try:
            self._pygame.mixer.music.load(str(midi_path))
            # Estimate duration (pygame doesn't provide this directly)
            # We'll update this from the score metadata
            self._duration = self._estimate_duration(midi_path)
            self._position_offset = 0.0
            return True
        except Exception as e:
            logger.error(f"Failed to load MIDI: {e}")
            return False
    
    def _estimate_duration(self, midi_path: Path) -> float:
        """Estimate MIDI duration using midiutil or music21."""
        try:
            from music21 import converter
            score = converter.parse(str(midi_path))
            return float(score.duration.quarterLength) * 0.5  # Rough estimate
        except Exception:
            return 180.0  # Default 3 minutes
    
    def play(self) -> None:
        if not self._initialized:
            return
        if self._paused:
            self._pygame.mixer.music.unpause()
            self._start_time = time.time() - self._pause_time
            self._paused = False
        else:
            self._pygame.mixer.music.play()
            self._start_time = time.time()
        self._playing = True
    
    def pause(self) -> None:
        if not self._initialized or not self._playing:
            return
        self._pygame.mixer.music.pause()
        self._pause_time = time.time() - self._start_time
        self._paused = True
    
    def stop(self) -> None:
        if not self._initialized:
            return
        self._pygame.mixer.music.stop()
        self._playing = False
        self._paused = False
        self._position_offset = 0.0
    
    def seek(self, position: float) -> None:
        if not self._initialized:
            return
        # pygame doesn't support seeking well, so we restart
        target_time = position * self._duration
        self._position_offset = target_time
        was_playing = self._playing and not self._paused
        self.stop()
        # Note: pygame.mixer.music doesn't support seeking
        # We'll need to use a different approach or accept this limitation
        if was_playing:
            self.play()
    
    def set_tempo(self, multiplier: float) -> None:
        # pygame doesn't support tempo changes
        pass
    
    def get_position(self) -> float:
        if not self._initialized or not self._playing:
            return 0.0
        if self._paused:
            return self._pause_time
        return time.time() - self._start_time + self._position_offset
    
    def get_duration(self) -> float:
        return self._duration
    
    def set_duration(self, duration: float) -> None:
        """Set duration from score metadata."""
        self._duration = duration
    
    def is_playing(self) -> bool:
        if not self._initialized:
            return False
        return self._playing and not self._paused
    
    def cleanup(self) -> None:
        if self._initialized:
            try:
                self._pygame.mixer.music.stop()
                self._pygame.mixer.quit()
            except Exception:
                pass


class MidiPlayer:
    """
    High-level MIDI player with transport controls.
    
    Features:
    - Play/pause/stop controls
    - Position tracking
    - Tempo adjustment
    - Callback for position updates
    """
    
    def __init__(self):
        self._backend: Optional[MidiPlayerBackend] = None
        self._state = PlaybackState.STOPPED
        self._tempo_multiplier = 1.0
        self._current_midi_path: Optional[Path] = None
        self._score_measures = 0
        self._score_tempo = 120
        
        # Position update callback
        self._position_callback: Optional[Callable[[PlaybackPosition], None]] = None
        self._update_thread: Optional[threading.Thread] = None
        self._stop_updates = threading.Event()
        
        # Initialize backend
        self._init_backend()
    
    def _init_backend(self) -> None:
        """Initialize the best available backend."""
        # Try pygame first
        backend = PygameMidiBackend()
        if backend.available:
            self._backend = backend
            logger.info("Using pygame MIDI backend")
            return
        
        logger.warning("No MIDI playback backend available")
    
    @property
    def available(self) -> bool:
        """Check if playback is available."""
        return self._backend is not None and self._backend.available
    
    @property
    def state(self) -> PlaybackState:
        """Current playback state."""
        return self._state
    
    @property
    def is_playing(self) -> bool:
        return self._state == PlaybackState.PLAYING
    
    @property
    def is_paused(self) -> bool:
        return self._state == PlaybackState.PAUSED
    
    def set_position_callback(self, callback: Callable[[PlaybackPosition], None]) -> None:
        """Set callback for position updates (called ~10 times per second)."""
        self._position_callback = callback
    
    def load_score(self, score) -> bool:
        """
        Load a Score object for playback.
        
        Args:
            score: Score object to play
            
        Returns:
            True if loading succeeded
        """
        if not self.available:
            return False
        
        try:
            # Export score to temporary MIDI file
            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
                temp_path = Path(f.name)
            
            # Export using music21
            score._score.write('midi', fp=str(temp_path))
            
            # Get score metadata
            self._score_measures = score.num_measures
            if score._score.metronomeMarkBoundaries():
                mm = score._score.metronomeMarkBoundaries()[0][2]
                self._score_tempo = int(mm.number) if mm else 120
            else:
                self._score_tempo = 120
            
            # Calculate duration
            duration = float(score._score.duration.quarterLength) * (60.0 / self._score_tempo)
            
            # Load into backend
            if self._backend.load(temp_path):
                self._current_midi_path = temp_path
                if hasattr(self._backend, 'set_duration'):
                    self._backend.set_duration(duration)
                return True
            
            return False
            
        except Exception as e:
            logger.exception(f"Failed to load score for playback: {e}")
            return False
    
    def play(self) -> None:
        """Start or resume playback."""
        if not self.available or not self._current_midi_path:
            return
        
        self._backend.play()
        self._state = PlaybackState.PLAYING
        self._start_position_updates()
    
    def pause(self) -> None:
        """Pause playback."""
        if not self.available:
            return
        
        self._backend.pause()
        self._state = PlaybackState.PAUSED
    
    def stop(self) -> None:
        """Stop playback and reset to beginning."""
        if not self.available:
            return
        
        self._stop_position_updates()
        self._backend.stop()
        self._state = PlaybackState.STOPPED
        
        # Send final position update
        if self._position_callback:
            self._position_callback(self.get_position())
    
    def toggle_play_pause(self) -> None:
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()
    
    def seek(self, position: float) -> None:
        """
        Seek to position.
        
        Args:
            position: Position from 0.0 to 1.0
        """
        if self.available:
            self._backend.seek(max(0.0, min(1.0, position)))
    
    def set_tempo(self, multiplier: float) -> None:
        """
        Set tempo multiplier.
        
        Args:
            multiplier: 0.5 = half speed, 1.0 = normal, 2.0 = double
        """
        self._tempo_multiplier = max(0.25, min(4.0, multiplier))
        if self.available:
            self._backend.set_tempo(self._tempo_multiplier)
    
    def get_position(self) -> PlaybackPosition:
        """Get current playback position."""
        if not self.available:
            return PlaybackPosition(
                current_time=0.0,
                total_time=0.0,
                current_measure=0,
                total_measures=0,
                current_beat=0.0,
                tempo=120
            )
        
        current = self._backend.get_position()
        total = self._backend.get_duration()
        
        # Calculate measure/beat from time
        beats_per_measure = 4  # Assume 4/4 for now
        beat_duration = 60.0 / self._score_tempo
        current_beat_total = current / beat_duration
        current_measure = int(current_beat_total / beats_per_measure)
        current_beat = current_beat_total % beats_per_measure
        
        return PlaybackPosition(
            current_time=current,
            total_time=total,
            current_measure=current_measure,
            total_measures=self._score_measures,
            current_beat=current_beat,
            tempo=int(self._score_tempo * self._tempo_multiplier)
        )
    
    def _start_position_updates(self) -> None:
        """Start position update thread."""
        self._stop_updates.clear()
        
        def update_loop():
            while not self._stop_updates.is_set():
                if self._position_callback and self._state == PlaybackState.PLAYING:
                    try:
                        pos = self.get_position()
                        self._position_callback(pos)
                        
                        # Check if playback finished
                        if pos.progress >= 0.99:
                            self._state = PlaybackState.STOPPED
                            self._stop_updates.set()
                    except Exception as e:
                        logger.debug(f"Position update error: {e}")
                
                time.sleep(0.1)  # 10 updates per second
        
        self._update_thread = threading.Thread(target=update_loop, daemon=True)
        self._update_thread.start()
    
    def _stop_position_updates(self) -> None:
        """Stop position update thread."""
        self._stop_updates.set()
        if self._update_thread:
            self._update_thread.join(timeout=0.5)
            self._update_thread = None
    
    def cleanup(self) -> None:
        """Release resources."""
        self.stop()
        if self._backend:
            self._backend.cleanup()
        
        # Clean up temp file
        if self._current_midi_path and self._current_midi_path.exists():
            try:
                self._current_midi_path.unlink()
            except Exception:
                pass


# Singleton instance
_player: Optional[MidiPlayer] = None


def get_midi_player() -> MidiPlayer:
    """Get the global MIDI player instance."""
    global _player
    if _player is None:
        _player = MidiPlayer()
    return _player
