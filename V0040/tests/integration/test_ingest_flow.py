"""
Headed Integration Test for the Smart Ingest Flow.

This test simulates the entire 'Incoming Delivery' process without needing a GUI.
It mocks:
- The Filesystem (Source/Dest paths)
- The Database (Project/Shot/Asset tracking)
- The Config Manager (Ingest Rules)

Goal: Verify that 'SmartScanWorker' correctly identifies file types (e.g., .exr, .wav) 
and moves them to their assigned folder structures (01_Plates, 02_Audio).
"""

from ut_vfx.core.domain.workers.smart_scan_worker import SmartScanWorker
from unittest.mock import MagicMock

class TestIngestFlow:
    """
    Integration Tests for the Ingest Lifecycle.
    Verifies: Source -> SmartScanWorker -> Target Structure -> Database
    """

    def test_smart_ingest_headless(self, temp_vfx_root, mock_db):
        """
        Scenario:
        1. Create 'Incoming/Reel_01/shot_010/plate.exr'
        2. Run SmartScanWorker targeting '05_Reels'
        3. Expect '05_Reels/Reel_01/shot_010/01_Plates/plate.exr'
        """
        
        # 1. SETUP: Create Mock Incoming Data
        source_dir = temp_vfx_root / "Incoming"
        
        # Create a "Reel" container
        reel_dir = source_dir / "Reel_Scans_01"
        reel_dir.mkdir()
        
        # Create a "Shot" inside
        shot_dir = reel_dir / "sh010"
        shot_dir.mkdir()
        
        # Create a File (Plate)
        plate_file = shot_dir / "sh010_bg_plate_v01.exr"
        # Create a "Audio" file too
        audio_file = shot_dir / "sh010_audio_ref.wav"
        
        plate_file.write_text("FAKE EXR DATA")
        audio_file.write_text("FAKE WAV DATA")
        
        # 2. EXECUTE: Run Worker
        # We target the root of the project for the worker
        target_dir = temp_vfx_root
        
        # --- PATCHING BEFORE INIT ---
        import ut_vfx.core.domain.workers.smart_scan_worker as worker_module
        
        # Patch DatabaseManager singleton
        worker_module.database_manager = mock_db
        
        # Patch ConfigManager CLASS
        mock_conf_instance = MagicMock()
        mock_conf_instance.ingest_rules = {
             "01_Plates": {"aliases": ["plate", "bg", "back"], "extensions": [".exr"], "priority": 10},
             "02_Audio": {"aliases": ["audio", "wav"], "extensions": [".wav"], "priority": 10}
        }
        # Store original class to restore later (or rely on module reload if we were careful, but here we just monkeypatch)
        worker_module.ConfigManager = MagicMock(return_value=mock_conf_instance)

        # Initialize Worker AFTER patching
        worker = SmartScanWorker(
            target_dir=target_dir,
            source_scan_path=source_dir,
            project_name="TestProject",
            template_data=([], [], [], ["01_Plates", "02_Audio"]), # Mock template subs matching keys
            overwrite=False,
            dry_run=False,
            fast_mode=True,
            confidence=0.6,
            sorting_logic="auto"
        )
        
        # DEBUG rules
        print(f"Analyzer Rules Keys: {worker.analyzer.rules.keys()}")
        
        # Run Synchronously (mimicking thread start/join)
        worker.run()
        
        # 3. VERIFY: Check Filesystem
        # Expected: target_dir/TestProject/05_Reels/Reel_Scans_01/sh010/01_Plates/sh010_bg_plate_v01.exr
        expected_path_plate = target_dir / "TestProject/05_Reels/Reel_Scans_01/sh010/01_Plates/sh010_bg_plate_v01.exr"
        expected_path_audio = target_dir / "TestProject/05_Reels/Reel_Scans_01/sh010/02_Audio/sh010_audio_ref.wav"
        
        # DEBUG: Print FS
        print("\n--- FILESYSTEM STATE ---")
        for p in target_dir.rglob("*"):
             print(p)
        print("------------------------")
        
        assert expected_path_plate.exists(), f"Plate was not moved to {expected_path_plate}"
        assert expected_path_audio.exists(), f"Audio was not moved to {expected_path_audio}"
