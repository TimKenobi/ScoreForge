"""
Score View - Widget for displaying musical scores using Verovio.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, Union
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QSpinBox, QTextBrowser, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QWheelEvent

# Try to import QWebEngineView, fall back to QTextBrowser if not available
WEBENGINE_AVAILABLE = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = None  # type: ignore

from sheet_music_scanner.core.score import Score
from sheet_music_scanner.config import get_config
from sheet_music_scanner.gui.theme import get_theme_manager

logger = logging.getLogger(__name__)


class ScoreView(QWidget):
    """
    Widget for displaying musical scores.
    
    Uses Verovio to render MusicXML as SVG, displayed in a QWebEngineView.
    Supports zoom and page navigation.
    """
    
    # Signals
    note_selected = Signal(int, int, float)  # part_index, measure, beat
    page_changed = Signal(int)  # current page
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.config = get_config()
        self._score: Optional[Score] = None
        self._current_page: int = 1
        self._total_pages: int = 1
        self._zoom: float = 1.0
        self._verovio_available: bool = False
        self._svg_cache: dict = {}  # page -> svg content
        
        self._setup_ui()
        self._check_verovio()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create appropriate view widget based on availability
        if WEBENGINE_AVAILABLE:
            # Web view for SVG rendering
            self.web_view = QWebEngineView()
            self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            layout.addWidget(self.web_view, 1)
            self._using_webengine = True
        else:
            # Fallback to QTextBrowser (supports basic HTML)
            logger.warning("QWebEngineView not available, using QTextBrowser fallback")
            self.web_view = QTextBrowser()
            self.web_view.setOpenExternalLinks(False)
            self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self.web_view, 1)
            self._using_webengine = False
        
        # Page navigation bar
        nav_bar = QFrame()
        nav_bar.setFrameShape(QFrame.Shape.StyledPanel)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        
        # Previous page button
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._on_prev_page)
        nav_layout.addWidget(self.prev_btn)
        
        nav_layout.addStretch()
        
        # Page indicator
        self.page_label = QLabel("Page 1 of 1")
        nav_layout.addWidget(self.page_label)
        
        # Page spinner
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.valueChanged.connect(self._on_page_spin_changed)
        nav_layout.addWidget(self.page_spin)
        
        nav_layout.addStretch()
        
        # Next page button
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._on_next_page)
        nav_layout.addWidget(self.next_btn)
        
        layout.addWidget(nav_bar)
        
        # Show placeholder
        self._show_placeholder()
    
    def _check_verovio(self):
        """Check if Verovio is available."""
        try:
            import verovio
            self._verovio_available = True
            logger.info("Verovio is available")
        except ImportError:
            self._verovio_available = False
            logger.warning("Verovio not installed. Using fallback display.")
    
    def _get_theme_colors(self):
        """Get current theme colors for HTML rendering."""
        tm = get_theme_manager()
        if tm.is_dark:
            return {
                'bg': '#1e1e1e',
                'fg': '#ffffff',
                'muted': '#808080',
                'panel_bg': '#252526',
                'panel_border': '#3c3c3c',
                'warning_bg': '#3c3c00',
                'warning_border': '#ffc107',
            }
        else:
            return {
                'bg': '#f5f5f5',
                'fg': '#333333',
                'muted': '#666666',
                'panel_bg': '#ffffff',
                'panel_border': '#e0e0e0',
                'warning_bg': '#fff3cd',
                'warning_border': '#ffc107',
            }

    def _show_placeholder(self):
        """Show placeholder when no score is loaded."""
        colors = self._get_theme_colors()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: {colors['bg']};
                    color: {colors['muted']};
                }}
                .placeholder {{
                    text-align: center;
                }}
                .icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                }}
                h2 {{
                    margin: 0 0 10px 0;
                    color: {colors['fg']};
                }}
                p {{
                    margin: 0;
                }}
            </style>
        </head>
        <body>
            <div class="placeholder">
                <div class="icon">🎼</div>
                <h2>No Score Loaded</h2>
                <p>Import an image or open a MusicXML file to get started.</p>
                <p style="margin-top: 15px; font-size: 12px;">
                    Drag and drop files here, or use File → Import Image
                </p>
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)
        self._update_nav_state()
    
    def set_score(self, score: Score):
        """
        Set the score to display.
        
        Args:
            score: Score object to display
        """
        self._score = score
        self._svg_cache.clear()
        self._current_page = 1
        
        if self._verovio_available and self._using_webengine:
            self._render_with_verovio()
        else:
            self._render_fallback()
    
    def _render_with_verovio(self):
        """Render the score using Verovio."""
        if not self._score:
            return
        
        try:
            import verovio
            
            # Export score to MusicXML string
            musicxml = self._score.to_musicxml_string()
            
            # Initialize Verovio toolkit
            toolkit = verovio.toolkit()
            
            # Set options for rendering
            options = {
                "pageWidth": 2100,
                "pageHeight": 2970,
                "scale": int(40 * self._zoom),
                "adjustPageHeight": False,
                "breaks": "auto",
                "mmOutput": False,
                "footer": "none",
                "header": "none",
            }
            toolkit.setOptions(options)
            
            # Load MusicXML
            toolkit.loadData(musicxml)
            
            # Get page count
            self._total_pages = toolkit.getPageCount()
            self.page_spin.setMaximum(self._total_pages)
            
            # Render current page
            self._render_page(toolkit)
            
        except Exception as e:
            logger.exception("Error rendering with Verovio")
            self._render_fallback()
    
    def _render_page(self, toolkit=None):
        """Render a specific page."""
        if not self._score:
            return
        
        # Check cache first
        cache_key = (self._current_page, self._zoom)
        if cache_key in self._svg_cache:
            self._display_svg(self._svg_cache[cache_key])
            return
        
        try:
            import verovio
            
            if toolkit is None:
                toolkit = verovio.toolkit()
                options = {
                    "pageWidth": 2100,
                    "pageHeight": 2970,
                    "scale": int(40 * self._zoom),
                    "adjustPageHeight": False,
                }
                toolkit.setOptions(options)
                toolkit.loadData(self._score.to_musicxml_string())
            
            # Render the page
            svg = toolkit.renderToSVG(self._current_page)
            
            # Cache it
            self._svg_cache[cache_key] = svg
            
            # Display
            self._display_svg(svg)
            
        except Exception as e:
            logger.exception("Error rendering page")
    
    def _display_svg(self, svg: str):
        """Display SVG content in the web view."""
        colors = self._get_theme_colors()
        # For score display, we still want white background for readability
        # but the surrounding area should match theme
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    background: {colors['bg']};
                    min-height: 100vh;
                }}
                .score-container {{
                    background: white;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                    padding: 20px;
                }}
                svg {{
                    display: block;
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <div class="score-container">
                {svg}
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)
        self._update_nav_state()
    
    def _render_fallback(self):
        """Fallback rendering when Verovio is not available."""
        if not self._score:
            return
        
        # Determine warning message based on what's missing
        if not self._using_webengine:
            warning = """⚠️ WebEngine not available. SVG rendering disabled.<br>
            <small>Install with: <code>pip install PySide6[webengine]</code></small>"""
        elif not self._verovio_available:
            warning = """⚠️ Verovio not installed. Install for graphical notation display:<br>
            <code>pip install verovio</code>"""
        else:
            warning = ""
        
        # Create a simple text-based representation
        colors = self._get_theme_colors()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
                    padding: 20px;
                    background: {colors['bg']};
                    color: {colors['fg']};
                }}
                .info {{
                    background: {colors['panel_bg']};
                    padding: 20px;
                    border-radius: 8px;
                    max-width: 600px;
                    margin: 0 auto;
                    border: 1px solid {colors['panel_border']};
                }}
                h2 {{ margin-top: 0; color: {colors['fg']}; }}
                .warning {{
                    background: {colors['warning_bg']};
                    border: 1px solid {colors['warning_border']};
                    padding: 10px;
                    border-radius: 4px;
                    margin-bottom: 15px;
                }}
                code {{
                    background: {colors['bg']};
                    padding: 2px 6px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            <div class="info">
                <div class="warning">
                    {warning}
                </div>
                <h2>Score Information</h2>
                <p><strong>Title:</strong> {self._score.title or 'Untitled'}</p>
                <p><strong>Composer:</strong> {self._score.composer or 'Unknown'}</p>
                <p><strong>Parts:</strong> {self._score.num_parts}</p>
                <p><strong>Measures:</strong> {self._score.num_measures}</p>
                <p><strong>Key:</strong> {self._score.key_signature or 'Not specified'}</p>
                <p><strong>Time Signature:</strong> {self._score.time_signature or 'Not specified'}</p>
                <p><strong>Tempo:</strong> {self._score.tempo_bpm or 'Not specified'} BPM</p>
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)
        self._total_pages = 1
        self._update_nav_state()
    
    def _update_nav_state(self):
        """Update navigation button states."""
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)
        self.page_label.setText(f"Page {self._current_page} of {self._total_pages}")
        self.page_spin.setValue(self._current_page)
    
    def _on_prev_page(self):
        """Go to previous page."""
        if self._current_page > 1:
            self._current_page -= 1
            self._render_page()
            self.page_changed.emit(self._current_page)
    
    def _on_next_page(self):
        """Go to next page."""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._render_page()
            self.page_changed.emit(self._current_page)
    
    def _on_page_spin_changed(self, value: int):
        """Handle page spinner change."""
        if value != self._current_page and 1 <= value <= self._total_pages:
            self._current_page = value
            self._render_page()
            self.page_changed.emit(self._current_page)
    
    def zoom_in(self):
        """Increase zoom level."""
        self._zoom = min(3.0, self._zoom + 0.1)
        self._svg_cache.clear()
        if self._score:
            if self._verovio_available and self._using_webengine:
                self._render_with_verovio()
            else:
                self._render_fallback()
    
    def zoom_out(self):
        """Decrease zoom level."""
        self._zoom = max(0.3, self._zoom - 0.1)
        self._svg_cache.clear()
        if self._score:
            if self._verovio_available and self._using_webengine:
                self._render_with_verovio()
            else:
                self._render_fallback()
    
    def zoom_reset(self):
        """Reset zoom to default."""
        self._zoom = 1.0
        self._svg_cache.clear()
        if self._score:
            if self._verovio_available and self._using_webengine:
                self._render_with_verovio()
            else:
                self._render_fallback()
    
    def get_zoom(self) -> float:
        """Get current zoom level."""
        return self._zoom
    
    def set_zoom(self, zoom: float):
        """Set zoom level."""
        self._zoom = max(0.3, min(3.0, zoom))
        self._svg_cache.clear()
        if self._score:
            if self._verovio_available and self._using_webengine:
                self._render_with_verovio()
            else:
                self._render_fallback()
    
    def refresh(self):
        """Refresh the display."""
        self._svg_cache.clear()
        if self._score:
            if self._verovio_available and self._using_webengine:
                self._render_with_verovio()
            else:
                self._render_fallback()
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming with Ctrl."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
