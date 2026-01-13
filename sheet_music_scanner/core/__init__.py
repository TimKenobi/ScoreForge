"""
Core module for Sheet Music Scanner.

Contains the Score model and music operations.
"""

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.core.operations import (
    transpose_score,
    shift_octave,
    change_key,
    add_lyric,
    remove_lyric,
)
from sheet_music_scanner.core.command_parser import (
    CommandParser,
    ParsedNote,
    ParsedRest,
    ParsedChord,
    ParsedBarline,
    ParsedCommand,
    format_help,
)
from sheet_music_scanner.core.command_executor import (
    CommandExecutor,
    execute_commands,
)

__all__ = [
    "Score",
    "transpose_score",
    "shift_octave",
    "change_key",
    "add_lyric",
    "remove_lyric",
    "CommandParser",
    "CommandExecutor",
    "ParsedNote",
    "ParsedRest",
    "ParsedChord",
    "ParsedBarline",
    "ParsedCommand",
    "format_help",
    "execute_commands",
]
