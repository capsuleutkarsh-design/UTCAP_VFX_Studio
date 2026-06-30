import os
import sys
import subprocess
import zipfile
import urllib.request
from pathlib import Path
import threading
import shutil

class DatabaseEngine:
    """
    Manages the embedded PostgreSQL instance.
    Handles initializing the cluster and starting/stopping.
    Assumes PostgreSQL binaries are bundled in the `bin/pgsql` directory.
    """
    
    def __init__(self, data_dir: str, port: int = 5440):
        self.data_dir = Path(data_dir)
        self.port = port
        
        # Resolve the bundled bin directory
        # When running in dev: ut_server/bin/pgsql/bin
        # When running compiled: _MEIPASS/ut_server/bin/pgsql/bin
        base_dir = Path(__file__).parent.parent
        if getattr(sys, 'frozen', False):
            base_dir = Path(getattr(sys, '_MEIPASS', sys.executable)) / "ut_server"
            
        self.bin_dir = base_dir / "bin" / "pgsql" / "bin"
        
        # Ensure base directories exist
        self.data_dir.parent.mkdir(parents=True, exist_ok=True)
        
    def is_installed(self) -> bool:
        """Check if Postgres binaries exist"""
        return (self.bin_dir / "postgres.exe").exists()

    def is_initialized(self) -> bool:
        """Check if the data directory has been initialized"""
        return (self.data_dir / "PG_VERSION").exists()

    def initialize_database(self, progress_callback=None):
        """Runs initdb.exe to create a new cluster."""
        if self.is_initialized():
            return True
            
        if progress_callback:
            progress_callback("Initializing Database Cluster...")

        initdb_exe = str(self.bin_dir / "initdb.exe")
        cmd = [
            initdb_exe,
            "-D", str(self.data_dir),
            "-U", "postgres",
            "-A", "trust", # Trust local connections
            "-E", "utf8"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self._configure_network_access()
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"initdb failed:\n{e.stderr}")

    def _configure_network_access(self):
        """Edits postgresql.conf and pg_hba.conf to allow network access."""
        conf_path = self.data_dir / "postgresql.conf"
        hba_path = self.data_dir / "pg_hba.conf"
        
        # Enable listening on all interfaces
        if conf_path.exists():
            with open(conf_path, 'a') as f:
                f.write("\n# --- UT CENTRAL SERVER CONFIG ---\n")
                f.write("listen_addresses = '*'\n")
                f.write(f"port = {self.port}\n")
        
        # Allow all IP ranges (Zero-config LAN trust)
        if hba_path.exists():
            with open(hba_path, 'a') as f:
                f.write("\n# --- UT CENTRAL SERVER CONFIG ---\n")
                f.write("host    all             all             0.0.0.0/0               trust\n")
                f.write("host    all             all             ::/0                    trust\n")

    def start(self, progress_callback=None):
        """Starts the PostgreSQL server using pg_ctl."""
        if not self.is_installed():
            raise Exception(f"PostgreSQL binaries not found at {self.bin_dir}")
            
        is_first_run = not self.is_initialized()
        if is_first_run:
            self.initialize_database(progress_callback)
        else:
            self._update_port_in_conf()
            
        if progress_callback:
            progress_callback("Starting Database Server...")

        pg_ctl_exe = str(self.bin_dir / "pg_ctl.exe")
        log_file = str(self.data_dir.parent / "pg_server.log")
        
        cmd = [
            pg_ctl_exe,
            "-D", str(self.data_dir),
            "-l", log_file,
            "start"
        ]
        
        try:
            # Prevent capture_output=True which hangs on Windows due to pipe inheritance
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags, check=True)
            
            if is_first_run:
                if progress_callback:
                    progress_callback("Waiting for database cluster...")
                import time
                time.sleep(2)  # Give postgres a moment to start accepting connections
                
            # Always ensure the ut_vfx database exists (in case it failed on first run or was deleted)
            createdb_exe = str(self.bin_dir / "createdb.exe")
            cmd_createdb = [
                createdb_exe,
                "-U", "postgres",
                "-p", str(self.port),
                "ut_vfx"
            ]
            # Try to create the database, but don't crash if it already exists somehow
            # We add a tiny sleep for non-first runs just in case pg_ctl returned slightly too fast
            if not is_first_run:
                import time
                time.sleep(1)
            subprocess.run(cmd_createdb, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to start server. Check log at {log_file}")

    def stop(self, progress_callback=None):
        """Gracefully stops the PostgreSQL server."""
        if not self.is_installed() or not self.is_initialized():
            return True
            
        if progress_callback:
            progress_callback("Stopping Database Server...")

        pg_ctl_exe = str(self.bin_dir / "pg_ctl.exe")
        
        cmd = [
            pg_ctl_exe,
            "-D", str(self.data_dir),
            "stop",
            "-m", "fast"
        ]
        
        try:
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags, check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to stop server. Check log at {self.data_dir.parent}/pg_server.log")

    def _update_port_in_conf(self):
        import re
        conf_path = self.data_dir / "postgresql.conf"
        if conf_path.exists():
            with open(conf_path, 'r') as f:
                content = f.read()
            content = re.sub(r"port\s*=\s*\d+", f"port = {self.port}", content)
            with open(conf_path, 'w') as f:
                f.write(content)
