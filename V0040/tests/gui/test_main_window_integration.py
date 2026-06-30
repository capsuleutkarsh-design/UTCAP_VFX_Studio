"""
GUI Integration Tests for the Main Window.

This suite uses 'pytest-qt' to launch the actual application window in a safe, controlled environment.
It verifies:
1. Application Startup: Ensures the window appears and title is correct.
2. Tab Navigation: Simulates clicking between 'Project', 'Ingest', and 'Stock' tabs.
3. Widget States: Checks that default buttons and labels are present.
"""

import pytest
import sys
from pathlib import Path

# --- FIX FOR DIRECT EXECUTION ---
# If running as script, add project root to path
if __name__ == "__main__":
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    sys.path.insert(0, str(project_root))
# -------------------------------
else:
    # If running via pytest from root, it might work, but safer to force it
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


# Import Main Window
from ut_vfx.gui.main_window import VFXFolderCreatorApp

@pytest.fixture
def app(qtbot):
    """Fixture to launch the application."""
    # Note: user_data=None defaults to "Developer" role in main_window.py
    window = VFXFolderCreatorApp(user_data={'role': 'Developer', 'username': 'test_dev'})
    qtbot.addWidget(window)
    return window

def test_app_launch(app):
    """Smoke Test: Does the app launch?"""
    assert app.isVisible() is False # checking before show
    app.show()
    assert app.isVisible() is True
    assert "UT_VFX" in app.windowTitle()

def test_tab_switching(app, qtbot):
    """Verify that changing the workflow dropdown changes the visible tab/sidebar item."""
    app.show()
    
    # Default is Index 0 (Standard/Excel)
    assert app.mode_selector.currentIndex() == 0
    
    # Check if "Folder Creator" item is visible and text is correct
    folder_item = None
    for entry in app.nav_items:
        if "Folder Creator" in entry['item'].text() or "Auto-Build" in entry['item'].text():
            folder_item = entry['item']
            break
            
    assert folder_item is not None
    assert "Folder Creator" in folder_item.text()
    assert folder_item.isHidden() is False
    
    # Switch to Auto-Scan (Index 1)
    app.mode_selector.setCurrentIndex(1)
    
    # Assert Item text changes
    assert "Auto-Build & Move" in folder_item.text()
    assert folder_item.isHidden() is False
    
    # Switch to Incoming Delivery (Index 2)
    app.mode_selector.setCurrentIndex(2)
    
    # Assert Folder Creator item is hidden
    assert folder_item.isHidden() is True
    
    # Assert Incoming item is shown
    inc_item = None
    for entry in app.nav_items:
        if "Incoming Delivery" in entry['item'].text():
            inc_item = entry['item']
            break
    assert inc_item is not None
    assert inc_item.isHidden() is False

def test_stock_browser_load(app, qtbot):
    """Verify Stock Browser Tab initializes."""
    app.show()
    
    # Find Stock Tab in Sidebar
    stock_row = -1
    for i in range(app.sidebar_nav.count()):
        item = app.sidebar_nav.item(i)
        if "Stock Viewer" in item.text():
            stock_row = i
            break
            
    assert stock_row != -1, "Stock Browser Item not found"
    
    # Simulate Click
    app.sidebar_nav.setCurrentRow(stock_row)
    assert app.content_stack.currentIndex() == stock_row
    
    # Check widget existence
    stock_tab = app.content_stack.widget(stock_row)
    assert stock_tab is not None

# --- ENTRY POINT ---
if __name__ == "__main__":
    # If run directly, invoke pytest on self
    sys.exit(pytest.main([__file__]))
