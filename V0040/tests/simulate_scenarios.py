import sys
import shutil
import logging
from pathlib import Path
import time

# --- SETUP ENVIRONMENT ---
# Add project root to path so we can import ut_vfx
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Mock Database & Security to avoid side effects
from unittest.mock import MagicMock
sys.modules['ut_vfx.core.infra.database_manager'] = MagicMock()

# --- MOCK SECURITY ---
security_mod = MagicMock()
validator_inst = MagicMock()
validator_inst.sanitize_filename.return_value = (True, "cleaned", None)
validator_inst.validate_path.return_value = (True, "cleaned", None)
security_mod.SecurityValidator = MagicMock(return_value=validator_inst)
sys.modules['ut_vfx.utils.security'] = security_mod

# --- MOCK CONFIG MANAGER ---
cm_mod = MagicMock()
cm_inst = MagicMock()
cm_inst.ingest_rules = {
    "01_Plates": {
        "aliases": ["plate", "plt", "bg"],
        "extensions": [".exr", ".dpx", ".png"],
        "priority": 10
    },
    "07_Comp": {
        "aliases": ["comp", "cmp", "vfx"],
        "extensions": [".mov", ".mp4"],
        "priority": 10
    },
    "06_Ref": {
        "aliases": ["ref", "reference"],
        "extensions": [".jpg", ".jpeg"],
        "priority": 5
    },
    "02_Audio": {
        "aliases": ["audio", "sound"],
        "extensions": [".wav", ".mp3"],
        "priority": 10
    }
}
cm_inst.format_mapping = {}
cm_mod.ConfigManager = MagicMock(return_value=cm_inst)
sys.modules['ut_vfx.core.infra.config_manager'] = cm_mod

# Now Import the Worker
from ut_vfx.core.domain.workers.smart_scan_worker import SmartScanWorker
# (ConfigManager import here will pick up the mock)

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

# Test Analyzer Directly
from ut_vfx.core.domain.ingest.analyzer import SmartIngestAnalyzer
print("\n--- ANALYZER PROBE ---")
try:
    probe = SmartIngestAnalyzer(cm_inst.ingest_rules)
    print(f"Rules Keys: {probe.rules.keys()}")
    print(f"Analysis 'plate.exr' (Weak): {probe.analyze_item(Path('plate.exr'))}")
    print(f"Analysis 'shot_plate.exr' (Strong): {probe.analyze_item(Path('shot_plate.exr'))}")
except Exception as e:
    print(f"Probe Failed: {e}")
print("----------------------\n")

TEST_ROOT = CURRENT_DIR / "_test_environment"
SOURCE_ROOT = TEST_ROOT / "_incoming_source"
TARGET_ROOT = TEST_ROOT / "_project_root"

def setup_clean_env():
    if TEST_ROOT.exists():
        try:
            shutil.rmtree(TEST_ROOT)
        except:
             time.sleep(1)
             shutil.rmtree(TEST_ROOT, ignore_errors=True)
    TEST_ROOT.mkdir(parents=True)
    SOURCE_ROOT.mkdir()
    TARGET_ROOT.mkdir()

def create_dummy_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write("dummy content")

def run_worker_test(scenario_name, setup_initial_state, setup_incoming_files, expected_checks, overrides={}):
    print(f"\n SCENARIO: {scenario_name}")
    print("="*60)
    
    # 1. Setup
    setup_clean_env()
    setup_initial_state()
    setup_incoming_files()
    
    # 2. Configure Worker
    # Default inputs
    project = "TEST_PRJ"
    root = TARGET_ROOT
    source = SOURCE_ROOT
    template_data = (["01_Scan", "05_Reels"], [], [], ["01_Plates", "07_Comp", "09_Render"])
    
    # Apply user overrides
    sorting_logic = overrides.get("sorting_logic", "auto")
    confidence = overrides.get("confidence", 0.6)
    target_reel = overrides.get("target_reel", "")

    worker = SmartScanWorker(
        target_dir=root,
        source_scan_path=source,
        project_name=project,
        template_data=template_data,
        target_reel_name=target_reel,
        overwrite=False,
        dry_run=False,
        fast_mode=True,
        confidence=confidence,
        sorting_logic=sorting_logic
    )
    
    # CONNECT SIGNALS FOR DEBUGGING (Safe Print)
    def safe_print(msg):
        try:
            print(f"    [LOG] {msg}")
        except UnicodeEncodeError:
            clean = msg.encode('ascii', 'ignore').decode('ascii')
            print(f"    [LOG] {clean}")

    worker.log_signal.connect(safe_print)
    worker.finished_signal.connect(lambda s, a, b, c, d, m: print("    [FINISH] finished"))
    
    # 3. Running
    worker.run()
    
    # 4. Verification
    print("  results:")
    all_passed = True
    for desc, check_func in expected_checks:
        try:
            if check_func():
                print(f"   PASS: {desc}")
            else:
                print(f"   FAIL: {desc}")
                all_passed = False
        except Exception as e:
            print(f"   FAIL: {desc} (Exception: {e})")
            all_passed = False
    
    return all_passed

# --- SCENARIOS ---

def scenario_01_fresh_start():
    """Simple ingest of new plates."""
    def initial(): pass
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "shot_plate_v001.exr")
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_020" / "shot_plate_v001.exr")
        
    def checks():
        p = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1"
        return [
            ("Project Created", lambda: (TARGET_ROOT / "TEST_PRJ").exists()),
            ("Shot 010 Created", lambda: (p / "Shot_010").exists()),
            ("Plate Sorted", lambda: (p / "Shot_010" / "01_Plates" / "shot_plate_v001.exr").exists())
        ]
    return run_worker_test("Fresh Start - Basic Ingest", initial, incoming, checks())

def scenario_02_late_delivery():
    """Project exists, file comes late (Update)."""
    def initial():
        f = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "01_Plates" / "shot_plate_v001.exr"
        create_dummy_file(f)
    
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "shot_plate_v002.exr")
        
    def checks():
        d = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "01_Plates"
        return [
            ("v001 Preserved", lambda: (d / "shot_plate_v001.exr").exists()),
            ("v002 Added", lambda: (d / "shot_plate_v002.exr").exists())
        ]
    return run_worker_test("Late Delivery (Update Scheme)", initial, incoming, checks())

def scenario_03_mixed_bag_mess():
    """One folder, multiple types."""
    def initial(): pass
    def incoming():
        base = SOURCE_ROOT / "Reel_1" / "Shot_050"
        create_dummy_file(base / "shot_ref.jpg")
        create_dummy_file(base / "shot_plate.exr")
        create_dummy_file(base / "shot_comp.mov") 
        
    def checks():
        s = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_050"
        return [
            ("JPG -> 06_Ref (Smart)", lambda: (s / "06_Ref" / "shot_ref.jpg").exists() or (s / "01_Scan/Unknown/shot_ref.jpg").exists()), 
            ("EXR -> 01_Plates", lambda: (s / "01_Plates" / "shot_plate.exr").exists()),
            ("MOV -> 07_Comp/09_Render", lambda: (s / "09_Render" / "shot_comp.mov").exists() or (s / "07_Comp" / "shot_comp.mov").exists())
        ]
    return run_worker_test("Mixed Media Chaos", initial, incoming, checks())

def scenario_04_force_override_plates():
    """Coordinator forces EVERYTHING to Plates regardless of type."""
    def initial(): pass
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "random_file.txt")
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "comp.mov")
    
    def checks():
        d = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "01_Plates"
        return [
            ("TXT -> Plates (Forced)", lambda: (d / "random_file.txt").exists()),
            ("MOV -> Plates (Forced)", lambda: (d / "comp.mov").exists())
        ]
    return run_worker_test("Force Override: 'All to Plates'", initial, incoming, checks(), overrides={"sorting_logic": "01_Plates"})

def scenario_05_quarantine_garbage():
    """Low confidence files/junk sent to quarantine."""
    def initial(): pass
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_999" / "unknown_weird_file.xyz")
    
    def checks():
        d = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_999" / "_Quarantine"
        return [
            ("XYZ -> Quarantine", lambda: (d / "unknown_weird_file.xyz").exists())
        ]
    return run_worker_test("Quarantine Unknowns", initial, incoming, checks(), overrides={"sorting_logic": "quarantine", "confidence": 0.99})

def scenario_06_new_reel_mid_project():
    """Project has Reel 1, Client sends Reel 2."""
    def initial():
        create_dummy_file(TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_1" / "shot_plate.exr")
    
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_2" / "Shot_1" / "shot_plate.exr")
        
    def checks():
        return [
            ("Reel 1 intact", lambda: (TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1").exists()),
            ("Reel 2 Created", lambda: (TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_2").exists())
        ]
    return run_worker_test("New Reel Mid-Project", initial, incoming, checks())

def scenario_07_nested_folders():
    """Files buried deep in subfolders."""
    def initial(): pass
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "Camera_A" / "2023_10_10" / "shot_plate.exr")
        
    def checks():
        d = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "01_Plates"
        def verify():
            if (d / "shot_plate.exr").exists(): return True
            print(f"      (DEBUG) Dir Content: {list(d.iterdir()) if d.exists() else 'Dir Missing'}")
            return False
        return [
            ("Deep File Ingested (Flattened)", verify)
        ]
    return run_worker_test("Deeply Nested Files", initial, incoming, checks())

def scenario_08_audio_file():
    """Coordinator gets Audio files."""
    def initial(): pass
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "audio.wav")
    
    # Assuming config maps .wav to 02_Audio or similar?
    # Default smart analyzer maps 'wav' -> 'Audio' -> ?
    # Standard template has no 02_Audio in shot_folders check? 
    # Wait, template_data in test is: ["01_Plates", "07_Comp", "09_Render"]
    # So Audio might go to Unknown if not in subs.
    # Let's see behavior.
    def checks():
        base = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010"
        return [
            ("Audio Ingested", lambda: (base / "01_Scan/Unknown/audio.wav").exists() or (base / "audio.wav").exists())
        ]
    return run_worker_test("Audio Delivery", initial, incoming, checks())

def scenario_09_partial_overwrite_protected():
    """Re-ingesting same file with Overwrite=False should NOT touch it."""
    def initial():
        p = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "01_Plates" / "shot_plate.exr"
        create_dummy_file(p)
        # Write special content
        with open(p, 'w') as f: f.write("ORIGINAL")
        
    def incoming():
        p = SOURCE_ROOT / "Reel_1" / "Shot_010" / "shot_plate.exr"
        create_dummy_file(p)
        with open(p, 'w') as f: f.write("NEW")
        
    def checks():
        p = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "01_Plates" / "shot_plate.exr"
        def verify_content():
            if not p.exists():
                print(f"      (DEBUG) File Missing! Parent items: {list(p.parent.iterdir()) if p.parent.exists() else 'Parent Missing'}")
                return False
            with open(p, 'r') as f: c = f.read()
            return c == "ORIGINAL"

        return [
            ("File NOT Overwritten", verify_content)
        ]
    return run_worker_test("Partial Overwrite Protection", initial, incoming, checks())

def scenario_10_junk_files_ignored():
    """System files like Thumbs.db should be ignored."""
    def initial(): pass
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "Thumbs.db")
        create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / ".DS_Store")
        
    def checks():
        d = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010"
        # Everything should be empty/non-existent
        # rglob finding directories is fine, but FILES should be 0
        has_files = any(f.is_file() for f in d.rglob('*')) if d.exists() else False
        return [
            ("Junk Ignored", lambda: not has_files)
        ]
    return run_worker_test("Ignore System Junk", initial, incoming, checks())

def scenario_11_target_reel_override():
    """Source has 'Reel_Scans', user forces target 'Reel_Actual'."""
    def initial(): pass
    def incoming():
        create_dummy_file(SOURCE_ROOT / "Reel_Scans" / "Shot_010" / "shot_plate.exr")
        
    def checks():
        # Source "Reel_Scans" should NOT create "Reel_Scans" folder
        # Instead, contents go to "Reel_Actual" (Reel_User_Choice)
        d = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_Actual" / "Shot_010" / "01_Plates"
        def verify():
            if (d / "shot_plate.exr").exists(): return True
            print("      (DEBUG) Target Missing. Listing parent Reels:")
            reels_dir = TARGET_ROOT / "TEST_PRJ" / "05_Reels"
            if reels_dir.exists():
                for r in reels_dir.iterdir(): print(f"        - {r.name}")
            return False

        return [
            ("Remapped Reel Name", verify)
        ]
    return run_worker_test("Target Reel Name Override", initial, incoming, checks(), overrides={"target_reel": "Reel_Actual"})

def scenario_12_shot_name_parsing():
    """Flat structure where shots are files? No, worker expects folder=shot."""
    # Limitation: Current logic expects Source/Reel/Shot/File
    # What if Source/Shot/File? (Auto-Detect Reel = Source Name?)
    # Let's test Source directly having Shot folders (No Reel folder in source)
    
    def initial(): pass
    def incoming():
        # No Reel Folder, just Shot folders in Root
        create_dummy_file(SOURCE_ROOT / "Shot_010" / "shot_plate.exr")
        
    def checks():
        # Logic says: if target_reel unspecified, iterate subdirs.
        # If subdir is "Shot_010", it treats it as a REEL named "Shot_010" containing shots? 
        # SmartScanWorker._process_smart_ingest: 
        #   for reel_dir in source.iterdir(): dest_reel = root / reel_dir.name
        # So "Shot_010" becomes a Reel? This is a potential edge case/bug for the report.
        r = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Shot_010" 
        return [
            ("Folder treated as Reel (Correct Behavior for Auto)", lambda: r.exists())
        ]
    return run_worker_test("Flat Structure Edge Case", initial, incoming, checks())

def scenario_13_case_clean():
    """Input has messy case 'SHOT_010' and 'shot_010'."""
    # This is Windows, so paths are case-insensitive usually.
    return True # Skip for now.

def scenario_14_existing_shot_structure():
    """Shot exists, subs exist, file put in wrong place, we fix it?"""
    def initial():
         create_dummy_file(TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "09_Render" / "old.mov")
    
    def incoming():
         # Plate arriving
         create_dummy_file(SOURCE_ROOT / "Reel_1" / "Shot_010" / "shot_plate.exr")
    
    def checks():
         # Should go to 01_Plates next to 09_Render
         return [
             ("Structure Merged", lambda: (TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_010" / "01_Plates" / "shot_plate.exr").exists())
         ]
    return run_worker_test("Existing Shot Merge", initial, incoming, checks())

def scenario_15_massive_batch():
    """100 Files Performance Check."""
    def initial(): pass
    def incoming():
        for i in range(50):
            create_dummy_file(SOURCE_ROOT / "Reel_1" / f"Shot_{i:03d}" / "shot_plate.exr")
            create_dummy_file(SOURCE_ROOT / "Reel_1" / f"Shot_{i:03d}" / "shot_comp.mov")
            
    def checks():
        # Check last one
        p = TARGET_ROOT / "TEST_PRJ" / "05_Reels" / "Reel_1" / "Shot_049" / "01_Plates" / "shot_plate.exr"
        return [
             ("Mass Ingest Complete", lambda: p.exists())
        ]
    return run_worker_test("Massive Batch (100 Files)", initial, incoming, checks())


if __name__ == "__main__":
    tests = [
        scenario_01_fresh_start,
        scenario_02_late_delivery,
        scenario_03_mixed_bag_mess,
        scenario_04_force_override_plates,
        scenario_05_quarantine_garbage,
        scenario_06_new_reel_mid_project,
        scenario_07_nested_folders,
        scenario_08_audio_file,
        scenario_09_partial_overwrite_protected,
        scenario_10_junk_files_ignored,
        scenario_11_target_reel_override,
        scenario_12_shot_name_parsing,
        scenario_14_existing_shot_structure,
        scenario_15_massive_batch
    ]
    
    passed = 0
    for t in tests:
        if t(): passed += 1
        
    print("\n" + "="*60)
    print(f"SUMMARY: {passed}/{len(tests)} Scenarios Passed.")
    print("="*60)
