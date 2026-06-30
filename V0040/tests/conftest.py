import pytest
import tempfile
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from ut_vfx.core.infra.database_manager import DatabaseManager
from ut_vfx.core.infra.config_manager import ConfigManager

@pytest.fixture
def temp_vfx_root():
    """Creates a temporary VFX Project Root structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Standard Structure
        (root / "01_Admin").mkdir()
        (root / "05_Reels").mkdir()
        (root / "Incoming").mkdir()
        
        yield root

@pytest.fixture
def mock_db(temp_vfx_root):
    """Creates a localized database manager that doesn't touch the real system DB."""
    db_path = temp_vfx_root / "test_ut_vfx.db"
    
    # Initialize Manager
    # We patch the class to use our temp path
    mgr = DatabaseManager()
    mgr.db_path = db_path
    mgr._initialize_database()
    
    yield mgr
    
    # mgr.close() # Method does not exist

@pytest.fixture
def mock_config(temp_vfx_root):
    """Creates a config manager pointing to temp paths."""
    cm = ConfigManager()
    # Override global paths if necessary
    # cm.global_settings['project_root'] = str(temp_vfx_root)
    yield cm

import os

@pytest.fixture(autouse=True)
def mock_gui_dialogs(monkeypatch):
    """
    Mock blocking GUI components for headless testing.
    This prevents tests from hanging when QMessageBox or QFileDialog is called.
    """
    os.environ["HEADLESS_TESTING"] = "1"
    
    try:
        from PySide6.QtWidgets import QMessageBox, QFileDialog, QProgressDialog, QDialog
        
        # Mock QMessageBox methods
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        
        # Mock QFileDialog methods
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/mock/path/file.txt", ""))
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: ("/mock/path/file.txt", ""))
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: "/mock/path/dir")
        
        # Mock QDialog exec (note: QDialog.DialogCode.Accepted is used, but for simplicity we return 1 which is the int value of Accepted)
        monkeypatch.setattr(QDialog, "exec", lambda *args, **kwargs: 1)
        
    except ImportError:
        pass
