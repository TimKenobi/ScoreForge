# Architecture Guide

This document describes the architecture and design of ScoreForge for developers.

## Overview

ScoreForge follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      GUI (PySide6)                          │ │
│  │  ┌───────────┐  ┌───────────────┐  ┌───────────────────┐   │ │
│  │  │ Command   │  │ Interactive   │  │   Editor Panel    │   │ │
│  │  │  Input    │  │    Editor     │  │                   │   │ │
│  │  └─────┬─────┘  └───────┬───────┘  └─────────┬─────────┘   │ │
│  └────────┼────────────────┼────────────────────┼─────────────┘ │
│           │                │                    │               │
│  ┌────────▼────────────────▼────────────────────▼─────────────┐ │
│  │                    Core Layer                               │ │
│  │  ┌─────────────┐  ┌───────────────┐  ┌──────────────────┐  │ │
│  │  │   Score     │  │  Operations   │  │ Command Parser/  │  │ │
│  │  │   Model     │  │               │  │    Executor      │  │ │
│  │  └──────┬──────┘  └───────┬───────┘  └────────┬─────────┘  │ │
│  └─────────┼─────────────────┼───────────────────┼────────────┘ │
│            │                 │                   │              │
│  ┌─────────▼─────────────────▼───────────────────▼────────────┐ │
│  │                   music21 Library                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────────┐  ┌────────────────────────────────────────┐  │
│  │   OMR Layer    │  │           Export Layer                 │  │
│  │  ┌──────────┐  │  │  ┌──────┐  ┌─────────┐  ┌───────────┐ │  │
│  │  │  oemer   │  │  │  │ MIDI │  │MusicXML │  │    PDF    │ │  │
│  │  │ Audiveris│  │  │  └──────┘  └─────────┘  └───────────┘ │  │
│  │  └──────────┘  │  │                                        │  │
│  └────────────────┘  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### GUI Layer (`gui/`)

The presentation layer using PySide6 (Qt for Python).

**Components:**
- `main_window.py`: Application shell, menus, toolbar
- `command_input.py`: Text-based music entry with syntax highlighting
- `interactive_editor.py`: Visual drag-and-drop score editing
- `score_view.py`: SVG score rendering via Verovio
- `editor_panel.py`: Transposition, key changes, lyrics editing
- `theme.py`: Theme management (dark/light/system)
- `dialogs/`: Modal dialogs for specific operations

**Design Principles:**
- Thin controllers - delegate logic to Core layer
- Signal/slot connections for inter-widget communication
- No direct music21 imports (use Core abstractions)

### Core Layer (`core/`)

Business logic and music processing, independent of GUI.

**Components:**
- `score.py`: Score model wrapping music21.stream.Score
- `operations.py`: Music operations (transpose, key change, octave shift)
- `command_parser.py`: Lexer/parser for text commands
- `command_executor.py`: Converts parsed commands to Score

**Design Principles:**
- Pure Python, no GUI dependencies
- Fully testable with unit tests
- music21 encapsulation for potential future replacement

### OMR Layer (`omr/`)

Optical Music Recognition integration.

**Components:**
- `processor.py`: OMR orchestration and result handling
- `oemer_adapter.py`: Integration with oemer library
- `audiveris_adapter.py`: Integration with Audiveris (external process)

**Design Principles:**
- Adapter pattern for multiple OMR engines
- Async processing to keep GUI responsive
- Confidence scores for recognition quality

### Export Layer (`export/`)

File format exporters.

**Components:**
- `midi_exporter.py`: MIDI file export
- `musicxml_exporter.py`: MusicXML export (compressed/uncompressed)
- `pdf_exporter.py`: PDF via LilyPond/Abjad

**Design Principles:**
- Each exporter is independent
- Graceful degradation when dependencies unavailable
- Configurable output options

### Utils Layer (`utils/`)

Shared utilities.

**Components:**
- `image_processing.py`: Image preprocessing for OMR

---

## Data Flow

### Command Input → Score

```
User types commands
        ↓
CommandInputPanel captures text
        ↓
CommandParser.parse() → List[ParsedElement]
        ↓
CommandExecutor.execute() → music21.stream.Score
        ↓
Score wrapper created
        ↓
InteractiveEditor updated
        ↓
ScoreView renders SVG
```

### OMR → Score

```
User imports image
        ↓
OMRProcessor.process_image()
        ↓
Adapter (oemer/audiveris) runs recognition
        ↓
Raw recognition data returned
        ↓
Converted to music21 Score
        ↓
Score wrapper created
        ↓
GUI displays result
```

### Score → Export

```
User triggers export
        ↓
Exporter receives Score
        ↓
Exporter converts to target format
        ↓
File written to disk
```

---

## Key Classes

### Score (`core/score.py`)

```python
class Score:
    """Wrapper around music21.stream.Score providing a clean API."""
    
    def __init__(self, m21_score: Optional[m21.stream.Score] = None):
        self._score = m21_score or m21.stream.Score()
    
    @property
    def music21_score(self) -> m21.stream.Score:
        """Access underlying music21 score."""
        return self._score
    
    def transpose(self, semitones: int) -> 'Score':
        """Return a new Score transposed by semitones."""
        ...
    
    def set_key(self, key: str) -> None:
        """Set the key signature."""
        ...
    
    def to_musicxml(self) -> str:
        """Export to MusicXML string."""
        ...
```

### CommandParser (`core/command_parser.py`)

```python
class ParsedElement:
    """Base class for parsed music elements."""
    element_type: str

class ParsedNote(ParsedElement):
    pitch: str
    duration: str
    lyric: Optional[str]

class ParsedRest(ParsedElement):
    duration: str

class ParsedChord(ParsedElement):
    pitches: List[str]
    duration: str

class CommandParser:
    """Parses text commands into ParsedElements."""
    
    def parse(self, text: str) -> List[ParsedElement]:
        """Parse multi-line command text."""
        ...
```

### ThemeManager (`gui/theme.py`)

```python
class Theme(Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

class ThemeManager(QObject):
    """Singleton managing application themes."""
    
    theme_changed = Signal(Theme)
    
    @classmethod
    def instance(cls) -> 'ThemeManager':
        """Get singleton instance."""
        ...
    
    def set_theme(self, theme: Theme) -> None:
        """Apply theme to application."""
        ...
    
    def toggle_dark_mode(self) -> None:
        """Toggle between light and dark."""
        ...
```

---

## Design Patterns Used

### Singleton
- `ThemeManager`: Single theme state for entire application
- `Config`: Application configuration

### Adapter
- `OemerAdapter`, `AudiverisAdapter`: Uniform interface for OMR engines

### Factory
- Export factories create appropriate exporter for format

### Observer (Signal/Slot)
- Qt signal/slot for GUI updates
- Theme change notifications

### Command
- Undo/redo system for score edits

### Strategy
- Different OMR strategies for different image types

---

## Configuration

### Config File Location

```python
# macOS
~/Library/Application Support/SheetMusicScanner/config.json

# Windows
%APPDATA%/SheetMusicScanner/config.json

# Linux
~/.config/SheetMusicScanner/config.json
```

### Config Structure

```python
@dataclass
class GUIConfig:
    theme: str = "system"
    window_width: int = 1200
    window_height: int = 800

@dataclass
class OMRConfig:
    engine: str = "oemer"
    confidence_threshold: float = 0.7

@dataclass
class ExportConfig:
    midi_tempo: int = 120
    pdf_quality: str = "high"

@dataclass
class AppConfig:
    gui: GUIConfig
    omr: OMRConfig
    export: ExportConfig
```

---

## Testing Strategy

### Unit Tests

Located in `tests/`:
- `test_score.py`: Core score operations
- `test_operations.py`: Music operations
- `test_command_parser.py`: Command parsing
- `test_command_executor.py`: Command execution
- `test_exporters.py`: Export functionality

### Integration Tests

- End-to-end command input to score
- OMR processing with test images
- Export roundtrips

### GUI Tests

- Widget behavior tests using pytest-qt
- Theme switching tests
- Dialog interaction tests

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=sheet_music_scanner

# Specific module
pytest tests/test_command_parser.py

# Verbose output
pytest -v
```

---

## Extension Points

### Adding a New OMR Engine

1. Create `omr/new_engine_adapter.py`
2. Implement the adapter interface:

```python
class NewEngineAdapter:
    def process(self, image_path: str) -> m21.stream.Score:
        """Process image and return Score."""
        ...
    
    @property
    def is_available(self) -> bool:
        """Check if engine dependencies are installed."""
        ...
```

3. Register in `omr/processor.py`

### Adding a New Export Format

1. Create `export/new_exporter.py`
2. Implement exporter interface:

```python
class NewExporter:
    def export(self, score: Score, path: str, **options) -> None:
        """Export score to file."""
        ...
    
    @classmethod
    def file_extension(cls) -> str:
        return ".new"
```

3. Add to export menu in `gui/main_window.py`

### Adding New Commands

1. Update `core/command_parser.py`:
   - Add parsing rule for new command
   - Create new `ParsedElement` subclass if needed

2. Update `core/command_executor.py`:
   - Handle new element type in execution

3. Update syntax highlighting in `gui/command_input.py`

---

## Dependencies

### Required

| Package | Purpose | Version |
|---------|---------|---------|
| music21 | Music processing | ≥9.0 |
| PySide6 | GUI framework | ≥6.5 |

### Optional

| Package | Purpose | Fallback |
|---------|---------|----------|
| verovio | Score rendering | QTextBrowser |
| oemer | OMR | Manual input |
| onnxruntime | ML inference | - |
| abjad | PDF export | No PDF |

---

## Performance Considerations

### Large Scores

- Lazy loading of score parts
- Virtualized rendering for many measures
- Background processing for exports

### OMR Processing

- Async processing with progress indication
- Caching of intermediate results
- Memory management for large images

### UI Responsiveness

- Background threads for long operations
- Debounced updates during editing
- Efficient SVG rendering

---

## Future Architecture Considerations

### Planned Improvements

1. **Plugin System**: Dynamic loading of OMR engines and exporters
2. **MIDI Playback**: Real-time audio synthesis
3. **Multi-page Support**: Document model for multi-page scores
4. **Cloud Sync**: Optional cloud storage integration
5. **Collaboration**: Real-time multi-user editing

### Technical Debt

- Consider migrating from music21 to more lightweight core
- Abstract SVG rendering for multiple backends
- Standardize error handling across layers

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

When adding new features:
1. Maintain layer boundaries
2. Add comprehensive tests
3. Update documentation
4. Follow existing patterns
