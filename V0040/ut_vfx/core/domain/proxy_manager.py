import subprocess
import logging
from pathlib import Path
import sys
import hashlib
from typing import Tuple
from PySide6.QtGui import QImage
from PySide6.QtCore import Qt  # Moved from line 149

from ut_vfx.utils.resource_manager import ResourcePathManager
from ut_vfx.utils.media_capabilities import is_image

class ProxyManager:
    """
    Handles generation of thumbnails and video proxies.
    SMART UPDATE: Retries thumbnail at frame 0 if seeking 1s fails (fixes short clips).
    """

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.cache_dir = self._get_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _find_ffmpeg(self) -> str:
        resolved = ResourcePathManager.get_ffmpeg_path()
        if not resolved:
            return None
        if Path(resolved).exists():
            return resolved
        from shutil import which
        return resolved if which(resolved) else None

    def _get_cache_dir(self) -> Path:
        """Resolve cache directory. Prefers Network Cache for Centralized Library."""
        try:
            from ut_vfx.core.infra.global_config import GlobalConfig
            server_root = GlobalConfig.server_root()
            
            # Use a centralized 'Cache' folder on the server
            cache_path = server_root / "Cache"
            
            # Ensure it exists (or try to create)
            try:
                cache_path.mkdir(parents=True, exist_ok=True)
                return cache_path
            except Exception as e:
                logging.warning(f"Failed to create Network Cache at {cache_path}: {e}")
                # Fallback to local if network is unwritable
                return GlobalConfig.local_cache_dir()
                
        except Exception as e:
            logging.exception(f"Error resolving cache path: {e}")
            return Path.cwd() / "Cache"

    def get_hash(self, path: Path) -> str:
        stat = path.stat()
        unique_str = f"{path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(unique_str.encode()).hexdigest()

    def generate_thumbnail(self, input_path: Path, is_seq: bool = False) -> Tuple[bool, Path]:
        """Generate JPG. Retries at frame 0 for short clips."""
        if not self.ffmpeg_path: return False, None

        file_hash = self.get_hash(input_path)
        output_thumb = self.cache_dir / f"{file_hash}_thumb.jpg"
        if output_thumb.exists(): return True, output_thumb

        if is_seq:
            try:
                import re
                stem = input_path.stem
                match = re.search(r'(\d+)$', stem)
                base = stem[:match.start()] if match else stem
                glob_pattern = f"{base}*{input_path.suffix}"
                
                from ut_vfx.utils.sequence_detector import detect_sequence, format_pattern_with_frame
                seq_info = detect_sequence(input_path.parent, glob_pattern)
                if seq_info:
                    # Thumbnail at 5th frame (or last frame if shorter)
                    target_frame = seq_info['first_frame'] + 4
                    if target_frame > seq_info['last_frame']:
                        target_frame = seq_info['last_frame']
                    
                    frame_name = format_pattern_with_frame(seq_info['pattern'], target_frame)
                    input_path = input_path.parent / frame_name
                    is_seq = False # Downgrade to single image for thumbnail gen
            except Exception as e:
                logging.debug(f"Failed to find sequence 5th frame for thumb: {e}")

        try:
            is_image_file = is_image(input_path.suffix.lower())
            
            # OPTIMIZATION: Use QImage for standard images (Faster/Native)
            if is_image_file and input_path.suffix.lower() not in ['.exr', '.dpx', '.tif', '.tiff']: # EXR/DPX still need FFmpeg
                try:
                    img = QImage(str(input_path))
                    if not img.isNull():
                        # Scale to 320
                        scaled = img.scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        scaled.save(str(output_thumb), "JPG", 80)
                        return True, output_thumb
                except Exception as exc:
                    logging.debug("QImage thumbnail path failed, falling back to ffmpeg: %s", exc)

            # ATTEMPT 1: Try seeking 1 second (skips slates/black frames)
            if not is_image_file:
                self._run_ffmpeg_thumb(input_path, output_thumb, seek_time="1")
            
            # ATTEMPT 2: If failed (or file too short), try Frame 0
            if not output_thumb.exists():
                self._run_ffmpeg_thumb(input_path, output_thumb, seek_time="0")

            return (True, output_thumb) if output_thumb.exists() else (False, None)


        except Exception as e:
            logging.exception(f"Thumb failed {input_path}: {e}")
            return False, None

    def _run_ffmpeg_thumb(self, input_path, output_path, seek_time="0"):
        """Helper to run the ffmpeg command."""
        cmd = [
            self.ffmpeg_path, "-y",
            "-ss", seek_time,
            "-i", str(input_path),
            "-vf", "scale=320:-2",
            "-vframes", "1",
            "-q:v", "5",
            str(output_path)
        ]
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Add timeout
        try:
            logging.debug(f"Executing FFmpeg Thumb Cmd: {' '.join(cmd)}")
            # Capture output to see error
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, timeout=15, text=True)
            if result.returncode != 0:
                 logging.error(f"FFmpeg Failed. Return Code: {result.returncode}")
                 logging.debug(f"FFmpeg Stderr: {result.stderr}")
            else:
                 logging.debug(f"FFmpeg finished cleanly for {input_path}")
                 
        except subprocess.TimeoutExpired:
            logging.error(f"FFmpeg thumb timeout: {input_path}")
            return  # Exit helper function after timeout
        except Exception as e:
            logging.exception(f"FFmpeg Exception: {e}")

    def generate_proxy(self, input_path: Path, is_seq: bool = False) -> Tuple[bool, Path]:
        if not self.ffmpeg_path: return False, None

        file_hash = self.get_hash(input_path)
        is_image_file = is_image(input_path.suffix.lower())
        
        # Determine output format (JPG for single images, MP4 for sequences/videos)
        if is_image_file and not is_seq:
            output_proxy = self.cache_dir / f"{file_hash}_proxy.jpg"
        else:
            output_proxy = self.cache_dir / f"{file_hash}_proxy.mp4"
            
        if output_proxy.exists(): return True, output_proxy

        try:
            cmd = [self.ffmpeg_path, "-y"]
            
            if is_image_file and not is_seq:
                # Generate a single 1920x1080 JPG proxy
                cmd.extend([
                    "-i", str(input_path),
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                    "-vframes", "1",
                    "-q:v", "2",  # High quality JPG
                    str(output_proxy)
                ])
            else:
                # Generate MP4 proxy
                if is_seq:
                    try:
                        import re
                        stem = input_path.stem
                        match = re.search(r'(\d+)$', stem)
                        base = stem[:match.start()] if match else stem
                        glob_pattern = f"{base}*{input_path.suffix}"
                        
                        from ut_vfx.utils.sequence_detector import detect_sequence
                        seq_info = detect_sequence(input_path.parent, glob_pattern)
                        if seq_info:
                            start_number = seq_info['first_frame']
                            pattern = seq_info['pattern']
                            cmd.extend(["-framerate", "24", "-start_number", str(start_number)])
                            cmd.extend(["-i", str(input_path.parent / pattern)])
                        else:
                            cmd.extend(["-i", str(input_path)])
                    except Exception as e:
                        logging.debug(f"Seq proxy error, fallback to single: {e}")
                        cmd.extend(["-i", str(input_path)])
                else:
                    cmd.extend(["-i", str(input_path)])
                
                cmd.extend([
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=yuv420p",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "28",
                    "-an",
                    str(output_proxy)
                ])

            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # LOW CPU PRIORITY
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW

            # Add timeout to prevent hang
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, creationflags=creationflags, timeout=60)
            return (True, output_proxy) if output_proxy.exists() else (False, None)

        except Exception as e:
            logging.exception(f"Proxy failed {input_path}: {e}")
            return False, None
            

# GLOBAL INSTANCE
proxy_manager = ProxyManager()
