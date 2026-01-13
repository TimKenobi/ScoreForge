"""
OMR (Optical Music Recognition) module.

Provides adapters for different OMR engines to convert
sheet music images into digital notation.
"""

from sheet_music_scanner.omr.processor import OMRProcessor
from sheet_music_scanner.omr.oemer_adapter import OemerAdapter

__all__ = ["OMRProcessor", "OemerAdapter"]
