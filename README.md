# ScoreForge

> Transform scanned sheet music into editable digital formats with OMR, command-based input, and intuitive editing.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-orange.svg)](https://coff.ee/timkenobi)

## ✨ Features

- **Optical Music Recognition (OMR)**: Scan images or PDFs of sheet music and convert them to editable digital scores
- **Command-Based Input**: Enter music using simple text commands (inspired by gabc notation)
- **Interactive Editing**: Drag-and-drop notes to change pitch, click to select, use keyboard shortcuts
- **Multiple Export Formats**: Save your work as MIDI, MusicXML, or high-quality PDF
- **Transposition &amp; Key Changes**: Easily transpose music or change key signatures
- **Lyrics Support**: Add and edit lyrics with syllable alignment
- **MIDI Playback**: Play back your scores with integrated audio playback
- **Dark Mode**: Full dark theme support with system theme detection
- **Cross-Platform**: Works on macOS, Windows, and Linux

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/TimKenobi/ScoreForge.git
cd ScoreForge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .

# Install optional dependencies for full functionality
pip install pygame verovio
```

### Optional Dependencies

For full functionality, install optional dependencies:

```bash
# OMR with oemer (requires onnxruntime)
pip install oemer onnxruntime

# Enhanced notation rendering with Verovio
brew install swig  # macOS only
pip install verovio

# PDF export with LilyPond
pip install abjad
brew install lilypond  # macOS
# Ubuntu/Debian: sudo apt install lilypond
```

## 🚀 Quick Start

### Launch the Application

```bash
python -m sheet_music_scanner
# Or after installation:
scoreforge
```

### Basic Workflow

1. **Import Music**: 
   - Drag &amp; drop an image/PDF onto the window, or
   - Use `File → Import Image` (Ctrl+I)

2. **Edit Your Score**:
   - Use the Command Input panel for text-based entry
   - Drag notes up/down in the Interactive Editor
   - Use the Editor Panel for transposition and key changes

3. **Play Back**:
   - Click the Play button or press Space to play your score
   - Adjust tempo and volume with the playback controls

4. **Export**:
   - `File → Export → MIDI` for audio playback
   - `File → Export → MusicXML` for notation software
   - `File → Export → PDF` for printing

## 📝 Command Input Syntax

Enter music using simple text commands in the left panel.

### Notes

```
PITCH DURATION "LYRIC"
```

| Component | Format | Examples |
|-----------|--------|----------|
| **Pitch** | Note + Accidental + Octave | `C4`, `D#5`, `Bb3`, `F##4` |
| **Duration** | w, h, q, e, s (+ . for dotted) | `q` (quarter), `h.` (dotted half) |
| **Lyric** | Quoted text | `"Al-"`, `"le-"`, `"lu-"`, `"ia"` |

### Duration Codes

| Code | Duration |
|------|----------|
| `w` | Whole note |
| `h` | Half note |
| `q` | Quarter note |
| `e` | Eighth note |
| `s` | Sixteenth note |
| `.` | Dotted (add after duration) |

### Examples

```
# Simple melody
C4 q "Twink-"
C4 q "le"
G4 q "twink-"
G4 q "le"
|

# Rest
r q

# Chord
[C4 E4 G4] q "chord"

# Dotted note
D4 h. "hold"
```

### Special Commands

```
key: G major       # Set key signature
time: 4/4          # Set time signature
tempo: 120         # Set tempo (BPM)
clef: treble       # Set clef (treble, bass, alto, tenor)
|                  # Single barline
||                 # Double barline
|||                # Final barline
```

### Full Example

```
# Amazing Grace - First Line
key: G major
time: 3/4
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
```

## ⌨️ Keyboard Shortcuts

### File Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+I` | Import Image |
| `Ctrl+O` | Open MusicXML |
| `Ctrl+S` | Save |
| `Ctrl+Q` | Quit |

### Edit Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+T` | Transpose |

### View Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl++` | Zoom In |
| `Ctrl+-` | Zoom Out |
| `Ctrl+0` | Reset Zoom |
| `Ctrl+Shift+D` | Toggle Dark Mode |

### Playback
| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause |
| `Ctrl+Space` | Stop |

### Interactive Editor
| Action | Effect |
|--------|--------|
| Click note | Select |
| Drag up/down | Change pitch |
| ↑/↓ arrows | Move pitch by half step |
| Delete/Backspace | Remove note |

## 🎨 Themes

ScoreForge supports three theme modes:

- **System**: Follows your operating system's theme preference
- **Light**: Clean, bright interface
- **Dark**: Easy on the eyes for long sessions

Change themes via `View → Theme` or use `Ctrl+Shift+D` to toggle.

## 📚 Architecture

```
sheet_music_scanner/
├── core/                 # Core music processing
│   ├── score.py          # Score model wrapper
│   ├── operations.py     # Music operations
│   ├── command_parser.py # Text command parsing
│   ├── command_executor.py # Convert commands to score
│   └── midi_player.py    # MIDI playback engine
├── gui/                  # User interface
│   ├── main_window.py    # Main application window
│   ├── score_view.py     # Score display (Verovio)
│   ├── command_input.py  # Text command panel
│   ├── interactive_editor.py # Drag-drop editor
│   ├── editor_panel.py   # Editing controls
│   ├── playback_controls.py # Transport controls
│   └── theme.py          # Theme management
├── omr/                  # Optical Music Recognition
│   ├── processor.py      # OMR orchestration
│   ├── oemer_adapter.py  # oemer integration
│   └── audiveris_adapter.py # Audiveris integration
├── export/               # File exporters
│   ├── midi_exporter.py
│   ├── musicxml_exporter.py
│   └── pdf_exporter.py
└── utils/                # Utilities
    └── image_processing.py
```

## Supported Input Formats

- **Images**: PNG, JPG, JPEG, TIFF, BMP
- **PDF**: Multi-page PDF documents (converted to images)

## Supported Output Formats

- **MIDI** (.mid, .midi)
- **MusicXML** (.musicxml, .xml, .mxl)
- **PDF** (.pdf) - requires LilyPond

## 🔧 Configuration

Configuration is stored in:
- macOS: `~/Library/Application Support/ScoreForge/config.json`
- Windows: `%APPDATA%/ScoreForge/config.json`
- Linux: `~/.config/ScoreForge/config.json`

### Available Settings

```json
{
  "gui": {
    "theme": "system",
    "window_width": 1200,
    "window_height": 800
  },
  "omr": {
    "engine": "oemer",
    "confidence_threshold": 0.7
  },
  "export": {
    "midi_tempo": 120,
    "pdf_quality": "high"
  }
}
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=sheet_music_scanner

# Format code
black sheet_music_scanner tests
ruff check sheet_music_scanner/
```

## 📋 Roadmap

- [x] MIDI playback within the app
- [ ] Multi-page score support
- [ ] Batch processing for multiple images
- [ ] Cloud sync for scores
- [ ] Plugin system for custom OMR engines
- [ ] Mobile companion app

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## ☕ Support

If you find this project useful, consider:

- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting features
- ☕ [Buying me a coffee](https://coff.ee/timkenobi)

## 🙏 Acknowledgments

- [music21](https://web.mit.edu/music21/) - Music theory and analysis toolkit
- [oemer](https://github.com/BreezeWhite/oemer) - End-to-end OMR
- [Verovio](https://www.verovio.org/) - Music notation engraving library
- [LilyPond](https://lilypond.org/) - Music engraving program
- [PySide6](https://doc.qt.io/qtforpython/) - Python bindings for Qt
- [pygame](https://www.pygame.org/) - MIDI playback

---

Made with ❤️ by [Tim Kenobi](https://github.com/TimKenobi)

[![Buy Me a Coffee](https://img.shields.io/badge/☕_Buy_Me_a_Coffee-Support_Development-FFDD00?style=for-the-badge)](https://coff.ee/timkenobi)
