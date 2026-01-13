"""
Command Parser - Parse text commands into musical notation.

Provides a simple, user-friendly syntax for entering notes, lyrics, and 
musical elements via text commands. Inspired by gabc notation but simplified
for modern users.

Syntax Examples:
    C4 q "Al-"          # C4 quarter note with lyric "Al-"
    D4 h                # D4 half note
    E4 w "le-"          # E4 whole note with lyric
    r q                 # Quarter rest
    C4 E4 G4 q "lu"     # C major chord, quarter duration
    C4-E4 q             # Tied notes
    [C4 D4 E4] q        # Slurred notes
    
Duration codes:
    w = whole, h = half, q = quarter, e = eighth, s = sixteenth
    . = dotted (e.g., q. = dotted quarter)
    
Pitch format:
    Note + Accidental (optional) + Octave
    C4, D#5, Bb3, F##4, Ebb2
    
Special commands:
    key: C major        # Set key signature
    time: 4/4           # Set time signature  
    tempo: 120          # Set tempo in BPM
    clef: treble        # Set clef (treble, bass, alto, tenor)
    measure             # Insert barline
    |                   # Shorthand for barline
    ||                  # Double barline
    |||                 # End barline
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


class Duration(Enum):
    """Note duration types."""
    WHOLE = "w"
    HALF = "h"
    QUARTER = "q"
    EIGHTH = "e"
    SIXTEENTH = "s"
    THIRTYSECOND = "t"
    
    @classmethod
    def from_code(cls, code: str) -> Optional["Duration"]:
        """Get duration from code letter."""
        code = code.lower().rstrip(".")
        for d in cls:
            if d.value == code:
                return d
        return None
    
    def to_music21_type(self) -> str:
        """Convert to music21 duration type."""
        mapping = {
            Duration.WHOLE: "whole",
            Duration.HALF: "half",
            Duration.QUARTER: "quarter",
            Duration.EIGHTH: "eighth",
            Duration.SIXTEENTH: "16th",
            Duration.THIRTYSECOND: "32nd",
        }
        return mapping.get(self, "quarter")


@dataclass
class ParsedNote:
    """Represents a parsed note."""
    pitch: str  # e.g., "C4", "D#5"
    duration: Duration = Duration.QUARTER
    dotted: bool = False
    lyric: Optional[str] = None
    tied: bool = False
    slurred: bool = False
    
    @property
    def pitch_name(self) -> str:
        """Get just the pitch name without octave (e.g., 'C#')."""
        match = re.match(r"([A-Ga-g][#b]*)", self.pitch)
        return match.group(1) if match else self.pitch
    
    @property
    def octave(self) -> int:
        """Get the octave number."""
        match = re.search(r"(\d+)$", self.pitch)
        return int(match.group(1)) if match else 4


@dataclass
class ParsedRest:
    """Represents a parsed rest."""
    duration: Duration = Duration.QUARTER
    dotted: bool = False


@dataclass
class ParsedChord:
    """Represents a parsed chord (multiple simultaneous notes)."""
    notes: list[ParsedNote] = field(default_factory=list)
    duration: Duration = Duration.QUARTER
    dotted: bool = False
    lyric: Optional[str] = None


@dataclass
class ParsedBarline:
    """Represents a barline."""
    style: str = "single"  # single, double, final


@dataclass
class ParsedCommand:
    """Represents a special command."""
    command: str  # key, time, tempo, clef
    value: str


# Type alias for parsed elements
ParsedElement = Union[ParsedNote, ParsedRest, ParsedChord, ParsedBarline, ParsedCommand]


class CommandParseError(Exception):
    """Error during command parsing."""
    def __init__(self, message: str, position: int = 0, line: int = 1):
        super().__init__(message)
        self.position = position
        self.line = line


class CommandParser:
    """
    Parser for text-based music notation commands.
    
    Converts user-friendly text commands into structured musical elements
    that can be added to a Score.
    """
    
    # Regex patterns
    PITCH_PATTERN = re.compile(
        r"^([A-Ga-g])([#b]{0,2})(\d)$"
    )
    DURATION_PATTERN = re.compile(
        r"^([whqest])(\.?)$", re.IGNORECASE
    )
    LYRIC_PATTERN = re.compile(
        r'"([^"]*)"'
    )
    COMMAND_PATTERN = re.compile(
        r"^(key|time|tempo|clef):\s*(.+)$", re.IGNORECASE
    )
    BARLINE_PATTERNS = {
        "|||": "final",
        "||": "double", 
        "|": "single",
        "measure": "single",
    }
    
    def __init__(self):
        self.errors: list[CommandParseError] = []
    
    def parse(self, text: str) -> list[ParsedElement]:
        """
        Parse a string of commands into musical elements.
        
        Args:
            text: Input text containing music commands
            
        Returns:
            List of parsed musical elements
            
        Raises:
            CommandParseError: If parsing fails
        """
        self.errors = []
        elements: list[ParsedElement] = []
        
        # Split into lines for multi-line input
        lines = text.strip().split("\n")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                # Skip empty lines and comments
                continue
            
            try:
                line_elements = self._parse_line(line, line_num)
                elements.extend(line_elements)
            except CommandParseError as e:
                e.line = line_num
                self.errors.append(e)
        
        return elements
    
    def _parse_line(self, line: str, line_num: int) -> list[ParsedElement]:
        """Parse a single line of input."""
        elements: list[ParsedElement] = []
        
        # Check for special commands first
        cmd_match = self.COMMAND_PATTERN.match(line)
        if cmd_match:
            return [ParsedCommand(
                command=cmd_match.group(1).lower(),
                value=cmd_match.group(2).strip()
            )]
        
        # Check for barlines
        for pattern, style in self.BARLINE_PATTERNS.items():
            if line == pattern:
                return [ParsedBarline(style=style)]
        
        # Tokenize the line
        tokens = self._tokenize(line)
        
        # Parse tokens into elements
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            # Check for rest
            if token.lower() == "r":
                duration, dotted = self._parse_duration_token(
                    tokens[i + 1] if i + 1 < len(tokens) else "q"
                )
                if duration:
                    elements.append(ParsedRest(duration=duration, dotted=dotted))
                    i += 2
                else:
                    elements.append(ParsedRest())
                    i += 1
                continue
            
            # Check for chord notation [C4 E4 G4]
            if token.startswith("["):
                chord, consumed = self._parse_chord(tokens[i:])
                if chord:
                    elements.append(chord)
                    i += consumed
                    continue
            
            # Check for barline in mixed content
            if token in self.BARLINE_PATTERNS:
                elements.append(ParsedBarline(style=self.BARLINE_PATTERNS[token]))
                i += 1
                continue
            
            # Try to parse as a note
            if self._is_pitch(token):
                note, consumed = self._parse_note(tokens[i:])
                if note:
                    elements.append(note)
                    i += consumed
                    continue
            
            # Unknown token - skip with warning
            logger.warning(f"Unknown token: {token}")
            i += 1
        
        return elements
    
    def _tokenize(self, line: str) -> list[str]:
        """
        Split a line into tokens while preserving quoted strings.
        """
        tokens = []
        current = ""
        in_quotes = False
        in_brackets = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
                current += char
            elif char == "[":
                in_brackets = True
                if current.strip():
                    tokens.append(current.strip())
                current = char
            elif char == "]":
                in_brackets = False
                current += char
                tokens.append(current.strip())
                current = ""
            elif char.isspace() and not in_quotes and not in_brackets:
                if current.strip():
                    tokens.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            tokens.append(current.strip())
        
        return tokens
    
    def _is_pitch(self, token: str) -> bool:
        """Check if a token looks like a pitch."""
        return bool(self.PITCH_PATTERN.match(token))
    
    def _parse_duration_token(self, token: str) -> tuple[Optional[Duration], bool]:
        """Parse a duration token, returns (duration, is_dotted)."""
        match = self.DURATION_PATTERN.match(token)
        if match:
            duration = Duration.from_code(match.group(1))
            dotted = match.group(2) == "."
            return duration, dotted
        return None, False
    
    def _parse_note(self, tokens: list[str]) -> tuple[Optional[ParsedNote], int]:
        """
        Parse a note from tokens.
        
        Returns:
            Tuple of (ParsedNote or None, number of tokens consumed)
        """
        if not tokens:
            return None, 0
        
        pitch = tokens[0]
        if not self._is_pitch(pitch):
            return None, 0
        
        consumed = 1
        duration = Duration.QUARTER
        dotted = False
        lyric = None
        tied = False
        
        # Check for tied note (hyphen suffix)
        if pitch.endswith("-"):
            tied = True
            pitch = pitch[:-1]
        
        # Look for duration and lyric in following tokens
        if consumed < len(tokens):
            next_token = tokens[consumed]
            dur, dot = self._parse_duration_token(next_token)
            if dur:
                duration = dur
                dotted = dot
                consumed += 1
        
        if consumed < len(tokens):
            lyric_match = self.LYRIC_PATTERN.match(tokens[consumed])
            if lyric_match:
                lyric = lyric_match.group(1)
                consumed += 1
        
        return ParsedNote(
            pitch=pitch.upper(),
            duration=duration,
            dotted=dotted,
            lyric=lyric,
            tied=tied,
        ), consumed
    
    def _parse_chord(self, tokens: list[str]) -> tuple[Optional[ParsedChord], int]:
        """
        Parse a chord notation like [C4 E4 G4] q "lyric".
        
        Returns:
            Tuple of (ParsedChord or None, number of tokens consumed)
        """
        if not tokens or not tokens[0].startswith("["):
            return None, 0
        
        # Find the chord content
        chord_token = tokens[0]
        if not chord_token.endswith("]"):
            # Chord spans multiple tokens - find closing bracket
            for i, t in enumerate(tokens[1:], 1):
                chord_token += " " + t
                if t.endswith("]"):
                    break
        
        # Extract pitches from chord
        content = chord_token[1:-1].strip()  # Remove brackets
        pitch_strings = content.split()
        
        notes = []
        for p in pitch_strings:
            if self._is_pitch(p):
                notes.append(ParsedNote(pitch=p.upper()))
        
        if not notes:
            return None, 0
        
        consumed = 1
        duration = Duration.QUARTER
        dotted = False
        lyric = None
        
        # Look for duration
        if consumed < len(tokens):
            dur, dot = self._parse_duration_token(tokens[consumed])
            if dur:
                duration = dur
                dotted = dot
                consumed += 1
        
        # Look for lyric
        if consumed < len(tokens):
            lyric_match = self.LYRIC_PATTERN.match(tokens[consumed])
            if lyric_match:
                lyric = lyric_match.group(1)
                consumed += 1
        
        return ParsedChord(
            notes=notes,
            duration=duration,
            dotted=dotted,
            lyric=lyric,
        ), consumed
    
    def validate(self, text: str) -> list[CommandParseError]:
        """
        Validate input without fully parsing.
        
        Returns:
            List of validation errors
        """
        self.parse(text)
        return self.errors


def format_help() -> str:
    """Return help text for the command syntax."""
    return """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         MUSIC COMMAND SYNTAX GUIDE                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

NOTES
─────
Format: PITCH DURATION "LYRIC"

  Pitch:    C4, D#5, Bb3, F##4 (note + accidental + octave)
  Duration: w=whole, h=half, q=quarter, e=eighth, s=sixteenth
            Add . for dotted (e.g., q. = dotted quarter)
  Lyric:    "text" in quotes, use hyphen for syllables: "Al-" "le-" "lu-" "ia"

Examples:
  C4 q              # C4 quarter note
  D#5 h.            # D#5 dotted half note  
  E4 q "Al-"        # E4 quarter with lyric syllable
  F4 w "le-"        # F4 whole note with lyric

RESTS
─────
Format: r DURATION

Examples:
  r q               # Quarter rest
  r h.              # Dotted half rest

CHORDS
──────
Format: [PITCH PITCH ...] DURATION "LYRIC"

Examples:
  [C4 E4 G4] q      # C major chord, quarter
  [D4 F#4 A4] h "la"# D major chord with lyric

BARLINES
────────
  |                 # Single barline
  ||                # Double barline
  |||               # Final barline
  measure           # Same as single barline

SPECIAL COMMANDS
────────────────
  key: C major      # Set key signature (C major, G major, D minor, etc.)
  time: 4/4         # Set time signature
  tempo: 120        # Set tempo in BPM
  clef: treble      # Set clef (treble, bass, alto, tenor)

FULL EXAMPLE
────────────
  key: G major
  time: 4/4
  tempo: 100
  
  G4 q "A-"
  B4 q "ma-"
  D5 h "zing"
  |
  D5 q "Grace"
  r q
  B4 q "how"
  G4 q "sweet"
  ||
"""
