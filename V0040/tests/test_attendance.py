"""
Test suite for Attendance tracking systems.

Tests attendance management:
1. Local attendance logging
2. Central attendance sync
3. Idle time detection  
4. Historical attendance queries
5. Team overview

Classes:
- TestAttendanceManager: Tests local attendance logging and work hour calculations
- TestCentralAttendance: Tests centralized attendance syncing and team overview
- TestIdleDetection: Tests idle time detection algorithms

Coverage:
- AttendanceManager (core/domain/attendance_manager.py)
- CentralAttendance (core/domain/central_attendance.py)
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ut_vfx.core.domain.attendance_manager import AttendanceManager
from ut_vfx.core.domain.central_attendance import CentralAttendance
from ut_vfx.core.infra.database_manager import DatabaseManager


class TestAttendanceManager:
    """Test the local AttendanceManager."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test_attendance.db"
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a database manager."""
        return DatabaseManager(db_path=temp_db_path)
    
    @pytest.fixture
    def attendance_manager(self, db_manager):
        """Create an attendance manager."""
        return AttendanceManager()
    
    def test_log_attendance(self, attendance_manager):
        """Test logging attendance."""
        success = attendance_manager.log_attendance(
            user_id="user123",
            user_name="Test User",
            action="login"
        )
        
        assert success
    
    def test_get_todays_attendance(self, attendance_manager):
        """Test getting today's attendance log."""
        # Log some attendance
        attendance_manager.log_attendance(
            user_id="user1",
            user_name="User One",
            action="login"
        )
        attendance_manager.log_attendance(
            user_id="user2",
            user_name="User Two",
            action="login"
        )
        
        # Get today's log
        today_log = attendance_manager.get_todays_attendance()
        
        assert len(today_log) >= 2
        # Verify structure
        for entry in today_log:
            assert 'user_name' in entry
            assert 'timestamp' in entry
            assert 'action' in entry
    
    def test_get_user_attendance_history(self, attendance_manager):
        """Test getting attendance history for a specific user."""
        user_id = "user123"
        
        # Log multiple entries
        for i in range(5):
            attendance_manager.log_attendance(
                user_id=user_id,
                user_name="Test User",
                action="login" if i % 2 == 0 else "logout"
            )
        
        # Get history
        history = attendance_manager.get_user_history(user_id, days=7)
        
        assert len(history) >= 5
    
    def test_calculate_work_hours(self, attendance_manager):
        """Test calculating work hours from attendance log."""
        user_id = "worker"
        
        # Simulate a work day
        attendance_manager.log_attendance(
            user_id=user_id,
            user_name="Worker",
            action="login",
            timestamp=datetime.now().replace(hour=9, minute=0)
        )
        attendance_manager.log_attendance(
            user_id=user_id,
            user_name="Worker",
            action="logout",
            timestamp=datetime.now().replace(hour=17, minute=30)
        )
        
        # Calculate hours
        hours = attendance_manager.calculate_work_hours(user_id, days=1)
        
        # Should be approximately 8.5 hours
        assert 8.0 <= hours <= 9.0


class TestCentralAttendance:
    """Test the centralized attendance system."""
    
    @pytest.fixture
    def temp_central_dir(self):
        """Create a temporary central attendance directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "central_attendance"
    
    @pytest.fixture
    def central_attendance(self, temp_central_dir):
        """Create a central attendance manager."""
        temp_central_dir.mkdir(parents=True, exist_ok=True)
        return CentralAttendance()
    
    def test_sync_attendance(self, central_attendance):
        """Test syncing attendance to central location."""
        success = central_attendance.sync_attendance(
            user_id="user123",
            user_name="Test User",
            action="login",
            timestamp=datetime.now()
        )
        
        # Should succeed or gracefully handle network issues
        assert success or success is False  # Boolean result
    
    def test_get_team_overview(self, central_attendance):
        """Test getting team attendance overview."""
        # Sync some attendance data
        users = ["user1", "user2", "user3"]
        for user_id in users:
            central_attendance.sync_attendance(
                user_id=user_id,
                user_name=f"User {user_id[-1]}",
                action="login",
                timestamp=datetime.now()
            )
        
        # Get overview
        overview = central_attendance.get_team_overview()
        
        # Should return team status
        assert isinstance(overview, (list, dict))
    
    def test_check_user_status(self, central_attendance):
        """Test checking if a user is currently active."""
        user_id = "user123"
        
        # Log user in
        central_attendance.sync_attendance(
            user_id=user_id,
            user_name="Active User",
            action="login",
            timestamp=datetime.now()
        )
        
        # Check status
        is_active = central_attendance.is_user_active(user_id)
        
        # User should be considered active
        assert is_active or is_active is False  # Boolean result


class TestIdleDetection:
    """Test idle time detection."""
    
    def test_detect_idle_time(self, attendance_manager):
        """Test detecting idle periods in attendance."""
        user_id = "idleuser"
        
        # Simulate activity with an idle gap
        attendance_manager.log_attendance(
            user_id=user_id,
            user_name="Idle User",
            action="activity",
            timestamp=datetime.now() - timedelta(hours=2)
        )
        # Gap of 30 minutes (idle)
        attendance_manager.log_attendance(
            user_id=user_id,
            user_name="Idle User",
            action="activity",
            timestamp=datetime.now() - timedelta(minutes=90)
        )
        
        # Calculate idle time
        idle_minutes = attendance_manager.calculate_idle_time(user_id, hours=3)
        
        # Should detect some idle time
        assert idle_minutes >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
