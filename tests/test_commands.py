"""
Tests for the command parser and executor.
"""

import pytest
from sheet_music_scanner.core.command_parser import (
    CommandParser, ParsedNote, ParsedRest, ParsedChord,
    ParsedBarline, ParsedCommand, Duration,
)
from sheet_music_scanner.core.command_executor import (
    CommandExecutor, execute_commands,
)


class TestCommandParser:
    """Tests for CommandParser."""
    
    def test_parse_simple_note(self):
        """Test parsing a simple note."""
        parser = CommandParser()
        elements = parser.parse("C4 q")
        
        assert len(elements) == 1
        assert isinstance(elements[0], ParsedNote)
        assert elements[0].pitch == "C4"
        assert elements[0].duration == Duration.QUARTER
        assert elements[0].lyric is None
    
    def test_parse_note_with_lyric(self):
        """Test parsing a note with a lyric."""
        parser = CommandParser()
        elements = parser.parse('D5 h "Al-"')
        
        assert len(elements) == 1
        note = elements[0]
        assert isinstance(note, ParsedNote)
        assert note.pitch == "D5"
        assert note.duration == Duration.HALF
        assert note.lyric == "Al-"
    
    def test_parse_dotted_note(self):
        """Test parsing a dotted note."""
        parser = CommandParser()
        elements = parser.parse("E4 q.")
        
        assert len(elements) == 1
        assert elements[0].dotted is True
    
    def test_parse_rest(self):
        """Test parsing a rest."""
        parser = CommandParser()
        elements = parser.parse("r q")
        
        assert len(elements) == 1
        assert isinstance(elements[0], ParsedRest)
        assert elements[0].duration == Duration.QUARTER
    
    def test_parse_chord(self):
        """Test parsing a chord."""
        parser = CommandParser()
        elements = parser.parse("[C4 E4 G4] q")
        
        assert len(elements) == 1
        chord = elements[0]
        assert isinstance(chord, ParsedChord)
        assert len(chord.notes) == 3
        assert chord.notes[0].pitch == "C4"
        assert chord.notes[1].pitch == "E4"
        assert chord.notes[2].pitch == "G4"
        assert chord.duration == Duration.QUARTER
    
    def test_parse_barline(self):
        """Test parsing barlines."""
        parser = CommandParser()
        
        single = parser.parse("|")
        assert len(single) == 1
        assert isinstance(single[0], ParsedBarline)
        assert single[0].style == "single"
        
        double = parser.parse("||")
        assert len(double) == 1
        assert double[0].style == "double"
        
        final = parser.parse("|||")
        assert len(final) == 1
        assert final[0].style == "final"
    
    def test_parse_key_command(self):
        """Test parsing key signature command."""
        parser = CommandParser()
        elements = parser.parse("key: G major")
        
        assert len(elements) == 1
        cmd = elements[0]
        assert isinstance(cmd, ParsedCommand)
        assert cmd.command == "key"
        assert cmd.value == "G major"
    
    def test_parse_time_command(self):
        """Test parsing time signature command."""
        parser = CommandParser()
        elements = parser.parse("time: 4/4")
        
        assert len(elements) == 1
        cmd = elements[0]
        assert cmd.command == "time"
        assert cmd.value == "4/4"
    
    def test_parse_tempo_command(self):
        """Test parsing tempo command."""
        parser = CommandParser()
        elements = parser.parse("tempo: 120")
        
        assert len(elements) == 1
        cmd = elements[0]
        assert cmd.command == "tempo"
        assert cmd.value == "120"
    
    def test_parse_multiline(self):
        """Test parsing multiline input."""
        parser = CommandParser()
        text = """
        key: C major
        time: 4/4
        
        C4 q "Do"
        D4 q "Re"
        E4 q "Mi"
        |
        """
        elements = parser.parse(text)
        
        # 2 commands + 3 notes + 1 barline = 6
        assert len(elements) == 6
        assert isinstance(elements[0], ParsedCommand)
        assert isinstance(elements[1], ParsedCommand)
        assert isinstance(elements[2], ParsedNote)
        assert isinstance(elements[5], ParsedBarline)
    
    def test_parse_comment_ignored(self):
        """Test that comments are ignored."""
        parser = CommandParser()
        elements = parser.parse("# This is a comment\nC4 q")
        
        assert len(elements) == 1
        assert isinstance(elements[0], ParsedNote)
    
    def test_parse_accidentals(self):
        """Test parsing notes with accidentals."""
        parser = CommandParser()
        
        sharp = parser.parse("C#4 q")
        assert sharp[0].pitch == "C#4"
        
        flat = parser.parse("Bb3 q")
        assert flat[0].pitch == "BB3"  # Normalized to uppercase
    
    def test_all_durations(self):
        """Test all duration types."""
        parser = CommandParser()
        
        durations = [
            ("C4 w", Duration.WHOLE),
            ("C4 h", Duration.HALF),
            ("C4 q", Duration.QUARTER),
            ("C4 e", Duration.EIGHTH),
            ("C4 s", Duration.SIXTEENTH),
        ]
        
        for text, expected in durations:
            elements = parser.parse(text)
            assert elements[0].duration == expected


class TestCommandExecutor:
    """Tests for CommandExecutor."""
    
    def test_create_simple_score(self):
        """Test creating a score from simple notes."""
        parser = CommandParser()
        elements = parser.parse("C4 q D4 q E4 q")
        
        score = execute_commands(elements, "Test Score")
        
        assert score is not None
        assert score.title == "Test Score"
        assert score.num_parts >= 1
    
    def test_create_score_with_lyrics(self):
        """Test creating a score with lyrics."""
        parser = CommandParser()
        elements = parser.parse('C4 q "Do" D4 q "Re" E4 q "Mi"')
        
        score = execute_commands(elements)
        
        # Check that lyrics were added
        notes = list(score._score.recurse().notes)
        lyrics = [n.lyric for n in notes if hasattr(n, 'lyric') and n.lyric]
        
        assert len(lyrics) == 3
        assert lyrics[0] == "Do"
        assert lyrics[1] == "Re"
        assert lyrics[2] == "Mi"
    
    def test_create_score_with_key(self):
        """Test creating a score with a key signature."""
        parser = CommandParser()
        elements = parser.parse("key: G major\nG4 q A4 q B4 q")
        
        score = execute_commands(elements)
        
        # Should have key signature
        assert score.key_signature is not None
    
    def test_create_chord(self):
        """Test creating a chord in the score."""
        parser = CommandParser()
        elements = parser.parse("[C4 E4 G4] q")
        
        score = execute_commands(elements)
        
        # Find the chord
        chords = list(score._score.recurse().getElementsByClass('Chord'))
        assert len(chords) == 1
        assert len(chords[0].pitches) == 3
    
    def test_duration_conversion(self):
        """Test that durations are converted correctly."""
        executor = CommandExecutor()
        
        # Test various durations
        assert executor.DURATION_MAP[Duration.WHOLE] == 4.0
        assert executor.DURATION_MAP[Duration.HALF] == 2.0
        assert executor.DURATION_MAP[Duration.QUARTER] == 1.0
        assert executor.DURATION_MAP[Duration.EIGHTH] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
