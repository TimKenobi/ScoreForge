"""
Template Dialog - GUI for selecting and creating templates.

Provides template selection, preview, and custom template creation.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QTextEdit, QSplitter,
    QWidget, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, Signal

from sheet_music_scanner.core.templates import (
    get_template_manager, ScoreTemplate, PartTemplate, TemplateCategory
)


class TemplateDialog(QDialog):
    """
    Dialog for selecting a score template.
    
    Features:
    - Browse built-in templates by category
    - Preview template structure
    - Create custom templates
    - Save current score as template
    """
    
    # Signals
    template_selected = Signal(object)  # ScoreTemplate
    
    def __init__(self, parent=None, current_score=None):
        super().__init__(parent)
        
        self.setWindowTitle("Score Templates")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)
        
        self._manager = get_template_manager()
        self._selected_template: Optional[ScoreTemplate] = None
        self._current_score = current_score
        
        self._setup_ui()
        self._populate_templates()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        
        # Browse tab
        browse_tab = self._create_browse_tab()
        tabs.addTab(browse_tab, "📋 Browse Templates")
        
        # Create tab
        create_tab = self._create_create_tab()
        tabs.addTab(create_tab, "➕ Create Template")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        self.use_btn = QPushButton("Use Template")
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._on_use_template)
        button_layout.addWidget(self.use_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_browse_tab(self) -> QWidget:
        """Create the browse templates tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left: Category and template list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Category filter
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("All", None)
        for cat in TemplateCategory:
            self.category_combo.addItem(cat.value, cat)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        category_layout.addWidget(self.category_combo, 1)
        
        left_layout.addLayout(category_layout)
        
        # Template list
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        self.template_list.itemDoubleClicked.connect(self._on_use_template)
        left_layout.addWidget(self.template_list)
        
        # Right: Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Preview header
        preview_header = QLabel("Template Preview")
        preview_header.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(preview_header)
        
        # Template info
        self.preview_name = QLabel("")
        self.preview_name.setStyleSheet("font-size: 14px; font-weight: bold;")
        right_layout.addWidget(self.preview_name)
        
        self.preview_desc = QLabel("")
        self.preview_desc.setWordWrap(True)
        right_layout.addWidget(self.preview_desc)
        
        # Template details
        details_group = QGroupBox("Settings")
        details_layout = QFormLayout(details_group)
        
        self.preview_time = QLabel("")
        details_layout.addRow("Time Signature:", self.preview_time)
        
        self.preview_key = QLabel("")
        details_layout.addRow("Key Signature:", self.preview_key)
        
        self.preview_tempo = QLabel("")
        details_layout.addRow("Tempo:", self.preview_tempo)
        
        right_layout.addWidget(details_group)
        
        # Parts list
        parts_group = QGroupBox("Parts")
        parts_layout = QVBoxLayout(parts_group)
        
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(3)
        self.parts_table.setHorizontalHeaderLabels(["Part Name", "Clef", "Instrument"])
        self.parts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.parts_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        parts_layout.addWidget(self.parts_table)
        
        right_layout.addWidget(parts_group)
        
        # Add panels to splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 400])
        
        layout.addWidget(splitter)
        
        return widget
    
    def _create_create_tab(self) -> QWidget:
        """Create the custom template tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Basic info
        info_group = QGroupBox("Template Information")
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Template")
        info_layout.addRow("Name:", self.name_edit)
        
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Description of this template")
        info_layout.addRow("Description:", self.desc_edit)
        
        layout.addWidget(info_group)
        
        # Settings
        settings_group = QGroupBox("Score Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.time_combo = QComboBox()
        self.time_combo.addItems(["4/4", "3/4", "2/4", "6/8", "2/2", "12/8"])
        settings_layout.addRow("Time Signature:", self.time_combo)
        
        self.key_combo = QComboBox()
        keys = [
            "C major", "G major", "D major", "A major", "E major", "B major",
            "F major", "Bb major", "Eb major", "Ab major",
            "A minor", "E minor", "D minor", "G minor", "C minor"
        ]
        self.key_combo.addItems(keys)
        settings_layout.addRow("Key Signature:", self.key_combo)
        
        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(20, 300)
        self.tempo_spin.setValue(120)
        self.tempo_spin.setSuffix(" BPM")
        settings_layout.addRow("Tempo:", self.tempo_spin)
        
        layout.addWidget(settings_group)
        
        # Parts
        parts_group = QGroupBox("Parts")
        parts_layout = QVBoxLayout(parts_group)
        
        self.create_parts_table = QTableWidget()
        self.create_parts_table.setColumnCount(3)
        self.create_parts_table.setHorizontalHeaderLabels(["Part Name", "Clef", "Instrument"])
        self.create_parts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        parts_layout.addWidget(self.create_parts_table)
        
        parts_btn_layout = QHBoxLayout()
        
        add_part_btn = QPushButton("Add Part")
        add_part_btn.clicked.connect(self._on_add_part)
        parts_btn_layout.addWidget(add_part_btn)
        
        remove_part_btn = QPushButton("Remove Part")
        remove_part_btn.clicked.connect(self._on_remove_part)
        parts_btn_layout.addWidget(remove_part_btn)
        
        parts_btn_layout.addStretch()
        parts_layout.addLayout(parts_btn_layout)
        
        layout.addWidget(parts_group)
        
        # Buttons
        create_btn_layout = QHBoxLayout()
        create_btn_layout.addStretch()
        
        if self._current_score:
            from_score_btn = QPushButton("Create from Current Score")
            from_score_btn.clicked.connect(self._on_create_from_score)
            create_btn_layout.addWidget(from_score_btn)
        
        save_template_btn = QPushButton("Save Template")
        save_template_btn.clicked.connect(self._on_save_template)
        create_btn_layout.addWidget(save_template_btn)
        
        layout.addLayout(create_btn_layout)
        
        # Add initial part
        self._on_add_part()
        
        return widget
    
    def _populate_templates(self):
        """Populate the template list."""
        self.template_list.clear()
        
        category = self.category_combo.currentData()
        
        if category:
            templates = self._manager.get_by_category(category)
        else:
            templates = self._manager.all_templates
        
        for template in templates:
            icon = "📄" if template.is_builtin else "📝"
            item = QListWidgetItem(f"{icon} {template.name}")
            item.setData(Qt.ItemDataRole.UserRole, template)
            item.setToolTip(template.description)
            self.template_list.addItem(item)
    
    def _on_category_changed(self):
        """Handle category filter change."""
        self._populate_templates()
    
    def _on_template_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle template selection."""
        if not current:
            self._selected_template = None
            self.use_btn.setEnabled(False)
            return
        
        template = current.data(Qt.ItemDataRole.UserRole)
        self._selected_template = template
        self.use_btn.setEnabled(True)
        
        # Update preview
        self.preview_name.setText(template.name)
        self.preview_desc.setText(template.description)
        self.preview_time.setText(template.time_signature)
        self.preview_key.setText(template.key_signature)
        self.preview_tempo.setText(f"{template.tempo_bpm} BPM")
        
        # Update parts table
        self.parts_table.setRowCount(len(template.parts))
        for i, part in enumerate(template.parts):
            self.parts_table.setItem(i, 0, QTableWidgetItem(part.name))
            self.parts_table.setItem(i, 1, QTableWidgetItem(part.clef))
            self.parts_table.setItem(i, 2, QTableWidgetItem(part.instrument or "-"))
    
    def _on_use_template(self):
        """Use the selected template."""
        if self._selected_template:
            self.template_selected.emit(self._selected_template)
            self.accept()
    
    def _on_add_part(self):
        """Add a part to the creation table."""
        row = self.create_parts_table.rowCount()
        self.create_parts_table.setRowCount(row + 1)
        
        # Name
        self.create_parts_table.setItem(row, 0, QTableWidgetItem(f"Part {row + 1}"))
        
        # Clef combo
        clef_combo = QComboBox()
        clef_combo.addItems(["treble", "bass", "alto", "tenor"])
        self.create_parts_table.setCellWidget(row, 1, clef_combo)
        
        # Instrument combo
        instr_combo = QComboBox()
        instr_combo.addItems([
            "", "Piano", "Violin", "Viola", "Violoncello",
            "Clarinet", "Trumpet", "Soprano", "Alto", "Tenor", "Bass"
        ])
        self.create_parts_table.setCellWidget(row, 2, instr_combo)
    
    def _on_remove_part(self):
        """Remove selected part from creation table."""
        row = self.create_parts_table.currentRow()
        if row >= 0:
            self.create_parts_table.removeRow(row)
    
    def _on_create_from_score(self):
        """Create template from current score."""
        if not self._current_score:
            return
        
        name = self.name_edit.text().strip() or "My Template"
        desc = self.desc_edit.text().strip()
        
        template = self._manager.create_from_score(
            self._current_score, name, desc
        )
        
        # Update UI with template info
        self.time_combo.setCurrentText(template.time_signature)
        self.key_combo.setCurrentText(template.key_signature)
        
        # Update parts table
        self.create_parts_table.setRowCount(0)
        for part in template.parts:
            self._on_add_part()
            row = self.create_parts_table.rowCount() - 1
            self.create_parts_table.item(row, 0).setText(part.name)
            
            clef_combo = self.create_parts_table.cellWidget(row, 1)
            if clef_combo:
                clef_combo.setCurrentText(part.clef)
        
        QMessageBox.information(
            self, "Template Created",
            f"Template '{name}' created from current score.\n"
            "Click 'Save Template' to save it."
        )
    
    def _on_save_template(self):
        """Save the custom template."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a template name.")
            return
        
        if self.create_parts_table.rowCount() == 0:
            QMessageBox.warning(self, "Parts Required", "Please add at least one part.")
            return
        
        # Build parts list
        parts = []
        for row in range(self.create_parts_table.rowCount()):
            name_item = self.create_parts_table.item(row, 0)
            part_name = name_item.text() if name_item else f"Part {row + 1}"
            
            clef_combo = self.create_parts_table.cellWidget(row, 1)
            clef = clef_combo.currentText() if clef_combo else "treble"
            
            instr_combo = self.create_parts_table.cellWidget(row, 2)
            instr = instr_combo.currentText() if instr_combo else ""
            
            parts.append(PartTemplate(name=part_name, clef=clef, instrument=instr))
        
        # Create template
        template = ScoreTemplate(
            name=name,
            description=self.desc_edit.text().strip(),
            category=TemplateCategory.CUSTOM,
            time_signature=self.time_combo.currentText(),
            key_signature=self.key_combo.currentText(),
            tempo_bpm=self.tempo_spin.value(),
            parts=parts,
            is_builtin=False,
        )
        
        # Save
        self._manager.add_custom_template(template)
        
        QMessageBox.information(
            self, "Template Saved",
            f"Template '{name}' has been saved."
        )
        
        # Refresh list
        self._populate_templates()
    
    def get_selected_template(self) -> Optional[ScoreTemplate]:
        """Get the selected template."""
        return self._selected_template
