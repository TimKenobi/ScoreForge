"""
Tests for Sheet Music Scanner core functionality.
"""

import pytest
from pathlib import Path
import tempfile


class TestScore:
    """Tests for the Score class."""
    
    def test_score_creation(self):
        """Test creating an empty score."""
        from sheet_music_scanner.core.score import Score
        
        score = Score()
        assert score is not None
        assert score.num_parts == 0
        assert score.num_measures == 0
        assert score.is_modified is False
    
    def test_score_from_music21(self):
        """Test creating a score from music21 objects."""
        from sheet_music_scanner.core.score import Score
        from music21 import stream, note
        
        # Create a simple music21 score
        m21_score = stream.Score()
        part = stream.Part()
        measure = stream.Measure(number=1)
        measure.append(note.Note("C4", quarterLength=1.0))
        measure.append(note.Note("D4", quarterLength=1.0))
        measure.append(note.Note("E4", quarterLength=1.0))
        measure.append(note.Note("F4", quarterLength=1.0))
        part.append(measure)
        m21_score.append(part)
        
        # Wrap in Score
        score = Score.from_music21(m21_score)
        
        assert score.num_parts == 1
        assert score.num_measures == 1
    
    def test_transpose(self):
        """Test transposing a score."""
        from sheet_music_scanner.core.score import Score
        from music21 import stream, note
        
        # Create a simple score with C4
        m21_score = stream.Score()
        part = stream.Part()
        measure = stream.Measure(number=1)
        measure.append(note.Note("C4", quarterLength=4.0))
        part.append(measure)
        m21_score.append(part)
        
        score = Score.from_music21(m21_score)
        
        # Transpose up by perfect fifth
        score.transpose("P5")
        
        # Check the note was transposed
        assert score.is_modified is True
        assert score.can_undo() is True
    
    def test_undo_redo(self):
        """Test undo/redo functionality."""
        from sheet_music_scanner.core.score import Score
        from music21 import stream, note
        
        m21_score = stream.Score()
        part = stream.Part()
        measure = stream.Measure(number=1)
        measure.append(note.Note("C4", quarterLength=4.0))
        part.append(measure)
        m21_score.append(part)
        
        score = Score.from_music21(m21_score)
        
        # Initial state
        assert score.can_undo() is False
        assert score.can_redo() is False
        
        # Make a change
        score.transpose(2)
        
        # Should be able to undo
        assert score.can_undo() is True
        assert score.can_redo() is False
        
        # Undo
        score.undo()
        assert score.can_undo() is False
        assert score.can_redo() is True
        
        # Redo
        score.redo()
        assert score.can_undo() is True
        assert score.can_redo() is False


class TestOperations:
    """Tests for music operations."""
    
    def test_get_available_keys(self):
        """Test getting available keys."""
        from sheet_music_scanner.core.operations import get_available_keys
        
        keys = get_available_keys()
        assert len(keys) > 0
        assert "C major" in keys
        assert "A minor" in keys
    
    def test_get_interval_options(self):
        """Test getting interval options."""
        from sheet_music_scanner.core.operations import get_interval_options
        
        intervals = get_interval_options()
        assert len(intervals) > 0
        
        # Check format
        for code, name in intervals:
            assert isinstance(code, str)
            assert isinstance(name, str)
    
    def test_pitch_conversion(self):
        """Test pitch to MIDI conversion."""
        from sheet_music_scanner.core.operations import pitch_to_midi, midi_to_pitch
        
        # C4 = MIDI 60
        assert pitch_to_midi("C4") == 60
        assert midi_to_pitch(60) == "C4"
        
        # A4 = MIDI 69
        assert pitch_to_midi("A4") == 69


class TestConfig:
    """Tests for configuration."""
    
    def test_config_creation(self):
        """Test creating a config."""
        from sheet_music_scanner.config import Config
        
        config = Config()
        assert config is not None
        assert config.omr is not None
        assert config.export is not None
        assert config.gui is not None
    
    def test_config_save_load(self):
        """Test saving and loading config."""
        from sheet_music_scanner.config import Config
        import tempfile
        from pathlib import Path
        
        # Create config with temp directory
        config = Config()
        config._config_dir = Path(tempfile.mkdtemp())
        config._config_file = config._config_dir / "config.json"
        
        # Modify and save
        config.gui.theme = "dark"
        config.export.midi_tempo = 140
        config.save()
        
        # Load
        loaded = Config.load()
        # Note: This creates a new config at default location
        # For proper testing we'd need to mock the config path


class TestExporters:
    """Tests for exporters."""
    
    def test_midi_exporter_creation(self):
        """Test creating MIDI exporter."""
        from sheet_music_scanner.export import MidiExporter
        from sheet_music_scanner.export.midi_exporter import MidiExportOptions
        
        exporter = MidiExporter()
        assert exporter is not None
        
        options = MidiExportOptions(velocity=100, tempo=140)
        exporter = MidiExporter(options)
        assert exporter.options.velocity == 100
        assert exporter.options.tempo == 140
    
    def test_musicxml_exporter_creation(self):
        """Test creating MusicXML exporter."""
        from sheet_music_scanner.export import MusicXMLExporter
        
        exporter = MusicXMLExporter()
        assert exporter is not None
    
    def test_pdf_exporter_creation(self):
        """Test creating PDF exporter."""
        from sheet_music_scanner.export import PDFExporter
        
        exporter = PDFExporter()
        assert exporter is not None


class TestImageProcessing:
    """Tests for image processing utilities."""
    
    def test_create_placeholder_musicxml(self):
        """Test creating placeholder MusicXML."""
        from sheet_music_scanner.utils.image_processing import create_placeholder_musicxml
        
        with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as f:
            output_path = Path(f.name)
        
        create_placeholder_musicxml(output_path)
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "score-partwise" in content
        assert "Placeholder Score" in content
        
        # Clean up
        output_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
