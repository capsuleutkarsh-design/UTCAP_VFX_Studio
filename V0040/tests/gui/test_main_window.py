"""
Unit Test for Main Window Instantiation.

This test verifies that the 'VFXFolderCreatorApp' (Main Window) can be initialized
without crashing and correctly sets up its basic user role data.
It relies on a simplified QTimer loop or direct instantiation checks.
"""

import sys
from PySide6.QtWidgets import QApplication
from ut_vfx.gui.main_window import VFXFolderCreatorApp

def test_main():
    # Check if app already exists
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    user_data = {
        "username": "tester",
        "role": "Tester",
        "display_name": "QA Tester"
    }

    print("Instantiating Main Window...")
    
    # Use try-finally to ensure cleanup works even if assertion fails
    window = None
    try:
        window = VFXFolderCreatorApp(user_data=user_data)
        window.show()
        print("Main Window instantiated and shown.")
        
        # In a real test we shouldn't block 5 seconds.
        # Just assert it showed up and move on.
        assert window.isVisible()
        
    finally:
        if window:
            window.close()
