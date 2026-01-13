"""
Transpose Dialog - Dialog for transposing scores.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QRadioButton, QSpinBox,
    QButtonGroup, QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt

from sheet_music_scanner.core.operations import (
    get_interval_options,
    get_available_keys,
)


class TransposeDialog(QDialog):
    """
    Dialog for transposing a score.
    
    Provides options for:
    - Transpose by interval (e.g., perfect fifth)
    - Transpose by semitones
    - Transpose to a specific key
    """
    
    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent)
        
        self.setWindowTitle("Transpose Score")
        self.setModal(True)
        self.setMinimumWidth(350)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Method selection
        method_group = QGroupBox("Transpose Method")
        method_layout = QVBoxLayout(method_group)
        
        self.method_group = QButtonGroup(self)
        
        # By interval
        self.interval_radio = QRadioButton("By interval")
        self.interval_radio.setChecked(True)
        self.method_group.addButton(self.interval_radio, 0)
        method_layout.addWidget(self.interval_radio)
        
        interval_layout = QHBoxLayout()
        interval_layout.addSpacing(20)
        self.interval_combo = QComboBox()
        for code, name in get_interval_options():
            self.interval_combo.addItem(name, code)
        interval_layout.addWidget(self.interval_combo)
        method_layout.addLayout(interval_layout)
        
        # By semitones
        self.semitones_radio = QRadioButton("By semitones")
        self.method_group.addButton(self.semitones_radio, 1)
        method_layout.addWidget(self.semitones_radio)
        
        semitones_layout = QHBoxLayout()
        semitones_layout.addSpacing(20)
        self.semitones_spin = QSpinBox()
        self.semitones_spin.setMinimum(-24)
        self.semitones_spin.setMaximum(24)
        self.semitones_spin.setValue(0)
        semitones_layout.addWidget(self.semitones_spin)
        semitones_layout.addWidget(QLabel("semitones"))
        semitones_layout.addStretch()
        method_layout.addLayout(semitones_layout)
        
        # By key
        self.key_radio = QRadioButton("To key")
        self.method_group.addButton(self.key_radio, 2)
        method_layout.addWidget(self.key_radio)
        
        key_layout = QHBoxLayout()
        key_layout.addSpacing(20)
        self.key_combo = QComboBox()
        for key_name in get_available_keys():
            self.key_combo.addItem(key_name)
        key_layout.addWidget(self.key_combo)
        method_layout.addLayout(key_layout)
        
        layout.addWidget(method_group)
        
        # Enable/disable based on selection
        self.interval_radio.toggled.connect(
            lambda checked: self.interval_combo.setEnabled(checked)
        )
        self.semitones_radio.toggled.connect(
            lambda checked: self.semitones_spin.setEnabled(checked)
        )
        self.key_radio.toggled.connect(
            lambda checked: self.key_combo.setEnabled(checked)
        )
        
        # Initial state
        self.semitones_spin.setEnabled(False)
        self.key_combo.setEnabled(False)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_interval(self) -> str:
        """
        Get the selected transposition interval.
        
        Returns:
            Interval string for use with Score.transpose()
        """
        method = self.method_group.checkedId()
        
        if method == 0:  # By interval
            return self.interval_combo.currentData()
        elif method == 1:  # By semitones
            semitones = self.semitones_spin.value()
            return str(semitones)
        else:  # By key
            return f"KEY:{self.key_combo.currentText()}"
    
    def get_method(self) -> str:
        """
        Get the selected transposition method.
        
        Returns:
            "interval", "semitones", or "key"
        """
        method = self.method_group.checkedId()
        return ["interval", "semitones", "key"][method]
