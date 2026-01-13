# Testing Plan for ScoreForge

This document lists what to test, how I tested it, and the results.

1) Unit tests
  - Run: `pytest -q` from the project root.
  - Scope: `tests/` (covers command parsing, core operations, exports)

2) Core functionality
  - `sheet_music_scanner/core/score.py`: load, modify, save operations
  - `sheet_music_scanner/core/midi_player.py`: playback start/stop
  - `sheet_music_scanner/core/operations.py`: transposition, editing

3) Exporters
  - `sheet_music_scanner/export/midi_exporter.py`
  - `sheet_music_scanner/export/musicxml_exporter.py`
  - `sheet_music_scanner/export/pdf_exporter.py`
  - Validate generated files open in external apps.

4) OMR adapters
  - `sheet_music_scanner/omr/audiveris_adapter.py`
  - `sheet_music_scanner/omr/oemer_adapter.py`
  - Verify processor pipeline handles scanned images gracefully.

5) GUI smoke tests (manual / automated)
  - Launch: `python -m sheet_music_scanner`
  - Verify main window appears, score loads, playback controls respond, and basic dialogs open.

6) Batch processing
  - `sheet_music_scanner/core/batch_processor.py` and `dialogs/batch_dialog.py` run without exceptions on sample inputs.

7) Plugins and templates
  - `sheet_music_scanner/core/plugins.py`
  - `sheet_music_scanner/core/templates.py` — ensure plugin loading and template dialogs work.

8) Integration flows
  - Full roundtrip: OMR -> edit -> export MIDI/MusicXML/PDF

How I ran tests (recorded):
- Unit test command: `cd /Users/timb/Documents/Git/MusicProgram && pytest -q`
- App launch command: `cd /Users/timb/Documents/Git/MusicProgram && python -m sheet_music_scanner`

Notes:
- If unit tests fail, run the failing tests directly and inspect tracebacks.
- GUI tests are manual; automated GUI testing is out of scope here.

Contact me if you want automated GUI tests or CI config added.
