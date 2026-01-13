"""
Command Executor - Execute parsed commands and add elements to a Score.

Bridges the gap between the CommandParser output and the Score model,
converting ParsedElements into music21 objects.
"""

from __future__ import annotations

from typing import Optional
import logging

from music21 import (
    note, chord, stream, pitch, key, meter, tempo,
    clef, bar, expressions, duration,
)

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.core.command_parser import (
    ParsedElement, ParsedNote, ParsedRest, ParsedChord,
    ParsedBarline, ParsedCommand, Duration,
)

logger = logging.getLogger(__name__)


class CommandExecutor:
    """
    Executes parsed commands and adds elements to a Score.
    
    Provides methods for:
    - Converting parsed elements to music21 objects
    - Adding elements to an existing Score
    - Creating new Scores from commands
    """
    
    # Duration to quarterLength mapping
    DURATION_MAP = {
        Duration.WHOLE: 4.0,
        Duration.HALF: 2.0,
        Duration.QUARTER: 1.0,
        Duration.EIGHTH: 0.5,
        Duration.SIXTEENTH: 0.25,
        Duration.THIRTYSECOND: 0.125,
    }
    
    # Clef name mapping
    CLEF_MAP = {
        "treble": clef.TrebleClef,
        "bass": clef.BassClef,
        "alto": clef.AltoClef,
        "tenor": clef.TenorClef,
        "soprano": clef.SopranoClef,
    }
    
    def __init__(self):
        self._pending_tie: Optional[note.Note] = None
    
    def create_score_from_elements(
        self, 
        elements: list[ParsedElement],
        title: str = "Untitled"
    ) -> Score:
        """
        Create a new Score from a list of parsed elements.
        
        Args:
            elements: List of parsed elements from CommandParser
            title: Title for the new score
            
        Returns:
            New Score containing the elements
        """
        # Create a new music21 stream
        part = stream.Part()
        part.id = "Part 1"
        
        # Add a default treble clef
        part.append(clef.TrebleClef())
        
        # Track current measure
        current_measure = stream.Measure(number=1)
        measure_offset = 0.0
        current_time_sig = meter.TimeSignature("4/4")
        beats_per_measure = 4.0
        
        # Process elements
        for elem in elements:
            if isinstance(elem, ParsedCommand):
                # Handle commands
                m21_elem = self._create_command_element(elem)
                if m21_elem:
                    if isinstance(m21_elem, meter.TimeSignature):
                        current_time_sig = m21_elem
                        beats_per_measure = m21_elem.beatCount * (4.0 / m21_elem.beatDuration.quarterLength)
                    current_measure.append(m21_elem)
            
            elif isinstance(elem, ParsedBarline):
                # End current measure and start new one
                part.append(current_measure)
                current_measure = stream.Measure(number=current_measure.number + 1)
                measure_offset = 0.0
                
                # Add barline style if not single
                if elem.style == "double":
                    part[-1].rightBarline = bar.Barline("double")
                elif elem.style == "final":
                    part[-1].rightBarline = bar.Barline("final")
            
            elif isinstance(elem, (ParsedNote, ParsedRest, ParsedChord)):
                m21_elem = self._create_music_element(elem)
                if m21_elem:
                    # Check if we need to start a new measure
                    elem_duration = m21_elem.duration.quarterLength
                    
                    if measure_offset + elem_duration > beats_per_measure:
                        # Start new measure
                        part.append(current_measure)
                        current_measure = stream.Measure(number=current_measure.number + 1)
                        measure_offset = 0.0
                    
                    current_measure.append(m21_elem)
                    measure_offset += elem_duration
        
        # Add final measure if it has content
        if current_measure.notes or current_measure.getElementsByClass(clef.Clef):
            part.append(current_measure)
        
        # Create the full score
        m21_score = stream.Score()
        m21_score.insert(0, part)
        
        # Wrap in our Score class
        score = Score(m21_score)
        score.title = title
        
        return score
    
    def add_elements_to_score(
        self,
        score: Score,
        elements: list[ParsedElement],
        part_index: int = 0,
        append: bool = True
    ) -> None:
        """
        Add parsed elements to an existing Score.
        
        Args:
            score: Target Score object
            elements: Elements to add
            part_index: Which part to add to (0-indexed)
            append: If True, append to end; if False, replace content
        """
        if not score._score.parts:
            logger.warning("Score has no parts, creating one")
            part = stream.Part()
            score._score.insert(0, part)
        
        if part_index >= len(score._score.parts):
            logger.warning(f"Part index {part_index} out of range, using part 0")
            part_index = 0
        
        target_part = score._score.parts[part_index]
        
        if not append:
            # Clear existing content
            target_part.clear()
        
        # Find the last offset in the part
        if target_part.elements:
            last_offset = max(
                e.offset + e.duration.quarterLength 
                for e in target_part.recurse().notes
            ) if target_part.recurse().notes else 0
        else:
            last_offset = 0
        
        current_offset = last_offset
        
        for elem in elements:
            m21_elem = None
            
            if isinstance(elem, ParsedCommand):
                m21_elem = self._create_command_element(elem)
            elif isinstance(elem, ParsedBarline):
                # Insert barline at current position
                bar_obj = self._create_barline(elem)
                if bar_obj:
                    target_part.insert(current_offset, bar_obj)
                continue
            elif isinstance(elem, (ParsedNote, ParsedRest, ParsedChord)):
                m21_elem = self._create_music_element(elem)
            
            if m21_elem:
                target_part.insert(current_offset, m21_elem)
                current_offset += m21_elem.duration.quarterLength
        
        # Record this as an undoable operation
        score._push_undo_state()
    
    def _create_music_element(
        self, 
        elem: ParsedNote | ParsedRest | ParsedChord
    ) -> Optional[note.GeneralNote]:
        """Create a music21 note, rest, or chord from parsed element."""
        
        if isinstance(elem, ParsedNote):
            return self._create_note(elem)
        elif isinstance(elem, ParsedRest):
            return self._create_rest(elem)
        elif isinstance(elem, ParsedChord):
            return self._create_chord(elem)
        
        return None
    
    def _create_note(self, parsed: ParsedNote) -> note.Note:
        """Create a music21 Note from ParsedNote."""
        # Parse pitch
        p = pitch.Pitch(parsed.pitch)
        
        # Create note
        n = note.Note(p)
        
        # Set duration
        quarter_length = self.DURATION_MAP.get(parsed.duration, 1.0)
        if parsed.dotted:
            quarter_length *= 1.5
        n.duration = duration.Duration(quarter_length)
        
        # Add lyric if present
        if parsed.lyric:
            n.lyric = parsed.lyric
        
        # Handle tie
        if parsed.tied:
            n.tie = expressions.Tie("start")
            self._pending_tie = n
        elif self._pending_tie:
            n.tie = expressions.Tie("stop")
            self._pending_tie = None
        
        return n
    
    def _create_rest(self, parsed: ParsedRest) -> note.Rest:
        """Create a music21 Rest from ParsedRest."""
        r = note.Rest()
        
        quarter_length = self.DURATION_MAP.get(parsed.duration, 1.0)
        if parsed.dotted:
            quarter_length *= 1.5
        r.duration = duration.Duration(quarter_length)
        
        return r
    
    def _create_chord(self, parsed: ParsedChord) -> chord.Chord:
        """Create a music21 Chord from ParsedChord."""
        # Create pitches
        pitches = [pitch.Pitch(n.pitch) for n in parsed.notes]
        
        # Create chord
        c = chord.Chord(pitches)
        
        # Set duration
        quarter_length = self.DURATION_MAP.get(parsed.duration, 1.0)
        if parsed.dotted:
            quarter_length *= 1.5
        c.duration = duration.Duration(quarter_length)
        
        # Add lyric if present
        if parsed.lyric:
            c.lyric = parsed.lyric
        
        return c
    
    def _create_barline(self, parsed: ParsedBarline) -> Optional[bar.Barline]:
        """Create a music21 Barline from ParsedBarline."""
        style_map = {
            "single": "regular",
            "double": "double",
            "final": "final",
        }
        style = style_map.get(parsed.style, "regular")
        return bar.Barline(style)
    
    def _create_command_element(self, parsed: ParsedCommand):
        """Create a music21 element from a command."""
        cmd = parsed.command.lower()
        value = parsed.value.strip()
        
        if cmd == "key":
            return self._parse_key_signature(value)
        elif cmd == "time":
            return self._parse_time_signature(value)
        elif cmd == "tempo":
            return self._parse_tempo(value)
        elif cmd == "clef":
            return self._parse_clef(value)
        
        return None
    
    def _parse_key_signature(self, value: str) -> Optional[key.Key]:
        """Parse a key signature string like 'C major' or 'A minor'."""
        value = value.strip()
        
        # Try to parse common formats
        parts = value.split()
        
        if len(parts) >= 2:
            tonic = parts[0]
            mode = parts[1].lower()
            
            # Handle accidentals
            if len(tonic) > 1:
                if tonic[1] == '#':
                    tonic = tonic[0] + '#'
                elif tonic[1].lower() == 'b':
                    tonic = tonic[0] + '-'
                elif tonic[1] == '-':
                    tonic = tonic[0] + '-'
            
            # Determine mode
            if mode in ('major', 'maj', 'm'):
                mode = 'major'
            elif mode in ('minor', 'min'):
                mode = 'minor'
            
            try:
                return key.Key(tonic, mode)
            except Exception as e:
                logger.warning(f"Could not parse key '{value}': {e}")
        
        # Try direct parsing
        try:
            return key.Key(value)
        except Exception:
            pass
        
        return None
    
    def _parse_time_signature(self, value: str) -> Optional[meter.TimeSignature]:
        """Parse a time signature string like '4/4' or '6/8'."""
        try:
            return meter.TimeSignature(value)
        except Exception as e:
            logger.warning(f"Could not parse time signature '{value}': {e}")
            return None
    
    def _parse_tempo(self, value: str) -> Optional[tempo.MetronomeMark]:
        """Parse a tempo value like '120' or '120 bpm'."""
        try:
            # Extract number
            import re
            match = re.search(r'(\d+)', value)
            if match:
                bpm = int(match.group(1))
                return tempo.MetronomeMark(number=bpm)
        except Exception as e:
            logger.warning(f"Could not parse tempo '{value}': {e}")
        
        return None
    
    def _parse_clef(self, value: str) -> Optional[clef.Clef]:
        """Parse a clef name like 'treble' or 'bass'."""
        value = value.lower().strip()
        
        clef_class = self.CLEF_MAP.get(value)
        if clef_class:
            return clef_class()
        
        logger.warning(f"Unknown clef '{value}'")
        return None


def execute_commands(elements: list[ParsedElement], title: str = "Untitled") -> Score:
    """
    Convenience function to create a Score from parsed elements.
    
    Args:
        elements: List of parsed elements
        title: Score title
        
    Returns:
        New Score object
    """
    executor = CommandExecutor()
    return executor.create_score_from_elements(elements, title)
