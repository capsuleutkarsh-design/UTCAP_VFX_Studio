import logging
import time
import re
import psutil
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition

# Production Imports
from ut_vfx.core.infra.database_manager import database_manager
from ut_vfx.core.infra.file_operations import SafeFileOperations
from ut_vfx.core.domain.ingest.analyzer import SmartIngestAnalyzer
from ut_vfx.core.infra.config_manager import ConfigManager
from ut_vfx.utils.security import SecurityValidator
from ut_vfx.utils.sequence_utils import SequenceDetector
from ut_vfx.core.services.path_template_manager import get_path_manager

# --- JUNK FILE FILTER LIST ---
IGNORED_FILES = {
    '.ds_store', 'thumbs.db', 'desktop.ini', 
    '._*',  # AppleDouble resource forks
    '*.tmp', '*.bak', '*.swp',  # Temp/Backup files
    '$recycle.bin', 'system volume information'
}

# Media extensions for detecting "has media" in folder
MEDIA_EXTENSIONS = {
    # Images/Sequences
    '.exr', '.dpx', '.cin', '.ari', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.tga',
    # Video
    '.mov', '.mp4', '.mxf', '.avi', '.mkv',
    # Valid Audio
    '.wav', '.mp3', '.aif', '.aiff', '.m4a', '.ogg',
    # 3D
    '.fbx', '.obj', '.abc', '.ma', '.mb', '.blend', '.usd', '.usdc', '.usda',
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.md',
    # Project Files
    '.nk', '.nknc', '.prproj', '.drp'
}


class SmartScanWorker(QThread):
    """
    PRODUCTION WORKER: Unified Project Builder & Smart Files Mover.
    Integrates Smart Ingest Intelligence into the standard Auto-Scan structure.
    
    Fixes applied:
        1. Progress emission during processing
        2. Recursive nesting detection (any depth)
        3. SequenceDetector integration (group frames)
        4. Loose files at root level handled
        5. Auto-detect reel naming (parent folder name, not hardcoded)
        6. Collision handling (logged + counted)
        7. Multi-scan-per-shot normalization
        8. Template data validation
        9. Dry run stats
    """
    
    log_signal = Signal(str)
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, int, int, int, int, str)
    dry_run_data = Signal(list)  # Emits list of operations for Visual Diff
    
    def __init__(self, target_dir, source_scan_path=None, project_name="", template_data=(), 
                 target_reel_name="", overwrite=False, dry_run=False, fast_mode=False,
                 confidence=0.6, sorting_logic="auto", format_mapping=None):
        super().__init__()
        self.target_dir = Path(target_dir)
        self.source_scan_path = Path(source_scan_path) if source_scan_path else None
        self.project_name = project_name
        self.template_data = template_data
        self.target_reel_name = target_reel_name
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.fast_mode = fast_mode
        self.confidence = confidence
        self.sorting_logic = sorting_logic
        self.format_mapping = format_mapping or {}
        
        self.is_running = True
        self.is_paused = False
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        
        self.folders_created = 0
        self.reels_count = 0
        self.shots_count = 0
        self.files_moved = 0
        self.files_skipped = 0
        self.errors = 0
        self.dry_run_ops = []
        self.security_validator = SecurityValidator()
        
        # Progress tracking
        self._total_files = 0
        self._processed_files = 0
        
        # Init Analyzer with Production Rules from Config
        cm = ConfigManager()
        rules = getattr(cm, 'ingest_rules', None)
        if not rules:
            # Fallback: use default_ingest_rules property
            rules = getattr(cm, 'default_ingest_rules', {})
        self.analyzer = SmartIngestAnalyzer(rules)

    def pause(self):
        self.mutex.lock()
        self.is_paused = True
        self.mutex.unlock()
        self.log_signal.emit("[WAIT] Process Paused.")

    def resume(self):
        self.mutex.lock()
        self.is_paused = False
        self.pause_condition.wakeAll()
        self.mutex.unlock()
        self.log_signal.emit("[RESUME] Process Resumed.")

    def check_pause(self):
        self.mutex.lock()
        if self.is_paused:
            self.pause_condition.wait(self.mutex)
        self.mutex.unlock()

    def stop(self):
        """Request the worker to stop gracefully."""
        self.mutex.lock()
        self.is_running = False
        self.is_paused = False # Break out of pause if stuck
        self.pause_condition.wakeAll()
        self.mutex.unlock()
        self.log_signal.emit("[STOP] Stopping worker...")

    def _emit_progress(self, message=""):
        """Emit progress based on files processed so far."""
        if self._total_files > 0:
            pct = min(int((self._processed_files / self._total_files) * 100), 99)
        else:
            pct = 0
        self.progress_signal.emit(pct, message or f"Processing... ({self._processed_files}/{self._total_files})")

    def run(self):
        start_time = time.time()
        
        try:
            # Production Database Check
            if hasattr(database_manager, 'record_project'):
                pid = database_manager.record_project(self.project_name, "smart_ingest", str(self.target_dir))
                op_type = "Smart Ingest"
                self.op_id = database_manager.start_operation(pid, op_type)
            else:
                 self.op_id = 0
        except Exception:
            self.op_id = 0

        try:
            self.log_signal.emit(f"[START] Starting Smart Ingest (Logic: {self.sorting_logic}, Conf: {int(self.confidence*100)}%)...")
            
            # --- Validate template_data ---
            if not self.template_data or len(self.template_data) < 4:
                self.log_signal.emit("[WARN] Template data incomplete — using defaults")
                base_folders = ["01_Scan", "05_Reels"]
                prod_subs = []
                outsource_subs = []
                shot_subs = ["01_Plates", "07_Comp", "09_Render"]
            else:
                base_folders, prod_subs, outsource_subs, shot_subs = self.template_data

            if not isinstance(shot_subs, list) or not shot_subs:
                self.log_signal.emit("[WARN] shot_folders empty/invalid - using defaults")
                shot_subs = ["01_Scan", "07_Comp", "08_Output"]


            # --- Disk space check ---
            if self.source_scan_path and not self.dry_run:
                total_size = self._calculate_directory_size(self.source_scan_path)
                if not self._check_disk_space(total_size, self.target_dir):
                    self.finished_signal.emit(False, 0, 0, 0, 0, "Insufficient Disk Space")
                    return

            # --- FIX #1: Count total files upfront for progress ---
            if self.source_scan_path and self.source_scan_path.exists():
                self._total_files = sum(1 for f in self.source_scan_path.rglob('*') 
                                       if f.is_file() and not self._is_junk_file(f))
                self.log_signal.emit(f"[INFO] Found {self._total_files} files to process")
            
            self._emit_progress("Building project structure...")

            project_path = self.target_dir / self.project_name
            
            # 1. Structure Creation
            self.log_signal.emit("[BUILD] Building Project Structure...")
            if not self.dry_run:
                SafeFileOperations.safe_create_directory(project_path)
                for f in base_folders: 
                    SafeFileOperations.safe_create_directory(project_path / f)
                if prod_subs:
                    p = project_path / "04_Production"
                    SafeFileOperations.safe_create_directory(p)
                    for s in prod_subs: 
                        SafeFileOperations.safe_create_directory(p / s)
                # Create 05_Reels using template
                mgr = get_path_manager()
                reels_path = Path(mgr.format_path('reels_root', project=self.project_name, root=str(project_path.parent)))
                SafeFileOperations.safe_create_directory(reels_path)
            else:
                # For dry run, compute reels_path without creating
                mgr = get_path_manager()
                reels_path = Path(mgr.format_path('reels_root', project=self.project_name, root=str(project_path.parent)))

            # 2. Smart Ingest Phase
            if self.source_scan_path:
                self._process_smart_ingest(reels_path, shot_subs, self.op_id)

            dur = time.time() - start_time
            if hasattr(database_manager, 'update_operation'):
                database_manager.update_operation(self.op_id, dur, self.files_moved, self.errors, True)
            
            if self.dry_run:
                self.dry_run_data.emit(self.dry_run_ops)
                # FIX #9: Report actual dry run counts
                self.finished_signal.emit(
                    True, self.reels_count, self.shots_count, self.folders_created, 
                    len(self.dry_run_ops), f"Dry Run: {len(self.dry_run_ops)} operations planned."
                )
            else:
                summary_parts = [f"Moved {self.files_moved} files"]
                if self.files_skipped > 0:
                    summary_parts.append(f"Skipped {self.files_skipped}")
                if self.errors > 0:
                    summary_parts.append(f"Errors: {self.errors}")
                summary_parts.append(f"in {dur:.1f}s")
                
                self.finished_signal.emit(
                    True, self.reels_count, self.shots_count, self.folders_created, 
                    self.files_moved, " | ".join(summary_parts)
                )

        except Exception as e:
            logging.exception(f"Smart Worker Error: {e}", exc_info=True)
            if hasattr(database_manager, 'update_operation'):
                database_manager.update_operation(self.op_id, time.time()-start_time, 0, 1, False)
            self.finished_signal.emit(False, 0, 0, 0, 0, str(e))

    # -------------------------------------------------------------------------
    # FIX #2: Recursive Nesting Detection
    # -------------------------------------------------------------------------
    
    def _detect_level(self, folder: Path) -> str:
        """
        Recursively detect what a folder represents:
            'media'     — contains media files directly (it's the deepest level)
            'shot'      — has known category subfolders (Plates, Comp, etc.)
            'container' — contains only subdirectories (reel or mid-level wrapper)
        """
        if not folder.is_dir():
            return 'unknown'
        
        children = list(folder.iterdir())
        has_media_files = any(
            f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS and not self._is_junk_file(f) 
            for f in children
        )
        sub_dirs = [d for d in children if d.is_dir()]
        sub_names_lower = {d.name.lower() for d in sub_dirs}
        
        # Known category folder names that indicate "this is a shot"
        known_categories = {
            "01_scan", "02_audio", "01_plates", "02_plate", "05_prep", "06_roto", 
            "07_comp", "08_lighting", "09_render", "06_ref",
            "scans", "plates", "comp", "renders", "audio", "ref", "footage",
            "prerenders", "roto", "paint", "prep", "cleanup"
        }
        
        looks_like_shot = bool(sub_names_lower.intersection(known_categories))
        
        if has_media_files:
            return 'media'
        elif looks_like_shot:
            return 'shot'
        elif sub_dirs:
            return 'container'
        else:
            return 'empty'

    def _walk_and_collect_shots(self, folder: Path, max_depth=6, current_depth=0):
        """
        FIX #2: Recursively walk folder tree to find actual shots,
        regardless of how many wrapper levels exist.
        
        Returns: list of (shot_folder: Path, reel_name: str) tuples
        """
        if current_depth > max_depth or not self.is_running:
            return []
        
        level = self._detect_level(folder)
        results = []
        
        if level in ('media', 'shot'):
            # This folder IS a shot — determine reel from parent
            reel_name = folder.parent.name if current_depth > 0 else "Reel_Root"
            results.append((folder, reel_name))
            
        elif level == 'container':
            # Recurse into subdirectories
            for sub in sorted(folder.iterdir()):
                if sub.is_dir() and self.is_running:
                    results.extend(self._walk_and_collect_shots(sub, max_depth, current_depth + 1))
        
        return results

    # -------------------------------------------------------------------------
    # FIX #7: Multi-scan normalization
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _normalize_shot_name(name: str) -> str:
        """
        Normalize shot folder names to detect duplicates/versions.
        
        Examples:
            'Shot_01_ScanA'    → 'Shot_01'
            'Shot_01_ScanB'    → 'Shot_01'
            'SH010_v02'        → 'SH010'
            'SH010_Rescan'     → 'SH010'
            'SH010'            → 'SH010'
        """
        normalized = name
        # Remove _ScanA, _ScanB, _Rescan, _scan_v2 etc.
        normalized = re.sub(r'[_\-](?:scan[_]?[a-z0-9]*|rescan)$', '', normalized, flags=re.IGNORECASE)
        # Remove _v01, _v02 suffixes
        normalized = re.sub(r'[_\-]v\d+$', '', normalized, flags=re.IGNORECASE)
        return normalized

    # -------------------------------------------------------------------------
    # Main Ingest Logic
    # -------------------------------------------------------------------------

    def _process_smart_ingest(self, root, subs, oid):
        self.log_signal.emit(f"[SCAN] Scanning: {self.source_scan_path}")
        
        if self.target_reel_name:
            # --- USER-SPECIFIED REEL ---
            dest_reel = root / self.target_reel_name
            if not self.dry_run: 
                SafeFileOperations.safe_create_directory(dest_reel)
            self.reels_count += 1
            
            # FIX #2: Use recursive detection instead of 1-level iteration
            collected = self._walk_and_collect_shots(self.source_scan_path)
            
            if not collected:
                # FIX #4: Maybe the source IS the shot itself (loose files at root)
                if self._has_media_files(self.source_scan_path):
                    collected = [(self.source_scan_path, self.target_reel_name)]
                else:
                    self.log_signal.emit("[WARN] No shots found in source path")
            
            # FIX #7: Group by normalized shot name
            shot_groups = self._group_shots_by_name(collected)
            
            for norm_name, shots_list in shot_groups.items():
                self.check_pause()
                if not self.is_running: break
                
                if len(shots_list) > 1:
                    self.log_signal.emit(f"  [MULTI] {len(shots_list)} scans detected for '{norm_name}': {[s[0].name for s in shots_list]}")
                
                for shot_path, _ in shots_list:
                    self.check_pause()
                    if not self.is_running: break
                    self._process_single_smart_shot(shot_path, dest_reel, subs, oid, norm_name)
        else:
            # --- AUTO-DETECT REELS ---
            # FIX #2: Recursively discover shots
            collected = self._walk_and_collect_shots(self.source_scan_path)
            
            # FIX #4: Handle loose files at source root
            if self._has_media_files(self.source_scan_path):
                collected.append((self.source_scan_path, "Reel_Root"))
            
            if not collected:
                self.log_signal.emit("[WARN] No shots found in source path")
                return
            
            self.log_signal.emit(f"[FOUND] Discovered {len(collected)} shot(s) across source")
            
            # FIX #5: Group by actual reel name (parent folder), not hardcoded Reel_Incoming
            reel_groups = {}
            for shot_path, reel_name in collected:
                # Use the detected reel name from _walk_and_collect_shots
                reel_groups.setdefault(reel_name, []).append(shot_path)
            
            for reel_name, shot_list in reel_groups.items():
                self.check_pause()
                if not self.is_running: break
                
                dest_reel = root / reel_name
                if not self.dry_run: 
                    SafeFileOperations.safe_create_directory(dest_reel)
                self.reels_count += 1
                self.log_signal.emit(f"  [REEL] {reel_name} ({len(shot_list)} shots)")
                
                # FIX #7: Group by normalized name within each reel
                named_shots = [(s, reel_name) for s in shot_list]
                shot_groups = self._group_shots_by_name(named_shots)
                
                for norm_name, shots_list in shot_groups.items():
                    self.check_pause()
                    if not self.is_running: break
                    
                    if len(shots_list) > 1:
                        self.log_signal.emit(f"    [MULTI] {len(shots_list)} scans for '{norm_name}'")
                    
                    for shot_path, _ in shots_list:
                        self.check_pause()
                        if not self.is_running: break
                        self._process_single_smart_shot(shot_path, dest_reel, subs, oid, norm_name)

    def _group_shots_by_name(self, shot_list):
        """
        FIX #7: Group shots by normalized name.
        Returns dict: normalized_name → [(shot_path, reel_name), ...]
        """
        groups = {}
        for shot_path, reel_name in shot_list:
            norm = self._normalize_shot_name(shot_path.name)
            groups.setdefault(norm, []).append((shot_path, reel_name))
        return groups

    def _has_media_files(self, folder: Path) -> bool:
        """FIX #4: Check if a folder contains media files directly (not in subdirs)."""
        try:
            return any(
                f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS and not self._is_junk_file(f)
                for f in folder.iterdir()
            )
        except (PermissionError, OSError):
            return False

    def _process_single_smart_shot(self, src_shot, dest_reel, subs, oid, dest_name=None):
        """
        Analyzes files in the shot folder and sorts them using Smart Analyzer.
        
        FIX #3: Uses SequenceDetector to group frame sequences.
        FIX #6: Logs collision/skip events.
        """
        shot_name = dest_name or src_shot.name
        
        # Calculate isolated version suffix if multiple scans are merged
        version_suffix = ""
        if dest_name and dest_name != src_shot.name:
            if src_shot.name.lower().startswith(dest_name.lower()):
                version_suffix = src_shot.name[len(dest_name):].lstrip('_-')
                
        dest_shot = dest_reel / shot_name
        
        if not self.dry_run: 
            SafeFileOperations.safe_create_directory(dest_shot)
        self.shots_count += 1
        self.folders_created += 1
        
        # Create standard subs first
        for s in subs:
            if not self.dry_run: 
                SafeFileOperations.safe_create_directory(dest_shot / s)
            self.folders_created += 1

        self.log_signal.emit(f"  [SHOT] {shot_name} (from: {src_shot.name})")

        # --- FIX #3: Detect sequences first ---
        all_files = [x for x in src_shot.rglob('*') if x.is_file() and not self._is_junk_file(x)]
        
        # Group files by sequence (if SequenceDetector available)
        sequence_groups = {}  # pattern → [files]
        standalone_files = []
        
        if SequenceDetector.is_available():
            # Find all sequences in this shot
            try:
                sequences_found = SequenceDetector.find_all_sequences(src_shot)
                # Build a set of files that belong to sequences
                seq_file_set = set()
                for seq in sequences_found:
                    pattern = SequenceDetector.get_pattern(seq)
                    frame_count = SequenceDetector.get_frame_count(seq)
                    start, end = SequenceDetector.get_frame_range(seq)
                    
                    # Get list of frame paths from the sequence
                    seq_files = []
                    for frame_path_str in seq:
                        fp = Path(str(frame_path_str))
                        if fp.exists() and fp.is_file():
                            seq_files.append(fp)
                            seq_file_set.add(fp)
                    
                    if seq_files:
                        missing = SequenceDetector.get_missing_frames(seq)
                        if missing:
                            self.log_signal.emit(f"    [WARN] Sequence {Path(pattern).name}: {len(missing)} missing frames")
                        
                        sequence_groups[pattern] = {
                            'files': seq_files,
                            'frame_count': frame_count,
                            'start': start,
                            'end': end,
                            'name': Path(pattern).name
                        }
                
                # Files not part of any sequence
                standalone_files = [f for f in all_files if f not in seq_file_set]
                
            except Exception as e:
                logging.warning(f"Sequence detection failed for {src_shot}: {e}")
                standalone_files = all_files
        else:
            standalone_files = all_files

        # --- Process sequences as groups ---
        for pattern, seq_info in sequence_groups.items():
            self.check_pause()
            if not self.is_running: break
            
            # Use first file in sequence for category detection
            first_file = seq_info['files'][0]
            target_sub = self._determine_target(first_file, src_shot, subs, version_suffix)
            
            self.log_signal.emit(
                f"    [SEQ] {seq_info['name']} [{seq_info['start']}-{seq_info['end']}] "
                f"({seq_info['frame_count']} frames) → {target_sub}"
            )
            
            # Move all frames in sequence
            for f in seq_info['files']:
                self.check_pause()
                if not self.is_running: break
                self._move_single_file(f, src_shot, dest_shot, target_sub, oid)

        # --- Process standalone files ---
        for f in standalone_files:
            self.check_pause()
            if not self.is_running: break
            
            target_sub = self._determine_target(f, src_shot, subs, version_suffix)
            self.log_signal.emit(f"    [FILE] {f.name} → {target_sub}")
            self._move_single_file(f, src_shot, dest_shot, target_sub, oid)

    def _determine_target(self, f: Path, src_shot: Path, subs: list, version_suffix: str = "") -> str:
        """Determine target subfolder for a file using sorting logic + analyzer."""
        target_sub = "01_Scan"
        
        # 1. FORCED FOLDERS
        if self.sorting_logic not in ["auto", "quarantine", "force_scan"]:
            target_sub = self.sorting_logic
        
        # 2. FORCE SCAN
        elif self.sorting_logic == "force_scan":
            target_sub = "01_Scan"

        # 3. SMART AUTO / QUARANTINE
        else:
            category, score, reason = self.analyzer.analyze_item(f)
            
            if score < self.confidence:
                if self.sorting_logic == "quarantine":
                    target_sub = "_Quarantine"
                else:
                    target_sub = "01_Scan"
            else:
                if category:
                    # Find matching folder in template subs
                    found = False
                    for s in subs:
                        if category.lower() in s.lower():
                            target_sub = s
                            found = True
                            break
                    if not found and score > 0.8:
                        target_sub = category
        
        # 3.5 VERSION ISOLATION 
        # Isolate versions into subdirectories inside Scan to prevent collisions
        if version_suffix and "scan" in target_sub.lower():
            target_sub = f"{target_sub}/{version_suffix}"

        # 4. SUB-FOLDER REFINEMENT (Format Mapping)
        # If the target is the generic Scan folder, try to sort by format (exr, mov, etc.)
        # This matches FolderCreationWorker behavior.
        if "scan" in target_sub.lower() and self.format_mapping:
            ext = f.suffix.lower().lstrip('.')
            # Check if we have a mapping for this extension
            mapped_folder = self.format_mapping.get(ext)
            
            if mapped_folder:
                # mapped_folder might be "01_Scan/exr" or just "exr"
                # We want to append the subpart to the current target_sub (which is likely "01_Scan")
                
                # If mapping is full path "01_Scan/exr", extract "exr"
                sub_part = mapped_folder.split('/')[-1]
                
                # If target_sub is "01_Scan", new path is "01_Scan/exr"
                target_sub = f"{target_sub}/{sub_part}"
            else:
                # Default fallback: 01_Scan/EXT (if not mapped but verified media)
                # But only if it's a media file.
                if ext in ['exr', 'dpx', 'mov', 'mp4', 'mxf', 'jpg', 'png', 'tif']:
                     target_sub = f"{target_sub}/{ext.upper()}"

        return target_sub

    def _move_single_file(self, f: Path, src_shot: Path, dest_shot: Path, target_sub: str, oid):
        """
        Move or simulate a single file. Handles:
            - FIX #1: Progress emission per file
            - FIX #6: Collision detection + logging
        """
        try:
            rel_parent = f.relative_to(src_shot).parent
        except ValueError:
            rel_parent = Path("")
        
        dest_file = dest_shot / target_sub / rel_parent / f.name
        
        # FIX #1: Update progress
        self._processed_files += 1
        if self._processed_files % 50 == 0 or self._processed_files == self._total_files:
            self._emit_progress(f"Processing: {f.name}")
        
        # Dry run: just record
        if self.dry_run:
            if len(self.dry_run_ops) < 5000:
                self.dry_run_ops.append({
                    "type": "MOVE", 
                    "source": str(f), 
                    "destination": str(dest_file),
                    "size": f.stat().st_size if f.exists() else 0
                })
            elif len(self.dry_run_ops) == 5000:
                self.dry_run_ops.append({
                    "type": "WARN", 
                    "source": "... and more files", 
                    "destination": "List truncated to prevent memory crash",
                    "size": 0
                })
            return
        
        # Ensure target parent
        SafeFileOperations.safe_create_directory(dest_file.parent)
        
        # FIX #6: Collision handling
        if dest_file.exists():
            if self.overwrite:
                self.log_signal.emit(f"      [OVERWRITE] {f.name} (replacing existing)")
                dest_file.unlink()
            else:
                self.files_skipped += 1
                self.log_signal.emit(f"      [SKIP] {f.name} — already exists at destination")
                self._processed_files += 1
                return
        
        # Capture size BEFORE move
        file_size = f.stat().st_size if f.exists() else 0
        
        try:
            verify = not self.fast_mode
            SafeFileOperations.safe_move_with_verification(f, dest_file, verify_checksum=verify)
            self.files_moved += 1
            
            if hasattr(database_manager, 'record_task_detail'):
                database_manager.record_task_detail(oid, f.name, f, dest_file, file_size, 0, "Success")
                
        except Exception as e:
            self.errors += 1
            self.log_signal.emit(f"      [ERR] {f.name}: {e}")

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _calculate_directory_size(self, path):
        try:
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        except (PermissionError, OSError):
            return 0

    def _check_disk_space(self, size, dest):
        try:
            free = psutil.disk_usage(str(dest.anchor)).free
            return free > (size * 1.1)
        except Exception:
            return True

    def _is_junk_file(self, path: Path) -> bool:
        name = path.name.lower()
        if name in IGNORED_FILES: return True
        if name.startswith("._"): return True
        if name.startswith("~$"): return True
        return False
