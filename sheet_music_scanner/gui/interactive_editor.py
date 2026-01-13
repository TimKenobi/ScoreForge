"""
Interactive Score Editor - Visual note editing with drag-and-drop.

Provides an interactive canvas for:
- Clicking to select notes
- Dragging notes up/down to change pitch
- Keyboard shortcuts for editing
- Visual feedback during editing
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsTextItem,
    QGraphicsLineItem, QSizePolicy, QPushButton, QToolBar,
    QSpinBox, QComboBox,
)
from PySide6.QtCore import (
    Qt, Signal, QRectF, QPointF, QSizeF, QMimeData,
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QKeyEvent,
    QMouseEvent, QWheelEvent, QDrag, QCursor,
)

logger = logging.getLogger(__name__)


# Constants for staff rendering
STAFF_LINE_SPACING = 10  # pixels between staff lines
STAFF_MARGIN_LEFT = 60
STAFF_MARGIN_TOP = 40
NOTE_WIDTH = 30
NOTE_HEIGHT = 8
MEASURE_WIDTH = 200


@dataclass
class NotePosition:
    """Represents a note's position in the score."""
    part_index: int
    measure_index: int
    note_index: int
    pitch: str
    octave: int
    duration: float
    lyric: Optional[str] = None
    x: float = 0
    y: float = 0


class NoteItem(QGraphicsEllipseItem):
    """
    Graphical representation of a note that can be dragged.
    
    Supports:
    - Selection (click)
    - Dragging up/down to change pitch
    - Visual feedback for hover/selection
    """
    
    def __init__(
        self,
        position: NotePosition,
        parent: Optional[QGraphicsItem] = None
    ):
        # Create ellipse for note head
        super().__init__(
            -NOTE_WIDTH / 2, -NOTE_HEIGHT / 2,
            NOTE_WIDTH, NOTE_HEIGHT,
            parent
        )
        
        self.position = position
        self._original_y = 0.0
        self._is_dragging = False
        self._is_selected = False
        self._pitch_offset = 0  # Half steps from original pitch
        
        # Set up appearance
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        
        self._update_appearance()
        
        # Add lyric label if present
        if position.lyric:
            self._lyric_item = QGraphicsTextItem(position.lyric, self)
            self._lyric_item.setPos(-NOTE_WIDTH / 2, NOTE_HEIGHT)
            self._lyric_item.setFont(QFont("Arial", 8))
    
    def _update_appearance(self):
        """Update visual appearance based on state."""
        if self._is_selected:
            self.setPen(QPen(QColor("#2196F3"), 2))
            self.setBrush(QBrush(QColor("#2196F3")))
        elif self._is_dragging:
            self.setPen(QPen(QColor("#FF9800"), 2))
            self.setBrush(QBrush(QColor("#FF9800")))
        else:
            self.setPen(QPen(QColor("#333"), 1.5))
            self.setBrush(QBrush(QColor("#333")))
    
    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        if not self._is_selected:
            self.setPen(QPen(QColor("#666"), 2))
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        self._update_appearance()
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press for selection and drag start."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_selected = True
            self._is_dragging = True
            self._original_y = self.y()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._update_appearance()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self._is_dragging:
            # Only allow vertical movement (pitch change)
            new_y = event.scenePos().y()
            
            # Snap to staff line positions
            snapped_y = round(new_y / (STAFF_LINE_SPACING / 2)) * (STAFF_LINE_SPACING / 2)
            
            self.setY(snapped_y)
            
            # Calculate pitch offset
            self._pitch_offset = int((self._original_y - snapped_y) / (STAFF_LINE_SPACING / 2))
            
            self._update_appearance()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to finish drag."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._update_appearance()
            
            # Emit pitch change signal through scene
            scene = self.scene()
            if scene and hasattr(scene, 'note_pitch_changed'):
                scene.note_pitch_changed.emit(
                    self.position,
                    self._pitch_offset
                )
        super().mouseReleaseEvent(event)
    
    def get_pitch_offset(self) -> int:
        """Get the current pitch offset in half steps."""
        return self._pitch_offset


class StaffLineItem(QGraphicsLineItem):
    """A single staff line."""
    
    def __init__(self, x1: float, y: float, x2: float):
        super().__init__(x1, y, x2, y)
        self.setPen(QPen(QColor("#999"), 1))


class InteractiveScoreScene(QGraphicsScene):
    """
    Scene for interactive score editing.
    
    Signals:
        note_selected: Emitted when a note is selected
        note_pitch_changed: Emitted when a note's pitch is changed via drag
        note_deleted: Emitted when a note is deleted
    """
    
    note_selected = Signal(object)  # NotePosition
    note_pitch_changed = Signal(object, int)  # NotePosition, pitch_offset
    note_deleted = Signal(object)  # NotePosition
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._notes: list[NoteItem] = []
        self._staff_lines: list[StaffLineItem] = []
        self._measure_lines: list[QGraphicsLineItem] = []
        
        self.setBackgroundBrush(QBrush(QColor("#FAFAFA")))
    
    def clear_score(self):
        """Clear all score elements."""
        for item in self._notes:
            self.removeItem(item)
        for item in self._staff_lines:
            self.removeItem(item)
        for item in self._measure_lines:
            self.removeItem(item)
        
        self._notes.clear()
        self._staff_lines.clear()
        self._measure_lines.clear()
    
    def draw_staff(self, num_measures: int = 4, width: float = 800):
        """Draw the staff lines."""
        # Clear existing staff
        for item in self._staff_lines:
            self.removeItem(item)
        self._staff_lines.clear()
        
        staff_width = max(width, num_measures * MEASURE_WIDTH + STAFF_MARGIN_LEFT * 2)
        
        # Draw 5 staff lines
        for i in range(5):
            y = STAFF_MARGIN_TOP + i * STAFF_LINE_SPACING
            line = StaffLineItem(STAFF_MARGIN_LEFT, y, staff_width - STAFF_MARGIN_LEFT)
            self._staff_lines.append(line)
            self.addItem(line)
        
        # Draw measure lines
        for i in range(num_measures + 1):
            x = STAFF_MARGIN_LEFT + i * MEASURE_WIDTH
            y_top = STAFF_MARGIN_TOP
            y_bottom = STAFF_MARGIN_TOP + 4 * STAFF_LINE_SPACING
            
            line = QGraphicsLineItem(x, y_top, x, y_bottom)
            line.setPen(QPen(QColor("#666"), 1.5))
            self._measure_lines.append(line)
            self.addItem(line)
        
        # Add clef placeholder
        clef_text = QGraphicsTextItem("𝄞")
        clef_text.setFont(QFont("Arial", 32))
        clef_text.setPos(STAFF_MARGIN_LEFT - 45, STAFF_MARGIN_TOP - 15)
        self.addItem(clef_text)
        
        # Update scene rect
        self.setSceneRect(0, 0, staff_width, STAFF_MARGIN_TOP * 2 + 4 * STAFF_LINE_SPACING + 50)
    
    def add_note(self, position: NotePosition) -> NoteItem:
        """Add a note to the scene."""
        note = NoteItem(position)
        
        # Calculate position on staff
        # Middle line (B4 in treble clef) is at y = STAFF_MARGIN_TOP + 2 * STAFF_LINE_SPACING
        middle_line_y = STAFF_MARGIN_TOP + 2 * STAFF_LINE_SPACING
        
        # Calculate y position based on pitch
        # Each half step is STAFF_LINE_SPACING / 2
        pitch_offset = self._pitch_to_offset(position.pitch, position.octave)
        y = middle_line_y - pitch_offset * (STAFF_LINE_SPACING / 2)
        
        # Calculate x position based on measure and note index
        x = (STAFF_MARGIN_LEFT + 
             position.measure_index * MEASURE_WIDTH + 
             NOTE_WIDTH + 
             position.note_index * (NOTE_WIDTH + 10))
        
        note.setPos(x, y)
        position.x = x
        position.y = y
        
        self.addItem(note)
        self._notes.append(note)
        
        return note
    
    def _pitch_to_offset(self, pitch: str, octave: int) -> int:
        """
        Convert a pitch to a staff position offset from middle line (B4).
        
        Returns offset in half-steps (positive = higher).
        """
        # Map pitch names to semitones from C
        pitch_map = {
            'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
        }
        
        # Parse pitch name and accidental
        base_pitch = pitch[0].upper()
        accidental = 0
        if len(pitch) > 1:
            if '#' in pitch:
                accidental = pitch.count('#')
            elif 'b' in pitch:
                accidental = -pitch.count('b')
        
        # Calculate semitones from C4
        semitones = pitch_map.get(base_pitch, 0) + accidental + (octave - 4) * 12
        
        # B4 is 11 semitones from C4, and is our middle line
        # So offset from B4:
        offset = semitones - 11
        
        # Convert to diatonic steps (roughly - staff positions)
        # This is simplified; real implementation would be more precise
        return offset
    
    def get_notes(self) -> list[NoteItem]:
        """Get all note items."""
        return self._notes.copy()


class InteractiveScoreEditor(QWidget):
    """
    Widget for interactive score editing.
    
    Features:
    - Visual staff display
    - Click to select notes
    - Drag notes up/down to change pitch
    - Keyboard shortcuts (arrows to move pitch, delete to remove)
    - Toolbar for note input
    
    Signals:
        note_changed: Emitted when a note is modified
        score_modified: Emitted when any change is made
    """
    
    note_changed = Signal(object, str, object)  # NotePosition, change_type, new_value
    score_modified = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._selected_note: Optional[NoteItem] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        # Note input mode
        toolbar.addWidget(QLabel(" Mode: "))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Select", "Add Note", "Add Rest"])
        toolbar.addWidget(self.mode_combo)
        
        toolbar.addSeparator()
        
        # Duration selector
        toolbar.addWidget(QLabel(" Duration: "))
        self.duration_combo = QComboBox()
        self.duration_combo.addItems([
            "Whole (w)", "Half (h)", "Quarter (q)", 
            "Eighth (e)", "Sixteenth (s)"
        ])
        self.duration_combo.setCurrentIndex(2)  # Quarter
        toolbar.addWidget(self.duration_combo)
        
        toolbar.addSeparator()
        
        # Octave selector
        toolbar.addWidget(QLabel(" Octave: "))
        self.octave_spin = QSpinBox()
        self.octave_spin.setRange(1, 8)
        self.octave_spin.setValue(4)
        toolbar.addWidget(self.octave_spin)
        
        toolbar.addSeparator()
        
        # Action buttons
        self.delete_btn = QPushButton("🗑 Delete")
        self.delete_btn.clicked.connect(self._on_delete_note)
        toolbar.addWidget(self.delete_btn)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._on_clear_all)
        toolbar.addWidget(self.clear_btn)
        
        layout.addWidget(toolbar)
        
        # Graphics view
        self.scene = InteractiveScoreScene()
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        layout.addWidget(self.view, 1)
        
        # Instructions label
        self.instructions = QLabel(
            "💡 Click notes to select | Drag up/down to change pitch | "
            "Arrow keys: ↑↓ = change pitch | Delete = remove note"
        )
        self.instructions.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        layout.addWidget(self.instructions)
        
        # Draw initial staff
        self.scene.draw_staff(4)
    
    def _connect_signals(self):
        """Connect signals."""
        self.scene.note_pitch_changed.connect(self._on_note_pitch_changed)
        self.scene.note_selected.connect(self._on_note_selected)
        self.view.viewport().installEventFilter(self)
    
    def _on_note_pitch_changed(self, position: NotePosition, offset: int):
        """Handle note pitch change from drag."""
        logger.info(f"Note pitch changed: {position.pitch}{position.octave} offset={offset}")
        self.note_changed.emit(position, "pitch", offset)
        self.score_modified.emit()
    
    def _on_note_selected(self, position: NotePosition):
        """Handle note selection."""
        logger.info(f"Note selected: {position.pitch}{position.octave}")
    
    def _on_delete_note(self):
        """Delete selected note."""
        # Find selected items
        for item in self.scene.selectedItems():
            if isinstance(item, NoteItem):
                self.scene.note_deleted.emit(item.position)
                self.scene.removeItem(item)
                self.scene._notes.remove(item)
        
        self.score_modified.emit()
    
    def _on_clear_all(self):
        """Clear all notes."""
        self.scene.clear_score()
        self.scene.draw_staff(4)
        self.score_modified.emit()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self._on_delete_note()
        elif event.key() == Qt.Key.Key_Up:
            self._move_selected_notes(1)
        elif event.key() == Qt.Key.Key_Down:
            self._move_selected_notes(-1)
        else:
            super().keyPressEvent(event)
    
    def _move_selected_notes(self, direction: int):
        """Move selected notes up or down by one step."""
        for item in self.scene.selectedItems():
            if isinstance(item, NoteItem):
                # Move by half a staff line (one half step)
                new_y = item.y() - direction * (STAFF_LINE_SPACING / 2)
                item.setY(new_y)
                item._pitch_offset += direction
                
                self.note_changed.emit(item.position, "pitch", direction)
        
        if self.scene.selectedItems():
            self.score_modified.emit()
    
    def load_notes(self, notes: list[NotePosition]):
        """Load a list of notes into the editor."""
        self.scene.clear_score()
        
        # Calculate number of measures needed
        if notes:
            max_measure = max(n.measure_index for n in notes) + 1
        else:
            max_measure = 4
        
        self.scene.draw_staff(max(4, max_measure))
        
        for position in notes:
            self.scene.add_note(position)
    
    def get_notes(self) -> list[NotePosition]:
        """Get all notes with their current positions."""
        result = []
        for item in self.scene.get_notes():
            pos = item.position
            pos.y = item.y()  # Update with current position
            result.append(pos)
        return result
