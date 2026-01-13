# User Guide

Welcome to ScoreForge! This guide will help you get started and make the most of the application.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Importing Sheet Music](#importing-sheet-music)
3. [Using Command Input](#using-command-input)
4. [Interactive Editing](#interactive-editing)
5. [Editing Your Score](#editing-your-score)
6. [Exporting Your Work](#exporting-your-work)
7. [Themes and Customization](#themes-and-customization)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Tips and Tricks](#tips-and-tricks)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Launching the Application

```bash
python -m sheet_music_scanner
```

### Main Interface

The interface is divided into four main areas:

```
┌─────────────────────────────────────────────────────────────┐
│  Menu Bar                                                    │
├──────────────┬──────────────────────────┬───────────────────┤
│              │                          │                   │
│   Command    │                          │     Editor        │
│    Input     │     Interactive          │     Panel         │
│    Panel     │       Editor             │                   │
│              │     (Score View)         │   • Transposition │
│   • Text     │                          │   • Key Changes   │
│   • Commands │     • Drag notes         │   • Lyrics        │
│              │     • Click to select    │                   │
│              │                          │                   │
└──────────────┴──────────────────────────┴───────────────────┘
```

1. **Command Input (Left)**: Text-based music entry
2. **Interactive Editor (Center)**: Visual score with drag-and-drop editing
3. **Editor Panel (Right)**: Controls for transposition, key changes, and lyrics

---

## Importing Sheet Music

### Scanning Images

1. Go to **File → Import Image** (or press `Ctrl+I`)
2. Select an image file (PNG, JPG, TIFF, BMP)
3. Wait for OMR (Optical Music Recognition) processing
4. Review the recognized notation

### Drag and Drop

Simply drag an image file from your file manager and drop it onto the application window.

### Supported Formats

- **Images**: PNG, JPG, JPEG, TIFF, BMP
- **PDF**: Multi-page PDF documents
- **MusicXML**: Import existing digital scores

### Tips for Best Recognition

- Use high-resolution scans (300 DPI or higher)
- Ensure good contrast between notes and background
- Straighten skewed images before importing
- Crop to just the music (remove margins)

---

## Using Command Input

The Command Input panel on the left lets you enter music using text commands.

### Quick Example

```
key: C major
time: 4/4

C4 q "Hel-"
D4 q "lo"
E4 h "World"
|
F4 q G4 q A4 q B4 q
|
C5 w
||
```

### Basic Elements

| Element | Syntax | Example |
|---------|--------|---------|
| Note | `PITCH DURATION` | `C4 q` |
| Rest | `r DURATION` | `r q` |
| Chord | `[NOTES] DURATION` | `[C4 E4 G4] q` |
| Barline | `\|` | `\|` |
| Lyric | `"TEXT"` | `"Hel-"` |

### Processing Commands

Click the **"Process"** button or press `Ctrl+Enter` to convert your commands into notation.

### Syntax Highlighting

The command input uses color coding:
- **Blue**: Note pitches
- **Green**: Durations
- **Purple**: Commands (key, time, etc.)
- **Orange**: Lyrics
- **Gray**: Comments

For detailed command syntax, see [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md).

---

## Interactive Editing

The center panel displays your score with visual notation.

### Selecting Notes

- **Click** on a note to select it
- **Shift+Click** to extend selection
- **Ctrl+Click** to toggle individual notes

### Moving Notes

- **Drag** a note up or down to change its pitch
- Selected notes snap to valid pitches
- Changes update in real-time

### Keyboard Controls

| Key | Action |
|-----|--------|
| ↑ | Move pitch up (half step) |
| ↓ | Move pitch down (half step) |
| Delete | Remove selected note |
| Escape | Deselect all |

### Visual Feedback

- **Blue outline**: Selected note
- **Yellow highlight**: Note being dragged
- **Red outline**: Invalid position

---

## Editing Your Score

The Editor Panel on the right provides controls for global edits.

### Transposition

1. Select the **Transposition** section
2. Choose interval (e.g., "Major 2nd Up")
3. Click **Apply Transposition**

Or use the Transpose dialog:
1. **Edit → Transpose** (`Ctrl+T`)
2. Enter semitones (+/- number)
3. Click **OK**

### Key Changes

1. Select the **Key Signature** section
2. Choose the new key from the dropdown
3. Click **Apply Key Change**

### Octave Shift

1. Select notes in the Interactive Editor
2. Use **Edit → Shift Octave → Up/Down**
3. Or use keyboard: `Ctrl+↑` / `Ctrl+↓`

### Adding/Editing Lyrics

1. Select a note in the Interactive Editor
2. In the Editor Panel, find **Lyrics**
3. Enter the lyric text
4. Press Enter or click **Apply**

---

## Exporting Your Work

### MIDI Export

For audio playback in DAWs or media players:

1. **File → Export → MIDI**
2. Choose save location
3. Select MIDI format (Type 0 or Type 1)

### MusicXML Export

For notation software (MuseScore, Finale, Sibelius):

1. **File → Export → MusicXML**
2. Choose save location
3. Select compressed (.mxl) or uncompressed (.musicxml)

### PDF Export

For printing high-quality sheet music:

1. **File → Export → PDF**
2. Choose save location
3. Select paper size and orientation

**Note**: PDF export requires LilyPond installed.

---

## Themes and Customization

### Changing Themes

Access themes via **View → Theme**:

- **System**: Matches your OS theme preference
- **Light**: Bright, clean interface
- **Dark**: Easy on the eyes for extended use

### Quick Toggle

Press `Ctrl+Shift+D` to toggle between light and dark modes.

### Theme Persistence

Your theme choice is saved and restored when you reopen the app.

---

## Keyboard Shortcuts

### File Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+I` | Import Image |
| `Ctrl+O` | Open MusicXML |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Q` | Quit |

### Edit Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+T` | Transpose Dialog |
| `Ctrl+A` | Select All |
| `Delete` | Delete Selection |

### View Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl++` | Zoom In |
| `Ctrl+-` | Zoom Out |
| `Ctrl+0` | Reset Zoom |
| `Ctrl+Shift+D` | Toggle Dark Mode |
| `F1` | Open Documentation |

### Command Input

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Process Commands |
| `Ctrl+/` | Toggle Comment |

---

## Tips and Tricks

### Workflow Efficiency

1. **Use command input for new music**: It's often faster than clicking
2. **Process frequently**: Check your work as you go
3. **Use keyboard shortcuts**: Much faster than menus

### OMR Best Practices

1. **Pre-process images**: Adjust contrast and crop before importing
2. **Review carefully**: OMR may misrecognize complex passages
3. **Edit immediately**: Fix errors while the music is fresh in mind

### Organization

1. **Save often**: Use `Ctrl+S` frequently
2. **Use meaningful filenames**: Include piece name and date
3. **Export multiple formats**: Keep MusicXML as your "source" format

### Advanced Tips

1. **Batch processing**: Process similar images with same settings
2. **Templates**: Save empty scores with common settings
3. **Backup**: Keep copies of important work

---

## Troubleshooting

### Common Issues

#### OMR Recognition is Poor

- Ensure image is high resolution (300+ DPI)
- Check image is properly oriented
- Try adjusting contrast/brightness before import
- Some handwritten or stylized notation may not recognize well

#### Notes Don't Sound Right

- Check key signature is correct
- Verify accidentals are properly applied
- Ensure octave numbers are correct (4 = middle C octave)

#### Export Fails

- **MIDI**: Ensure score is not empty
- **PDF**: Verify LilyPond is installed
- **MusicXML**: Check for unsupported features

#### Application Crashes

- Update to latest version
- Check Python version (3.10+ required)
- Try with a fresh virtual environment
- Report persistent issues on GitHub

### Getting Help

1. **Documentation**: Press `F1` or **Help → Documentation**
2. **GitHub Issues**: Report bugs and request features
3. **Community**: Join discussions on GitHub

### Reporting Bugs

When reporting issues, include:
- Operating system and version
- Python version
- Steps to reproduce
- Error messages (if any)
- Sample files (if applicable)

---

## What's Next?

- Explore the [Command Reference](COMMAND_REFERENCE.md) for advanced syntax
- Check the [Architecture Guide](ARCHITECTURE.md) for development
- Visit the [GitHub repository](https://github.com/yourusername/sheet-music-scanner) for updates

Happy music making! 🎵
