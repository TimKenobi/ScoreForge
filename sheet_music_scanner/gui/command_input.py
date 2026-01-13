"""
Command Input Panel - Text-based music notation input widget.

Provides a text editor for entering music via commands, with syntax
highlighting, auto-completion, and real-time preview.
"""

from __future__ import annotations

from typing import Optional
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QFrame, QSplitter, QToolButton, QMenu, QMessageBox,
    QPlainTextEdit, QCompleter, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QStringListModel
from PySide6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QTextDocument, QKeySequence, QShortcut, QTextCursor,
)

from sheet_music_scanner.core.command_parser import (
    CommandParser, ParsedElement, ParsedNote, ParsedRest, 
    ParsedChord, ParsedBarline, ParsedCommand, format_help,
)
from sheet_music_scanner.gui.theme import get_theme_manager

logger = logging.getLogger(__name__)


class CommandSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for music commands."""
    
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._setup_formats()
    
    def _setup_formats(self):
        """Set up text formats for different syntax elements."""
        # Pitch format (notes like C4, D#5)
        self.pitch_format = QTextCharFormat()
        self.pitch_format.setForeground(QColor("#2196F3"))  # Blue
        self.pitch_format.setFontWeight(QFont.Weight.Bold)
        
        # Duration format (w, h, q, e, s)
        self.duration_format = QTextCharFormat()
        self.duration_format.setForeground(QColor("#4CAF50"))  # Green
        
        # Lyric format (quoted strings)
        self.lyric_format = QTextCharFormat()
        self.lyric_format.setForeground(QColor("#FF9800"))  # Orange
        self.lyric_format.setFontItalic(True)
        
        # Command format (key:, time:, etc.)
        self.command_format = QTextCharFormat()
        self.command_format.setForeground(QColor("#9C27B0"))  # Purple
        self.command_format.setFontWeight(QFont.Weight.Bold)
        
        # Rest format
        self.rest_format = QTextCharFormat()
        self.rest_format.setForeground(QColor("#607D8B"))  # Gray
        
        # Barline format
        self.barline_format = QTextCharFormat()
        self.barline_format.setForeground(QColor("#795548"))  # Brown
        self.barline_format.setFontWeight(QFont.Weight.Bold)
        
        # Comment format
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#9E9E9E"))  # Light gray
        self.comment_format.setFontItalic(True)
        
        # Error format
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor("#F44336"))
        self.error_format.setUnderlineStyle(
            QTextCharFormat.UnderlineStyle.WaveUnderline
        )
        
        # Chord bracket format
        self.bracket_format = QTextCharFormat()
        self.bracket_format.setForeground(QColor("#E91E63"))  # Pink
        self.bracket_format.setFontWeight(QFont.Weight.Bold)
    
    def highlightBlock(self, text: str):
        """Highlight a block of text."""
        import re
        
        # Skip empty lines
        if not text.strip():
            return
        
        # Comments
        if text.strip().startswith("#"):
            self.setFormat(0, len(text), self.comment_format)
            return
        
        # Commands (key:, time:, tempo:, clef:)
        cmd_match = re.match(r"^(key|time|tempo|clef):", text, re.IGNORECASE)
        if cmd_match:
            self.setFormat(0, cmd_match.end(), self.command_format)
            return
        
        # Process tokens
        pos = 0
        while pos < len(text):
            # Skip whitespace
            if text[pos].isspace():
                pos += 1
                continue
            
            # Find next token boundary
            token_start = pos
            
            # Handle quoted strings
            if text[pos] == '"':
                end = text.find('"', pos + 1)
                if end != -1:
                    self.setFormat(pos, end - pos + 1, self.lyric_format)
                    pos = end + 1
                    continue
            
            # Handle brackets (chords)
            if text[pos] == '[':
                self.setFormat(pos, 1, self.bracket_format)
                pos += 1
                continue
            if text[pos] == ']':
                self.setFormat(pos, 1, self.bracket_format)
                pos += 1
                continue
            
            # Handle barlines
            if text[pos] == '|':
                bar_end = pos
                while bar_end < len(text) and text[bar_end] == '|':
                    bar_end += 1
                self.setFormat(pos, bar_end - pos, self.barline_format)
                pos = bar_end
                continue
            
            # Find token end
            token_end = pos
            while token_end < len(text) and not text[token_end].isspace():
                if text[token_end] in '"[]|':
                    break
                token_end += 1
            
            token = text[pos:token_end]
            
            # Rest
            if token.lower() == 'r' or token.lower() == 'rest':
                self.setFormat(pos, len(token), self.rest_format)
            # Pitch (note)
            elif re.match(r'^[A-Ga-g][#b]{0,2}\d$', token):
                self.setFormat(pos, len(token), self.pitch_format)
            # Duration
            elif re.match(r'^[whqest]\.?$', token, re.IGNORECASE):
                self.setFormat(pos, len(token), self.duration_format)
            # Barline words
            elif token.lower() == 'measure':
                self.setFormat(pos, len(token), self.barline_format)
            
            pos = token_end


class CommandInputPanel(QWidget):
    """
    Panel for entering music via text commands.
    
    Features:
    - Multi-line text editor with syntax highlighting
    - Real-time parsing and validation
    - Preview of parsed elements
    - Insert snippets for common patterns
    - Help documentation
    
    Signals:
        commands_parsed: Emitted when valid commands are parsed
        apply_requested: Emitted when user wants to apply commands to score
    """
    
    commands_parsed = Signal(list)  # list of ParsedElement
    apply_requested = Signal(list)  # list of ParsedElement to add to score
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.parser = CommandParser()
        self._last_parsed: list[ParsedElement] = []
        
        self._setup_ui()
        self._setup_completer()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header with title and help button
        header = QHBoxLayout()
        
        title = QLabel("Command Input")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Snippet menu button
        self.snippet_btn = QToolButton()
        self.snippet_btn.setText("📋 Snippets")
        self.snippet_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._setup_snippet_menu()
        header.addWidget(self.snippet_btn)
        
        # Help button
        self.help_btn = QPushButton("❓ Help")
        self.help_btn.setMaximumWidth(80)
        self.help_btn.clicked.connect(self._show_help)
        header.addWidget(self.help_btn)
        
        layout.addLayout(header)
        
        # Main splitter for editor and preview
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Text editor
        editor_frame = QFrame()
        editor_frame.setFrameShape(QFrame.Shape.StyledPanel)
        editor_layout = QVBoxLayout(editor_frame)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "Enter music commands here...\n\n"
            "Examples:\n"
            "  C4 q \"Al-\"\n"
            "  D4 h \"le-\"\n"
            "  E4 w \"lu-\" \"ia\"\n"
            "  |\n"
            "\n"
            "Click 'Help' for full syntax guide."
        )
        
        # Set monospace font (use platform-appropriate font)
        font = QFont("Menlo")  # macOS default monospace
        if not font.exactMatch():
            font = QFont("Consolas")  # Windows fallback
        if not font.exactMatch():
            font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(12)
        self.editor.setFont(font)
        
        # Add syntax highlighter
        self.highlighter = CommandSyntaxHighlighter(self.editor.document())
        
        editor_layout.addWidget(self.editor)
        splitter.addWidget(editor_frame)
        
        # Preview panel
        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(4, 4, 4, 4)
        
        preview_header = QLabel("Preview")
        preview_header.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(preview_header)
        
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(100)
        self.preview.setFont(font)
        # Preview background handled by theme palette
        preview_layout.addWidget(self.preview)
        
        splitter.addWidget(preview_frame)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 100])
        
        layout.addWidget(splitter, 1)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self._on_validate)
        btn_layout.addWidget(self.validate_btn)
        
        self.apply_btn = QPushButton("Apply to Score")
        self.apply_btn.setProperty("primary", True)  # Use theme primary button style
        self.apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)
    
    def _setup_snippet_menu(self):
        """Set up the snippets menu."""
        menu = QMenu(self)
        
        snippets = [
            ("Scale (C Major)", "C4 e D4 e E4 e F4 e G4 e A4 e B4 e C5 e"),
            ("Arpeggio", "[C4 E4 G4] q [E4 G4 C5] q [G4 C5 E5] q"),
            ("Simple Melody", 'C4 q "Twink-" C4 q "le" G4 q "twink-" G4 q "le"'),
            ("Hymn Start", 'key: G major\ntime: 4/4\ntempo: 100\n\nG4 q "A-"'),
            ("Measure Break", "|"),
            ("Double Barline", "||"),
            ("Final Barline", "|||"),
            ("Quarter Rest", "r q"),
            ("Half Rest", "r h"),
        ]
        
        for name, snippet in snippets:
            action = menu.addAction(name)
            action.setData(snippet)
            action.triggered.connect(
                lambda checked, s=snippet: self._insert_snippet(s)
            )
        
        self.snippet_btn.setMenu(menu)
    
    def _setup_completer(self):
        """Set up auto-completion."""
        completions = [
            # Pitches
            "C4", "D4", "E4", "F4", "G4", "A4", "B4",
            "C5", "D5", "E5", "F5", "G5", "A5", "B5",
            "C3", "D3", "E3", "F3", "G3", "A3", "B3",
            # Accidentals
            "C#4", "D#4", "F#4", "G#4", "A#4",
            "Db4", "Eb4", "Gb4", "Ab4", "Bb4",
            # Durations
            "w", "h", "q", "e", "s",
            "w.", "h.", "q.", "e.", "s.",
            # Commands
            "key:", "time:", "tempo:", "clef:",
            "key: C major", "key: G major", "key: D major",
            "key: A minor", "key: E minor",
            "time: 4/4", "time: 3/4", "time: 6/8", "time: 2/4",
            "tempo: 60", "tempo: 80", "tempo: 100", "tempo: 120",
            "clef: treble", "clef: bass", "clef: alto",
            # Rests
            "r", "r q", "r h", "r w", "r e",
            # Barlines
            "|", "||", "|||", "measure",
        ]
        
        model = QStringListModel(completions)
        self.completer = QCompleter(model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.editor.textChanged.connect(self._on_text_changed)
    
    def _on_text_changed(self):
        """Handle text changes - parse and update preview."""
        text = self.editor.toPlainText()
        
        if not text.strip():
            self.preview.clear()
            self.status_label.setText("Ready")
            self._last_parsed = []
            return
        
        try:
            elements = self.parser.parse(text)
            self._last_parsed = elements
            
            # Update preview
            preview_text = self._format_preview(elements)
            self.preview.setPlainText(preview_text)
            
            # Update status
            note_count = sum(1 for e in elements if isinstance(e, (ParsedNote, ParsedChord)))
            rest_count = sum(1 for e in elements if isinstance(e, ParsedRest))
            
            if self.parser.errors:
                self.status_label.setText(
                    f"⚠️ {len(self.parser.errors)} error(s) | "
                    f"{note_count} notes, {rest_count} rests"
                )
                self.status_label.setStyleSheet("color: #FFA500; font-size: 11px;")  # Orange
            else:
                self.status_label.setText(
                    f"✓ Valid | {note_count} notes, {rest_count} rests"
                )
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")  # Green
            
            self.commands_parsed.emit(elements)
            
        except Exception as e:
            logger.exception("Parse error")
            self.status_label.setText(f"❌ Error: {e}")
            self.status_label.setStyleSheet("color: #FF6B6B; font-size: 11px;")  # Light red
    
    def _format_preview(self, elements: list[ParsedElement]) -> str:
        """Format parsed elements for preview display."""
        parts = []
        
        for elem in elements:
            if isinstance(elem, ParsedNote):
                s = f"♪ {elem.pitch}"
                if elem.duration != elem.duration.QUARTER:
                    s += f"({elem.duration.value})"
                if elem.dotted:
                    s += "."
                if elem.lyric:
                    s += f' "{elem.lyric}"'
                parts.append(s)
            
            elif isinstance(elem, ParsedRest):
                s = f"𝄽 rest({elem.duration.value})"
                if elem.dotted:
                    s += "."
                parts.append(s)
            
            elif isinstance(elem, ParsedChord):
                pitches = " ".join(n.pitch for n in elem.notes)
                s = f"🎵 [{pitches}]({elem.duration.value})"
                if elem.lyric:
                    s += f' "{elem.lyric}"'
                parts.append(s)
            
            elif isinstance(elem, ParsedBarline):
                if elem.style == "double":
                    parts.append("║")
                elif elem.style == "final":
                    parts.append("𝄂")
                else:
                    parts.append("│")
            
            elif isinstance(elem, ParsedCommand):
                parts.append(f"⚙ {elem.command}={elem.value}")
        
        return " ".join(parts)
    
    def _insert_snippet(self, snippet: str):
        """Insert a snippet at cursor position."""
        cursor = self.editor.textCursor()
        
        # Add newline if not at start of line
        if cursor.positionInBlock() > 0:
            snippet = "\n" + snippet
        
        cursor.insertText(snippet)
        self.editor.setFocus()
    
    def _on_clear(self):
        """Clear the editor."""
        self.editor.clear()
        self.preview.clear()
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #666;")
    
    def _on_validate(self):
        """Validate current input and show detailed errors."""
        text = self.editor.toPlainText()
        
        if not text.strip():
            QMessageBox.information(
                self, "Validation", "No input to validate."
            )
            return
        
        errors = self.parser.validate(text)
        
        if errors:
            error_text = "\n".join(
                f"Line {e.line}: {str(e)}" for e in errors
            )
            QMessageBox.warning(
                self, "Validation Errors", 
                f"Found {len(errors)} error(s):\n\n{error_text}"
            )
        else:
            elements = self.parser.parse(text)
            note_count = sum(1 for e in elements if isinstance(e, (ParsedNote, ParsedChord)))
            QMessageBox.information(
                self, "Validation Passed",
                f"✓ Input is valid!\n\n"
                f"Parsed {len(elements)} elements including {note_count} notes."
            )
    
    def _on_apply(self):
        """Apply parsed commands to the score."""
        if not self._last_parsed:
            QMessageBox.warning(
                self, "No Content",
                "No valid commands to apply. Enter some notes first."
            )
            return
        
        self.apply_requested.emit(self._last_parsed)
    
    def _show_help(self):
        """Show help documentation."""
        help_text = format_help()
        
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Command Syntax Help")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setText("Music Command Syntax Guide")
        dialog.setDetailedText(help_text)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Make detail text visible by default
        for btn in dialog.buttons():
            if dialog.buttonRole(btn) == QMessageBox.ButtonRole.ActionRole:
                btn.click()
                break
        
        dialog.exec()
    
    def get_parsed_elements(self) -> list[ParsedElement]:
        """Get the currently parsed elements."""
        return self._last_parsed
    
    def set_text(self, text: str):
        """Set the editor text."""
        self.editor.setPlainText(text)
    
    def get_text(self) -> str:
        """Get the editor text."""
        return self.editor.toPlainText()
