"""
Unit Test for the Tester Panel.

This test verifies the standalone 'TesterPanel' widget, which provides
developer tools for debugging and manual testing within the application.
"""

import sys
from PySide6.QtWidgets import QApplication
from ut_vfx.gui.tester_panel import TesterPanel

def test_panel():
    # Check if app already exists (from another test or pytest-qt)
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    window = TesterPanel()
    window.resize(600, 400)
    window.show()
    
    # Assert window is visible
    assert window.isVisible()
    
    # Close it
    window.close()
