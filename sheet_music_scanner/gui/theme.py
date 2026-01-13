"""
Theme Manager - Provides light and dark themes for the application.

Supports system theme detection and manual theme switching.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
import logging

from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


class Theme(Enum):
    """Available application themes."""
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


# Dark theme color palette
DARK_PALETTE = {
    "window": "#1e1e1e",
    "window_text": "#ffffff",
    "base": "#252526",
    "alternate_base": "#2d2d30",
    "text": "#ffffff",
    "button": "#3c3c3c",
    "button_text": "#ffffff",
    "bright_text": "#ff0000",
    "highlight": "#0078d4",
    "highlight_text": "#ffffff",
    "link": "#3794ff",
    "disabled_text": "#808080",
    "disabled_button_text": "#6d6d6d",
    "tooltip_base": "#2d2d30",
    "tooltip_text": "#ffffff",
    "placeholder_text": "#808080",
    # Custom colors for specific widgets
    "panel_background": "#252526",
    "panel_border": "#3c3c3c",
    "input_background": "#1e1e1e",
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "info": "#2196f3",
}

# Light theme color palette
LIGHT_PALETTE = {
    "window": "#f5f5f5",
    "window_text": "#1e1e1e",
    "base": "#ffffff",
    "alternate_base": "#f0f0f0",
    "text": "#1e1e1e",
    "button": "#e1e1e1",
    "button_text": "#1e1e1e",
    "bright_text": "#ff0000",
    "highlight": "#0078d4",
    "highlight_text": "#ffffff",
    "link": "#0066cc",
    "disabled_text": "#a0a0a0",
    "disabled_button_text": "#a0a0a0",
    "tooltip_base": "#ffffdc",
    "tooltip_text": "#1e1e1e",
    "placeholder_text": "#a0a0a0",
    # Custom colors for specific widgets
    "panel_background": "#ffffff",
    "panel_border": "#e0e0e0",
    "input_background": "#ffffff",
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "info": "#2196f3",
}


class ThemeManager:
    """
    Manages application themes.
    
    Provides methods for:
    - Applying light/dark themes
    - Detecting system theme preference
    - Persisting theme choice
    - Getting theme-aware colors
    """
    
    _instance: Optional["ThemeManager"] = None
    _current_theme: Theme = Theme.SYSTEM
    _palette: dict = LIGHT_PALETTE
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_saved_theme()
    
    def _load_saved_theme(self):
        """Load saved theme preference."""
        settings = QSettings("SheetMusicScanner", "SheetMusicScanner")
        theme_str = settings.value("theme", "system")
        
        try:
            self._current_theme = Theme(theme_str)
        except ValueError:
            self._current_theme = Theme.SYSTEM
    
    def save_theme(self):
        """Save current theme preference."""
        settings = QSettings("SheetMusicScanner", "SheetMusicScanner")
        settings.setValue("theme", self._current_theme.value)
    
    @property
    def current_theme(self) -> Theme:
        """Get the current theme."""
        return self._current_theme
    
    @property
    def is_dark(self) -> bool:
        """Check if the current effective theme is dark."""
        if self._current_theme == Theme.DARK:
            return True
        elif self._current_theme == Theme.LIGHT:
            return False
        else:
            # System theme - detect
            return self._detect_system_dark_mode()
    
    def _detect_system_dark_mode(self) -> bool:
        """Detect if system is using dark mode."""
        try:
            # Try to detect macOS dark mode
            from subprocess import run, PIPE
            result = run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip().lower() == "dark"
        except Exception:
            # Fallback: check palette brightness
            app = QApplication.instance()
            if app:
                palette = app.palette()
                bg = palette.color(QPalette.ColorRole.Window)
                # If background is dark (low luminance), assume dark mode
                luminance = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
                return luminance < 128
            return False
    
    def set_theme(self, theme: Theme):
        """
        Set the application theme.
        
        Args:
            theme: Theme to apply
        """
        self._current_theme = theme
        self._apply_theme()
        self.save_theme()
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        if self.is_dark:
            self.set_theme(Theme.LIGHT)
        else:
            self.set_theme(Theme.DARK)
    
    def _apply_theme(self):
        """Apply the current theme to the application."""
        app = QApplication.instance()
        if not app:
            return
        
        # Use Fusion style for consistent theming
        app.setStyle(QStyleFactory.create("Fusion"))
        
        if self.is_dark:
            self._palette = DARK_PALETTE
            palette = self._create_dark_palette()
        else:
            self._palette = LIGHT_PALETTE
            palette = self._create_light_palette()
        
        app.setPalette(palette)
        
        # Apply stylesheet for additional customization
        stylesheet = self._get_stylesheet()
        app.setStyleSheet(stylesheet)
        
        logger.info(f"Applied {'dark' if self.is_dark else 'light'} theme")
    
    def _create_dark_palette(self) -> QPalette:
        """Create a dark color palette."""
        palette = QPalette()
        p = DARK_PALETTE
        
        palette.setColor(QPalette.ColorRole.Window, QColor(p["window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(p["window_text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(p["base"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(p["alternate_base"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(p["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(p["button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(p["button_text"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(p["bright_text"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(p["highlight"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(p["highlight_text"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(p["link"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(p["tooltip_base"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(p["tooltip_text"]))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(p["placeholder_text"]))
        
        # Disabled colors
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Text,
            QColor(p["disabled_text"])
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(p["disabled_button_text"])
        )
        
        return palette
    
    def _create_light_palette(self) -> QPalette:
        """Create a light color palette."""
        palette = QPalette()
        p = LIGHT_PALETTE
        
        palette.setColor(QPalette.ColorRole.Window, QColor(p["window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(p["window_text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(p["base"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(p["alternate_base"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(p["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(p["button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(p["button_text"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(p["bright_text"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(p["highlight"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(p["highlight_text"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(p["link"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(p["tooltip_base"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(p["tooltip_text"]))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(p["placeholder_text"]))
        
        # Disabled colors
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Text,
            QColor(p["disabled_text"])
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(p["disabled_button_text"])
        )
        
        return palette
    
    def _get_stylesheet(self) -> str:
        """Get the stylesheet for additional customization."""
        p = self._palette
        
        return f"""
            /* Scrollbars */
            QScrollBar:vertical {{
                background: {p["base"]};
                width: 12px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {p["button"]};
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {p["highlight"]};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            
            QScrollBar:horizontal {{
                background: {p["base"]};
                height: 12px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {p["button"]};
                min-width: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {p["highlight"]};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            
            /* Tool tips */
            QToolTip {{
                background-color: {p["tooltip_base"]};
                color: {p["tooltip_text"]};
                border: 1px solid {p["panel_border"]};
                padding: 4px;
                border-radius: 4px;
            }}
            
            /* Menu */
            QMenu {{
                background-color: {p["base"]};
                border: 1px solid {p["panel_border"]};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {p["highlight"]};
                color: {p["highlight_text"]};
            }}
            QMenu::separator {{
                height: 1px;
                background: {p["panel_border"]};
                margin: 4px 8px;
            }}
            
            /* Tabs */
            QTabWidget::pane {{
                border: 1px solid {p["panel_border"]};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {p["button"]};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {p["highlight"]};
                color: {p["highlight_text"]};
            }}
            
            /* Group boxes */
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {p["panel_border"]};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
            
            /* Splitter */
            QSplitter::handle {{
                background: {p["panel_border"]};
            }}
            QSplitter::handle:horizontal {{
                width: 2px;
            }}
            QSplitter::handle:vertical {{
                height: 2px;
            }}
            
            /* Status bar */
            QStatusBar {{
                background: {p["window"]};
                border-top: 1px solid {p["panel_border"]};
            }}
            
            /* Text inputs */
            QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {{
                background: {p["input_background"]};
                border: 1px solid {p["panel_border"]};
                border-radius: 4px;
                padding: 4px;
                color: {p["text"]};
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus {{
                border-color: {p["highlight"]};
            }}
            
            /* Combo boxes */
            QComboBox {{
                background: {p["button"]};
                border: 1px solid {p["panel_border"]};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox:hover {{
                border-color: {p["highlight"]};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            /* Spin boxes */
            QSpinBox, QDoubleSpinBox {{
                background: {p["input_background"]};
                border: 1px solid {p["panel_border"]};
                border-radius: 4px;
                padding: 4px;
            }}
            
            /* Buttons */
            QPushButton {{
                background: {p["button"]};
                border: 1px solid {p["panel_border"]};
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background: {p["highlight"]};
                color: {p["highlight_text"]};
            }}
            QPushButton:pressed {{
                background: {p["highlight"]};
            }}
            QPushButton:disabled {{
                background: {p["alternate_base"]};
                color: {p["disabled_text"]};
            }}
            
            /* Primary buttons */
            QPushButton[primary="true"] {{
                background: {p["highlight"]};
                color: {p["highlight_text"]};
                border: none;
            }}
            QPushButton[primary="true"]:hover {{
                background: #1a8ad4;
            }}
            
            /* Tool buttons */
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
            }}
            QToolButton:hover {{
                background: {p["button"]};
                border-color: {p["panel_border"]};
            }}
            QToolButton:pressed {{
                background: {p["highlight"]};
            }}
            
            /* Frames */
            QFrame[frameShape="4"] {{ /* StyledPanel */
                background: {p["panel_background"]};
                border: 1px solid {p["panel_border"]};
                border-radius: 4px;
            }}
            
            /* Dock widgets */
            QDockWidget {{
                color: {p["text"]};
            }}
            QDockWidget::title {{
                background: {p["button"]};
                padding: 6px;
                border-bottom: 1px solid {p["panel_border"]};
            }}
            
            /* List widgets */
            QListWidget, QListView {{
                background: {p["base"]};
                border: 1px solid {p["panel_border"]};
                border-radius: 4px;
            }}
            QListWidget::item, QListView::item {{
                padding: 4px;
            }}
            QListWidget::item:selected, QListView::item:selected {{
                background: {p["highlight"]};
                color: {p["highlight_text"]};
            }}
            QListWidget::item:hover, QListView::item:hover {{
                background: {p["alternate_base"]};
            }}
            
            /* Toolbar */
            QToolBar {{
                background: {p["window"]};
                border-bottom: 1px solid {p["panel_border"]};
                spacing: 4px;
                padding: 2px;
            }}
        """
    
    def get_color(self, name: str) -> str:
        """
        Get a theme color by name.
        
        Args:
            name: Color name (e.g., "success", "warning", "error")
            
        Returns:
            Color as hex string
        """
        return self._palette.get(name, "#ffffff")


def get_theme_manager() -> ThemeManager:
    """Get the singleton ThemeManager instance."""
    return ThemeManager()


def apply_theme(theme: Theme = Theme.SYSTEM):
    """
    Apply a theme to the application.
    
    Args:
        theme: Theme to apply (default: SYSTEM)
    """
    manager = get_theme_manager()
    manager.set_theme(theme)


def is_dark_mode() -> bool:
    """Check if currently using dark mode."""
    return get_theme_manager().is_dark
