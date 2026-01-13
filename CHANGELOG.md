# Changelog

All notable changes to ScoreForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-13

### Added
- **Project renamed to ScoreForge**
- MIDI playback with pygame integration
- Dark mode with full theme support (system/light/dark)
- Theme toggle keyboard shortcut (Ctrl+Shift+D)
- Support Developer link (Buy Me a Coffee) in Help menu
- Comprehensive documentation
  - User Guide
  - Command Reference
  - Architecture Guide
  - Contributing Guidelines
  - Testing Guide
- Keyboard Shortcuts dialog
- GitHub repository at https://github.com/TimKenobi/ScoreForge

### Changed
- Improved About dialog with version info and links
- Updated all branding to ScoreForge
- Fixed font family references for cross-platform compatibility

### Fixed
- Qt font warning for "Monospace" family on macOS
- Pygame welcome banner now suppressed

## [0.2.0] - 2024-XX-XX

### Added
- Command-based music input system
  - Text commands for notes, rests, chords
  - Key signature, time signature, tempo commands
  - Lyrics support with syllable alignment
  - Barlines (single, double, final, repeats)
- Syntax highlighting in command input panel
- Interactive drag-and-drop note editor
- Real-time score rendering updates
- Command parser with comprehensive grammar support
- Command executor converting text to music21 Score

### Changed
- Main window now has three-panel layout
- Score view integrated with interactive editing

### Fixed
- Qt WebEngine import made optional with fallback

## [0.1.0] - 2024-XX-XX

### Added
- Initial release
- Optical Music Recognition (OMR) with oemer integration
- Alternative OMR with Audiveris adapter
- Score model wrapping music21
- Music operations
  - Transposition by semitones
  - Key signature changes
  - Octave shifting
- MIDI export
- MusicXML export (compressed and uncompressed)
- PDF export via LilyPond/Abjad
- PySide6 GUI with:
  - Main application window
  - Score view with Verovio SVG rendering
  - Editor panel for transposition and editing
  - Import dialogs for images and files
  - Export dialogs for all formats
- Configuration system with JSON persistence
- Image preprocessing utilities

### Technical
- Python 3.10+ required
- music21 for music representation
- PySide6 for cross-platform GUI
- Verovio for notation rendering
- Comprehensive test suite

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.2.0 | TBD | Command input, interactive editing |
| 0.1.0 | TBD | Initial release, OMR, basic editing |

## Upgrade Notes

### 0.1.x → 0.2.x

No breaking changes. New features are additive.

### Future Plans

See the [Roadmap](README.md#-roadmap) for planned features.
