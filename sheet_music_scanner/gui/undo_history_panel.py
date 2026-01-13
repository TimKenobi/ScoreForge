"""
Undo History Panel - Visual display of undo/redo stack.

Provides a list view of all undo states with ability to jump to any state.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Callable, Any
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush


@dataclass
class UndoState:
    """Represents a single undo state."""
    index: int
    description: str
    timestamp: datetime
    data: Any  # Serialized state data
    
    @property
    def time_str(self) -> str:
        """Format timestamp as HH:MM:SS."""
        return self.timestamp.strftime("%H:%M:%S")


class UndoHistoryManager:
    """
    Manages undo/redo history with descriptions.
    
    Provides a more detailed undo system than the basic Score undo,
    with named states and ability to jump to any point.
    """
    
    def __init__(self, max_states: int = 50):
        self.max_states = max_states
        self._states: List[UndoState] = []
        self._current_index = -1
        self._state_counter = 0
        
        # Callbacks
        self._get_state_callback: Optional[Callable[[], Any]] = None
        self._set_state_callback: Optional[Callable[[Any], None]] = None
        self._change_callback: Optional[Callable[[], None]] = None
    
    def set_callbacks(
        self,
        get_state: Callable[[], Any],
        set_state: Callable[[Any], None],
        on_change: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Set callbacks for state management.
        
        Args:
            get_state: Returns current document state
            set_state: Applies a saved state
            on_change: Called when history changes
        """
        self._get_state_callback = get_state
        self._set_state_callback = set_state
        self._change_callback = on_change
    
    def save_state(self, description: str) -> None:
        """
        Save current state to history.
        
        Args:
            description: Human-readable description of the action
        """
        if not self._get_state_callback:
            return
        
        # Get current state
        data = self._get_state_callback()
        
        # Remove any states after current position (new branch)
        if self._current_index < len(self._states) - 1:
            self._states = self._states[:self._current_index + 1]
        
        # Create new state
        state = UndoState(
            index=self._state_counter,
            description=description,
            timestamp=datetime.now(),
            data=data
        )
        self._state_counter += 1
        
        # Add to history
        self._states.append(state)
        self._current_index = len(self._states) - 1
        
        # Trim old states
        if len(self._states) > self.max_states:
            self._states = self._states[-self.max_states:]
            self._current_index = len(self._states) - 1
        
        if self._change_callback:
            self._change_callback()
    
    def undo(self) -> bool:
        """
        Undo to previous state.
        
        Returns:
            True if undo was performed
        """
        if not self.can_undo():
            return False
        
        self._current_index -= 1
        self._apply_current_state()
        
        if self._change_callback:
            self._change_callback()
        
        return True
    
    def redo(self) -> bool:
        """
        Redo to next state.
        
        Returns:
            True if redo was performed
        """
        if not self.can_redo():
            return False
        
        self._current_index += 1
        self._apply_current_state()
        
        if self._change_callback:
            self._change_callback()
        
        return True
    
    def jump_to(self, index: int) -> bool:
        """
        Jump to a specific state by list index.
        
        Args:
            index: Index in states list
            
        Returns:
            True if jump was performed
        """
        if index < 0 or index >= len(self._states):
            return False
        
        self._current_index = index
        self._apply_current_state()
        
        if self._change_callback:
            self._change_callback()
        
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._current_index > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._current_index < len(self._states) - 1
    
    @property
    def states(self) -> List[UndoState]:
        """Get all states."""
        return self._states.copy()
    
    @property
    def current_index(self) -> int:
        """Get current state index."""
        return self._current_index
    
    def _apply_current_state(self) -> None:
        """Apply the current state."""
        if self._set_state_callback and 0 <= self._current_index < len(self._states):
            state = self._states[self._current_index]
            self._set_state_callback(state.data)
    
    def clear(self) -> None:
        """Clear all history."""
        self._states.clear()
        self._current_index = -1
        
        if self._change_callback:
            self._change_callback()


class UndoHistoryPanel(QWidget):
    """
    Visual panel displaying undo/redo history.
    
    Features:
    - List of all undo states with descriptions
    - Click to jump to any state
    - Current state highlighted
    - Time stamps for each state
    """
    
    # Signals
    state_selected = Signal(int)  # Index of selected state
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._manager: Optional[UndoHistoryManager] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("History")
        title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(50)
        self.clear_btn.clicked.connect(self._on_clear)
        header_layout.addWidget(self.clear_btn)
        
        layout.addLayout(header_layout)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)
        
        # State list
        self.state_list = QListWidget()
        self.state_list.setAlternatingRowColors(True)
        self.state_list.itemClicked.connect(self._on_item_clicked)
        self.state_list.setStyleSheet("""
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #ecf0f1;
            }
        """)
        layout.addWidget(self.state_list)
        
        # Undo/Redo buttons
        button_layout = QHBoxLayout()
        
        self.undo_btn = QPushButton("← Undo")
        self.undo_btn.clicked.connect(self._on_undo)
        button_layout.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton("Redo →")
        self.redo_btn.clicked.connect(self._on_redo)
        button_layout.addWidget(self.redo_btn)
        
        layout.addLayout(button_layout)
        
        # Info label
        self.info_label = QLabel("No history")
        self.info_label.setStyleSheet("color: gray; font-size: 11px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
        self._update_buttons()
    
    def set_manager(self, manager: UndoHistoryManager) -> None:
        """Set the undo history manager."""
        self._manager = manager
        self._manager.set_callbacks(
            get_state=self._manager._get_state_callback,
            set_state=self._manager._set_state_callback,
            on_change=self._refresh_list
        )
        self._refresh_list()
    
    def _refresh_list(self) -> None:
        """Refresh the state list."""
        self.state_list.clear()
        
        if not self._manager:
            return
        
        states = self._manager.states
        current = self._manager.current_index
        
        for i, state in enumerate(states):
            # Format item text
            text = f"{state.time_str} - {state.description}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            # Highlight current state
            if i == current:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setText(f"► {text}")
            elif i > current:
                # Future states (available for redo) - gray
                item.setForeground(QBrush(QColor(128, 128, 128)))
            
            self.state_list.addItem(item)
        
        # Select current item
        if 0 <= current < self.state_list.count():
            self.state_list.setCurrentRow(current)
        
        # Update info
        self.info_label.setText(f"{len(states)} states, current: {current + 1}")
        
        self._update_buttons()
    
    def _update_buttons(self) -> None:
        """Update button enabled states."""
        if not self._manager:
            self.undo_btn.setEnabled(False)
            self.redo_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            return
        
        self.undo_btn.setEnabled(self._manager.can_undo())
        self.redo_btn.setEnabled(self._manager.can_redo())
        self.clear_btn.setEnabled(len(self._manager.states) > 0)
    
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item click - jump to state."""
        if not self._manager:
            return
        
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is not None:
            self._manager.jump_to(index)
            self.state_selected.emit(index)
    
    def _on_undo(self) -> None:
        """Handle undo button click."""
        if self._manager:
            self._manager.undo()
    
    def _on_redo(self) -> None:
        """Handle redo button click."""
        if self._manager:
            self._manager.redo()
    
    def _on_clear(self) -> None:
        """Handle clear button click."""
        if self._manager:
            self._manager.clear()
