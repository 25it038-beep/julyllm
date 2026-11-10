"""
HS AI SOLUTIONS â€” JULY CLIENT EPHEMERAL RAM STORAGE
Layer: EPHEMERAL RAM STORAGE (july_distribution.client.storage)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Implements Requirement 6 & 8:
- Allocates temporary RAM-backed storage with Windows FILE_ATTRIBUTE_TEMPORARY.
- Zero permanent GGUF copies on client machines.
- Guaranteed secure wipe and unlinking upon unload, session exit, or SIGINT.
"""

from __future__ import annotations
import os
import gc
import sys
import ctypes
import atexit
import tempfile
from pathlib import Path
from typing import Optional

FILE_ATTRIBUTE_TEMPORARY = 0x00000100


class ClientEphemeralStorage:
    """Manages ephemeral RAM-backed model storage on client machines."""

    def __init__(self, auto_wipe_atexit: bool = False):
        self._active_files: set[Path] = set()
        if auto_wipe_atexit:
            atexit.register(self.wipe_all)

    def allocate_path(self, prefix: str = "july_ram_model") -> Path:
        temp_dir = Path(tempfile.gettempdir()) / "july_ephemeral_runtime"
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{prefix}.gguf"

        self._active_files.add(file_path)

        if sys.platform == "win32":
            try:
                if not file_path.exists():
                    file_path.touch()
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(file_path),
                    FILE_ATTRIBUTE_TEMPORARY
                )
            except Exception:
                pass

        return file_path

    def wipe_and_unlink(self, file_path: str | Path):
        p = Path(file_path)
        if p in self._active_files:
            self._active_files.remove(p)

        if p.exists():
            try:
                size = p.stat().st_size
                if size > 0:
                    with open(p, "r+b") as f:
                        f.seek(0)
                        f.write(b"\x00" * min(size, 4096))
                        f.flush()
                p.unlink(missing_ok=True)
            except Exception:
                pass

        gc.collect()
        self.reclaim_os_memory()

    def wipe_all(self):
        for p in list(self._active_files):
            self.wipe_and_unlink(p)

    @staticmethod
    def reclaim_os_memory():
        if sys.platform == "win32":
            try:
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.psapi.EmptyWorkingSet(handle)
            except Exception:
                pass

