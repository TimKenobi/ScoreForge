"""
Main entry point for ScoreForge application.
"""

import sys
from pathlib import Path


def main():
    """Main entry point for the application."""
    # Import PySide6 here to allow CLI usage without GUI
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    
    from sheet_music_scanner.gui.main_window import MainWindow
    from sheet_music_scanner.gui.theme import get_theme_manager, Theme
    from sheet_music_scanner.config import get_config
    
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("ScoreForge")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ScoreForge")
    app.setOrganizationDomain("scoreforge.app")
    
    # Apply theme (loads saved preference or uses system default)
    theme_manager = get_theme_manager()
    config = get_config()
    
    # Map config theme to Theme enum
    theme_map = {
        "dark": Theme.DARK,
        "light": Theme.LIGHT,
        "system": Theme.SYSTEM,
    }
    theme = theme_map.get(config.gui.theme, Theme.SYSTEM)
    theme_manager.set_theme(theme)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Handle file arguments
    if len(sys.argv) > 1:
        filepath = Path(sys.argv[1])
        if filepath.exists():
            window.open_file(str(filepath))
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
