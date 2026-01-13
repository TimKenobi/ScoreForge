"""
Music operations module.

Provides high-level functions for common music transformations
that can be applied to Score objects.
"""

from typing import Optional, List, Tuple
from music21 import interval, key, pitch, note

from sheet_music_scanner.core.score import Score


def transpose_score(
    score: Score,
    semitones: Optional[int] = None,
    interval_name: Optional[str] = None
) -> None:
    """
    Transpose a score by a given interval.
    
    Args:
        score: Score to transpose
        semitones: Number of semitones (positive = up, negative = down)
        interval_name: Interval name like "P5", "m3", "-M2"
        
    Note:
        Provide either semitones OR interval_name, not both.
    """
    if semitones is not None:
        score.transpose(semitones)
    elif interval_name is not None:
        score.transpose(interval_name)
    else:
        raise ValueError("Must provide either semitones or interval_name")


def shift_octave(
    score: Score,
    octaves: int,
    part_index: Optional[int] = None
) -> None:
    """
    Shift notes by octave(s).
    
    Args:
        score: Score to modify
        octaves: Number of octaves (positive = up, negative = down)
        part_index: Specific part to shift, or None for all parts
    """
    score.shift_octave(octaves, part_index)


def change_key(score: Score, new_key: str) -> None:
    """
    Change the key of a score (transposes accordingly).
    
    Args:
        score: Score to modify
        new_key: New key like "G major", "D minor", "Bb major"
    """
    score.change_key(new_key)


def add_lyric(
    score: Score,
    part_index: int,
    measure_number: int,
    beat: float,
    text: str,
    syllabic: str = "single"
) -> bool:
    """
    Add a lyric to a specific note.
    
    Args:
        score: Score to modify
        part_index: Part index
        measure_number: Measure number (1-based)
        beat: Beat position
        text: Lyric text
        syllabic: Syllabic type ("single", "begin", "middle", "end")
        
    Returns:
        True if successful
    """
    return score.add_lyric_to_note(
        part_index, measure_number, beat, text, syllabic
    )


def remove_lyric(
    score: Score,
    part_index: int,
    measure_number: int,
    beat: float
) -> bool:
    """
    Remove a lyric from a specific note.
    
    Args:
        score: Score to modify
        part_index: Part index
        measure_number: Measure number
        beat: Beat position
        
    Returns:
        True if successful
    """
    return score.add_lyric_to_note(part_index, measure_number, beat, "")


def get_available_keys() -> List[str]:
    """
    Get list of common key signatures.
    
    Returns:
        List of key names
    """
    return [
        "C major", "G major", "D major", "A major", "E major", "B major",
        "F# major", "Gb major", "Db major", "Ab major", "Eb major", "Bb major", "F major",
        "A minor", "E minor", "B minor", "F# minor", "C# minor", "G# minor",
        "D# minor", "Eb minor", "Bb minor", "F minor", "C minor", "G minor", "D minor",
    ]


def get_interval_options() -> List[Tuple[str, str]]:
    """
    Get list of common transposition intervals.
    
    Returns:
        List of (interval_code, display_name) tuples
    """
    return [
        ("P1", "Unison (no change)"),
        ("m2", "Minor 2nd up"),
        ("-m2", "Minor 2nd down"),
        ("M2", "Major 2nd up"),
        ("-M2", "Major 2nd down"),
        ("m3", "Minor 3rd up"),
        ("-m3", "Minor 3rd down"),
        ("M3", "Major 3rd up"),
        ("-M3", "Major 3rd down"),
        ("P4", "Perfect 4th up"),
        ("-P4", "Perfect 4th down"),
        ("A4", "Tritone up"),
        ("-A4", "Tritone down"),
        ("P5", "Perfect 5th up"),
        ("-P5", "Perfect 5th down"),
        ("m6", "Minor 6th up"),
        ("-m6", "Minor 6th down"),
        ("M6", "Major 6th up"),
        ("-M6", "Major 6th down"),
        ("m7", "Minor 7th up"),
        ("-m7", "Minor 7th down"),
        ("M7", "Major 7th up"),
        ("-M7", "Major 7th down"),
        ("P8", "Octave up"),
        ("-P8", "Octave down"),
    ]


def get_pitch_names() -> List[str]:
    """
    Get list of pitch names for note editing.
    
    Returns:
        List of pitch names like "C", "C#", "D", etc.
    """
    return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def get_octave_range() -> Tuple[int, int]:
    """
    Get valid octave range.
    
    Returns:
        Tuple of (min_octave, max_octave)
    """
    return (0, 9)


def pitch_to_midi(pitch_name: str) -> int:
    """
    Convert pitch name to MIDI number.
    
    Args:
        pitch_name: Pitch like "C4", "F#5"
        
    Returns:
        MIDI note number (0-127)
    """
    p = pitch.Pitch(pitch_name)
    return p.midi


def midi_to_pitch(midi_number: int) -> str:
    """
    Convert MIDI number to pitch name.
    
    Args:
        midi_number: MIDI note number (0-127)
        
    Returns:
        Pitch name like "C4"
    """
    p = pitch.Pitch(midi=midi_number)
    return p.nameWithOctave


def analyze_score_key(score: Score) -> str:
    """
    Analyze the key of a score using music21's analysis.
    
    Args:
        score: Score to analyze
        
    Returns:
        Detected key like "C major" or "A minor"
    """
    return score.analyze_key()


def get_duration_types() -> List[Tuple[str, float]]:
    """
    Get list of common note durations.
    
    Returns:
        List of (duration_name, quarter_length) tuples
    """
    return [
        ("whole", 4.0),
        ("half", 2.0),
        ("quarter", 1.0),
        ("eighth", 0.5),
        ("16th", 0.25),
        ("32nd", 0.125),
        ("dotted whole", 6.0),
        ("dotted half", 3.0),
        ("dotted quarter", 1.5),
        ("dotted eighth", 0.75),
    ]
