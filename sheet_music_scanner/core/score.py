"""
Score model - A wrapper around music21.stream.Score.

Provides a simplified interface for working with musical scores,
including loading, editing, and exporting functionality.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional, List, Iterator, Tuple, Union
from dataclasses import dataclass, field
import tempfile

from music21 import (
    converter,
    stream,
    note,
    chord,
    key,
    meter,
    tempo,
    clef,
    instrument,
    metadata,
    layout,
)
from music21.midi import translate as midi_translate


@dataclass
class NoteInfo:
    """Information about a single note for display/editing."""
    
    part_index: int
    measure_number: int
    beat: float
    pitch: str  # e.g., "C4", "F#5"
    midi_pitch: int
    duration: float  # in quarter notes
    duration_type: str  # "quarter", "half", etc.
    lyric: Optional[str] = None
    is_rest: bool = False
    is_chord: bool = False
    chord_pitches: List[str] = field(default_factory=list)
    
    # Internal reference for editing
    _element_id: Optional[int] = None


@dataclass
class MeasureInfo:
    """Information about a measure."""
    
    number: int
    part_index: int
    time_signature: Optional[str] = None
    key_signature: Optional[str] = None
    notes: List[NoteInfo] = field(default_factory=list)


@dataclass  
class PartInfo:
    """Information about a part/instrument."""
    
    index: int
    name: str
    instrument: Optional[str] = None
    measures: List[MeasureInfo] = field(default_factory=list)


class Score:
    """
    Wrapper around music21 Score object.
    
    Provides simplified interface for:
    - Loading from various formats (MusicXML, MIDI, images via OMR)
    - Editing operations (transpose, octave shift, note correction, lyrics)
    - Exporting to MIDI, MusicXML, PDF
    - Undo/redo functionality
    """
    
    def __init__(self, music21_score: Optional[stream.Score] = None):
        """
        Initialize Score wrapper.
        
        Args:
            music21_score: Optional music21 Score object to wrap
        """
        self._score: stream.Score = music21_score or stream.Score()
        self._source_path: Optional[Path] = None
        self._is_modified: bool = False
        
        # Undo/redo stacks
        self._undo_stack: List[stream.Score] = []
        self._redo_stack: List[stream.Score] = []
        self._max_undo: int = 50
    
    @classmethod
    def from_musicxml(cls, filepath: Union[str, Path]) -> "Score":
        """
        Load a score from a MusicXML file.
        
        Args:
            filepath: Path to MusicXML file (.xml, .musicxml, .mxl)
            
        Returns:
            Score object
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        music21_score = converter.parse(str(filepath))
        
        # Ensure we have a Score object
        if not isinstance(music21_score, stream.Score):
            score_obj = stream.Score()
            score_obj.append(music21_score)
            music21_score = score_obj
        
        score = cls(music21_score)
        score._source_path = filepath
        return score
    
    @classmethod
    def from_midi(cls, filepath: Union[str, Path]) -> "Score":
        """
        Load a score from a MIDI file.
        
        Args:
            filepath: Path to MIDI file (.mid, .midi)
            
        Returns:
            Score object
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        music21_score = converter.parse(str(filepath))
        
        if not isinstance(music21_score, stream.Score):
            score_obj = stream.Score()
            score_obj.append(music21_score)
            music21_score = score_obj
        
        score = cls(music21_score)
        score._source_path = filepath
        return score
    
    @classmethod
    def from_music21(cls, music21_obj: stream.Score) -> "Score":
        """Create Score from existing music21 Score object."""
        return cls(music21_obj)
    
    @property
    def music21_score(self) -> stream.Score:
        """Get the underlying music21 Score object."""
        return self._score
    
    @property
    def is_modified(self) -> bool:
        """Check if score has been modified since last save."""
        return self._is_modified
    
    @property
    def source_path(self) -> Optional[Path]:
        """Get the original file path if loaded from file."""
        return self._source_path
    
    @property
    def title(self) -> Optional[str]:
        """Get the score title."""
        if self._score.metadata and self._score.metadata.title:
            return self._score.metadata.title
        return None
    
    @title.setter
    def title(self, value: str) -> None:
        """Set the score title."""
        if not self._score.metadata:
            self._score.metadata = metadata.Metadata()
        self._score.metadata.title = value
        self._mark_modified()
    
    @property
    def composer(self) -> Optional[str]:
        """Get the composer name."""
        if self._score.metadata and self._score.metadata.composer:
            return self._score.metadata.composer
        return None
    
    @composer.setter
    def composer(self, value: str) -> None:
        """Set the composer name."""
        if not self._score.metadata:
            self._score.metadata = metadata.Metadata()
        self._score.metadata.composer = value
        self._mark_modified()
    
    @property
    def num_parts(self) -> int:
        """Get number of parts/instruments in the score."""
        return len(self._score.parts)
    
    @property
    def num_measures(self) -> int:
        """Get total number of measures (from first part)."""
        if self._score.parts:
            measures = self._score.parts[0].getElementsByClass(stream.Measure)
            return len(measures)
        return 0
    
    @property
    def key_signature(self) -> Optional[str]:
        """Get the key signature of the score."""
        ks = self._score.flatten().getElementsByClass(key.KeySignature)
        if ks:
            return str(ks[0])
        
        k = self._score.flatten().getElementsByClass(key.Key)
        if k:
            return str(k[0])
        
        return None
    
    @property
    def time_signature(self) -> Optional[str]:
        """Get the time signature of the score."""
        ts = self._score.flatten().getElementsByClass(meter.TimeSignature)
        if ts:
            return ts[0].ratioString
        return None
    
    @property
    def tempo_bpm(self) -> Optional[int]:
        """Get the tempo in BPM."""
        tempos = self._score.flatten().getElementsByClass(tempo.MetronomeMark)
        if tempos:
            return int(tempos[0].number)
        return None
    
    @tempo_bpm.setter
    def tempo_bpm(self, bpm: int) -> None:
        """Set the tempo in BPM."""
        self._save_undo_state()
        
        # Remove existing tempo marks
        for t in self._score.flatten().getElementsByClass(tempo.MetronomeMark):
            self._score.remove(t, recurse=True)
        
        # Add new tempo
        mm = tempo.MetronomeMark(number=bpm)
        self._score.insert(0, mm)
        self._mark_modified()
    
    def _save_undo_state(self) -> None:
        """Save current state for undo."""
        self._undo_stack.append(copy.deepcopy(self._score))
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        # Clear redo stack on new action
        self._redo_stack.clear()
    
    def _mark_modified(self) -> None:
        """Mark the score as modified."""
        self._is_modified = True
    
    def undo(self) -> bool:
        """
        Undo the last operation.
        
        Returns:
            True if undo was successful, False if nothing to undo
        """
        if not self._undo_stack:
            return False
        
        # Save current state to redo stack
        self._redo_stack.append(copy.deepcopy(self._score))
        
        # Restore previous state
        self._score = self._undo_stack.pop()
        self._is_modified = True
        return True
    
    def redo(self) -> bool:
        """
        Redo the last undone operation.
        
        Returns:
            True if redo was successful, False if nothing to redo
        """
        if not self._redo_stack:
            return False
        
        # Save current state to undo stack
        self._undo_stack.append(copy.deepcopy(self._score))
        
        # Restore redo state
        self._score = self._redo_stack.pop()
        self._is_modified = True
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    def transpose(self, interval: Union[str, int]) -> None:
        """
        Transpose the entire score.
        
        Args:
            interval: Interval to transpose by. Can be:
                - String like "P5" (perfect fifth up), "m3" (minor third up)
                - String like "-M2" (major second down)
                - Integer for semitones (positive = up, negative = down)
        """
        self._save_undo_state()
        
        if isinstance(interval, int):
            # Transpose by semitones
            self._score = self._score.transpose(interval)
        else:
            # Transpose by interval name
            self._score = self._score.transpose(interval)
        
        self._mark_modified()
    
    def shift_octave(self, direction: int, part_index: Optional[int] = None) -> None:
        """
        Shift notes by octave(s).
        
        Args:
            direction: Number of octaves to shift (positive = up, negative = down)
            part_index: If specified, only shift this part. Otherwise shift all.
        """
        self._save_undo_state()
        
        semitones = direction * 12
        
        if part_index is not None:
            # Shift specific part
            if 0 <= part_index < len(self._score.parts):
                part = self._score.parts[part_index]
                for n in part.recurse().notes:
                    n.transpose(semitones, inPlace=True)
        else:
            # Shift all parts
            self._score = self._score.transpose(semitones)
        
        self._mark_modified()
    
    def change_key(self, new_key: str) -> None:
        """
        Change the key signature of the score (transposes accordingly).
        
        Args:
            new_key: New key like "G major", "D minor", "Bb major"
        """
        self._save_undo_state()
        
        # Analyze current key if not specified
        current_key = self._score.analyze('key')
        new_key_obj = key.Key(new_key)
        
        # Calculate interval between keys
        interval = key.Key.getInterval(current_key, new_key_obj)
        
        # Transpose
        self._score = self._score.transpose(interval)
        
        # Update key signature
        for ks in self._score.flatten().getElementsByClass(key.KeySignature):
            self._score.remove(ks, recurse=True)
        
        self._score.insert(0, new_key_obj)
        self._mark_modified()
    
    def get_parts(self) -> List[PartInfo]:
        """
        Get information about all parts in the score.
        
        Returns:
            List of PartInfo objects
        """
        parts = []
        
        for i, part in enumerate(self._score.parts):
            part_name = part.partName or f"Part {i + 1}"
            
            # Get instrument
            instruments = part.getElementsByClass(instrument.Instrument)
            instr_name = instruments[0].instrumentName if instruments else None
            
            part_info = PartInfo(
                index=i,
                name=part_name,
                instrument=instr_name,
            )
            parts.append(part_info)
        
        return parts
    
    def get_notes_in_measure(
        self, 
        part_index: int, 
        measure_number: int
    ) -> List[NoteInfo]:
        """
        Get all notes in a specific measure.
        
        Args:
            part_index: Index of the part
            measure_number: Measure number (1-based)
            
        Returns:
            List of NoteInfo objects
        """
        notes = []
        
        if part_index >= len(self._score.parts):
            return notes
        
        part = self._score.parts[part_index]
        measure = part.measure(measure_number)
        
        if measure is None:
            return notes
        
        for element in measure.notesAndRests:
            if isinstance(element, note.Rest):
                note_info = NoteInfo(
                    part_index=part_index,
                    measure_number=measure_number,
                    beat=element.beat,
                    pitch="rest",
                    midi_pitch=0,
                    duration=element.quarterLength,
                    duration_type=element.duration.type,
                    is_rest=True,
                    _element_id=id(element),
                )
            elif isinstance(element, chord.Chord):
                pitches = [p.nameWithOctave for p in element.pitches]
                note_info = NoteInfo(
                    part_index=part_index,
                    measure_number=measure_number,
                    beat=element.beat,
                    pitch=pitches[0] if pitches else "",
                    midi_pitch=element.pitches[0].midi if element.pitches else 0,
                    duration=element.quarterLength,
                    duration_type=element.duration.type,
                    lyric=element.lyric if hasattr(element, 'lyric') else None,
                    is_chord=True,
                    chord_pitches=pitches,
                    _element_id=id(element),
                )
            elif isinstance(element, note.Note):
                note_info = NoteInfo(
                    part_index=part_index,
                    measure_number=measure_number,
                    beat=element.beat,
                    pitch=element.nameWithOctave,
                    midi_pitch=element.pitch.midi,
                    duration=element.quarterLength,
                    duration_type=element.duration.type,
                    lyric=element.lyric,
                    _element_id=id(element),
                )
            else:
                continue
            
            notes.append(note_info)
        
        return notes
    
    def iter_notes(self) -> Iterator[NoteInfo]:
        """
        Iterate over all notes in the score.
        
        Yields:
            NoteInfo objects for each note
        """
        for part_index, part in enumerate(self._score.parts):
            for measure in part.getElementsByClass(stream.Measure):
                for note_info in self.get_notes_in_measure(
                    part_index, 
                    measure.measureNumber
                ):
                    yield note_info
    
    def set_note_pitch(
        self,
        part_index: int,
        measure_number: int,
        beat: float,
        new_pitch: str
    ) -> bool:
        """
        Change the pitch of a specific note.
        
        Args:
            part_index: Index of the part
            measure_number: Measure number
            beat: Beat position of the note
            new_pitch: New pitch like "C4", "F#5"
            
        Returns:
            True if successful
        """
        self._save_undo_state()
        
        if part_index >= len(self._score.parts):
            return False
        
        part = self._score.parts[part_index]
        measure = part.measure(measure_number)
        
        if measure is None:
            return False
        
        for element in measure.notes:
            if abs(element.beat - beat) < 0.01:
                if isinstance(element, note.Note):
                    element.pitch = note.Note(new_pitch).pitch
                    self._mark_modified()
                    return True
        
        return False
    
    def add_lyric_to_note(
        self,
        part_index: int,
        measure_number: int,
        beat: float,
        lyric_text: str,
        syllabic: str = "single"
    ) -> bool:
        """
        Add a lyric to a specific note.
        
        Args:
            part_index: Index of the part
            measure_number: Measure number
            beat: Beat position of the note
            lyric_text: Text to add
            syllabic: "single", "begin", "middle", "end"
            
        Returns:
            True if successful
        """
        self._save_undo_state()
        
        if part_index >= len(self._score.parts):
            return False
        
        part = self._score.parts[part_index]
        measure = part.measure(measure_number)
        
        if measure is None:
            return False
        
        for element in measure.notes:
            if abs(element.beat - beat) < 0.01:
                element.lyric = lyric_text
                self._mark_modified()
                return True
        
        return False
    
    def to_musicxml(self, filepath: Union[str, Path]) -> Path:
        """
        Export score to MusicXML format.
        
        Args:
            filepath: Output file path
            
        Returns:
            Path to created file
        """
        filepath = Path(filepath)
        self._score.write('musicxml', fp=str(filepath))
        return filepath
    
    def to_midi(self, filepath: Union[str, Path]) -> Path:
        """
        Export score to MIDI format.
        
        Args:
            filepath: Output file path
            
        Returns:
            Path to created file
        """
        filepath = Path(filepath)
        self._score.write('midi', fp=str(filepath))
        return filepath
    
    def to_musicxml_string(self) -> str:
        """
        Get MusicXML representation as string.
        
        Returns:
            MusicXML string
        """
        from music21.musicxml import m21ToXml
        
        exporter = m21ToXml.GeneralObjectExporter(self._score)
        return exporter.parse().decode('utf-8')
    
    def get_duration_seconds(self) -> float:
        """
        Get the total duration of the score in seconds.
        
        Returns:
            Duration in seconds
        """
        return self._score.seconds or 0.0
    
    def get_duration_quarters(self) -> float:
        """
        Get the total duration in quarter notes.
        
        Returns:
            Duration in quarter notes
        """
        return self._score.quarterLength
    
    def analyze_key(self) -> str:
        """
        Analyze and return the detected key of the score.
        
        Returns:
            Key string like "C major" or "A minor"
        """
        detected_key = self._score.analyze('key')
        return str(detected_key)
    
    def __str__(self) -> str:
        """String representation."""
        title = self.title or "Untitled"
        return f"Score('{title}', {self.num_parts} parts, {self.num_measures} measures)"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"Score(title={self.title!r}, "
            f"parts={self.num_parts}, "
            f"measures={self.num_measures}, "
            f"key={self.key_signature}, "
            f"time={self.time_signature})"
        )
