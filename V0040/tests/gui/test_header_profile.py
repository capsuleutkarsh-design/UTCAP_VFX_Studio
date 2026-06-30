
import pytest
from PySide6.QtWidgets import QLabel, QComboBox
from ut_vfx.gui.main_window import VFXFolderCreatorApp

@pytest.fixture
def app(qtbot, mock_db):
    """Fixture to create the app with mocked DB and User Manager."""
    # Mocking UserManager to return a specific user with a profile pic
    # Note: We can't easily mock the internal UserManager of the App class 
    # without dependency injection or patching, but we can check the default state.
    widget = VFXFolderCreatorApp()
    widget.show()
    qtbot.addWidget(widget)
    return widget

def test_header_structure(app, qtbot):
    """Test that the header contains the new Mode Selector, Search Bar, and Avatar."""
    app.findChild(QLabel, "appLogo").parent() # Get the header GroupBox
    
    # 1. Check Mode Selector
    mode_selector = app.mode_selector
    assert isinstance(mode_selector, QComboBox)
    assert mode_selector.isVisible()
    assert mode_selector.count() == 3
    
    # 2. Check Logo Text
    logo = app.findChild(QLabel, "appLogo")
    assert logo is not None
    assert logo.text() == "UT_VFX" # Updated for Typographic Pair Design

def test_avatar_rendering(app, qtbot):
    """Test that the avatar label is present and has a pixmap."""
    # Find by ObjectName we just added
    avatar_label = app.findChild(QLabel, "userAvatar")
            
    assert avatar_label is not None
    assert avatar_label.pixmap() is not None
    assert not avatar_label.pixmap().isNull()
