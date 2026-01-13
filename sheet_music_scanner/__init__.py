"""
ScoreForge - Sheet Music Scanner & Editor

A Python desktop application for scanning sheet music and converting
it to MIDI, MusicXML, and PDF formats with editing capabilities.

Developed by Tim Kenobi
https://github.com/TimKenobi/ScoreForge
"""

__version__ = "1.0.0"
__author__ = "Tim Kenobi"

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.config import Config

__all__ = ["Score", "Config", "__version__"]
