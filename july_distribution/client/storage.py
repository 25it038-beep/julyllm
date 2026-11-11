"""
HS AI SOLUTIONS — MODEL STORAGE ARCHITECTURE (PERMANENT & MEMORY-SAFE)
Layer: STORAGE MANAGEMENT (july_distribution.client.storage)
Organization: HS AI Solutions | Founder & Chief Architect: Harshan Seliyan
Product: JULY & GRAVITY DUAL-MODEL ARCHITECTURE

Implements Requirement 2:
- Maintain independent model directories:
    models/
      july/
        model.gguf
        manifest.json
        metadata.json
      gravity/
        model.gguf
        manifest.json
        metadata.json
- Never use a shared filename that allows one model to overwrite another.
- Keep verified model files permanently until the user explicitly requests deletion.
- Free RAM/CUDA memory during unloading WITHOUT deleting or corrupting GGUF files on disk.
"""

from __future__ import annotations
import os
import gc
import sys
import json
import ctypes
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

FILE_ATTRIBUTE_TEMPORARY = 0x00000100


def get_models_root_dir() -> Path:
    """Returns the persistent base directory for models."""
    env_dir = os.getenv("JULY_MODELS_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Check cwd / models
    cwd_models = Path.cwd() / "models"
    if cwd_models.exists() and cwd_models.is_dir():
        return cwd_models

    # Check script parent models
    script_models = Path(__file__).resolve().parent.parent.parent / "models"
    if script_models.exists() and script_models.is_dir():
        return script_models

    # Default to ~/.july/models
    user_models = Path.home() / ".july" / "models"
    user_models.mkdir(parents=True, exist_ok=True)
    return user_models


class PermanentModelStorage:
    """
    Manages independent, permanent on-disk model directories for July and Gravity.
    Selecting or unloading a model NEVER deletes, replaces, or unlinks these files.
    """

    TRUSTED_CHECKSUMS = {
        "july": "f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4",
        "gravity": "f24a90361aaac8cb3dce9f18b276b1444af106d205f411c4e674b58a9adf53c8"
    }

    EXPECTED_SIZES = {
        "july": 2019377888,
        "gravity": 5629108096
    }

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or get_models_root_dir()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def get_model_dir(self, model_id: str) -> Path:
        mid = model_id.lower().strip()
        mdir = self.root_dir / mid
        mdir.mkdir(parents=True, exist_ok=True)
        return mdir

    def get_model_file(self, model_id: str) -> Path:
        return self.get_model_dir(model_id) / "model.gguf"

    def get_manifest_file(self, model_id: str) -> Path:
        return self.get_model_dir(model_id) / "manifest.json"

    def get_metadata_file(self, model_id: str) -> Path:
        return self.get_model_dir(model_id) / "metadata.json"

    def is_model_present(self, model_id: str) -> bool:
        """Checks if model.gguf exists and matches the expected size."""
        f = self.get_model_file(model_id)
        if not f.exists() or not f.is_file():
            return False
        exp_size = self.EXPECTED_SIZES.get(model_id.lower().strip())
        if exp_size is not None and f.stat().st_size != exp_size:
            return False
        return f.stat().st_size > 0

    def verify_model_checksum(self, model_id: str, chunk_size: int = 16 * 1024 * 1024) -> Tuple[bool, str, str]:
        """
        Calculates SHA-256 of the permanent model file and compares against the trusted digest.
        Returns: (is_valid, actual_hash, expected_hash)
        """
        mid = model_id.lower().strip()
        f = self.get_model_file(mid)
        expected = self.TRUSTED_CHECKSUMS.get(mid, "")

        if not f.exists():
            return False, "", expected

        h = hashlib.sha256()
        with open(f, "rb") as fp:
            while True:
                buf = fp.read(chunk_size)
                if not buf:
                    break
                h.update(buf)

        actual = h.hexdigest().lower()
        is_valid = (actual == expected.lower()) if expected else True
        return is_valid, actual, expected

    def save_manifest(self, model_id: str, manifest_data: Dict[str, Any]):
        mf = self.get_manifest_file(model_id)
        with open(mf, "w", encoding="utf-8") as fp:
            json.dump(manifest_data, fp, indent=2)

    def load_manifest(self, model_id: str) -> Dict[str, Any]:
        mf = self.get_manifest_file(model_id)
        if mf.exists():
            try:
                with open(mf, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except Exception:
                pass
        return {}

    def save_metadata(self, model_id: str, metadata: Dict[str, Any]):
        mf = self.get_metadata_file(model_id)
        with open(mf, "w", encoding="utf-8") as fp:
            json.dump(metadata, fp, indent=2)

    def load_metadata(self, model_id: str) -> Dict[str, Any]:
        mf = self.get_metadata_file(model_id)
        if mf.exists():
            try:
                with open(mf, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except Exception:
                pass
        return {}

    def delete_model_permanently(self, model_id: str, explicit_user_confirmation: bool = False):
        """NEVER unlinks or deletes model files unless explicit_user_confirmation is True."""
        if not explicit_user_confirmation:
            raise PermissionError("Deleting a permanent model requires explicit user confirmation.")
        
        f = self.get_model_file(model_id)
        if f.exists():
            f.unlink(missing_ok=True)
        m = self.get_manifest_file(model_id)
        if m.exists():
            m.unlink(missing_ok=True)


class ClientEphemeralStorage:
    """
    Manages runtime memory operations without corrupting permanent disk files.
    """

    def __init__(self, auto_wipe_atexit: bool = False):
        self._active_files: set[Path] = set()

    def allocate_path(self, prefix: str = "july_ram_model") -> Path:
        permanent = PermanentModelStorage()
        if "gravity" in prefix.lower():
            return permanent.get_model_file("gravity")
        return permanent.get_model_file("july")

    def wipe_and_unlink(self, file_path: str | Path, allow_permanent_deletion: bool = False):
        """
        Safely unloads and frees RAM.
        CRITICAL ARCHITECTURAL SAFETY:
        Never unlinks or wipes files located in the permanent models directory unless allow_permanent_deletion=True!
        """
        p = Path(file_path).resolve()
        models_root = get_models_root_dir().resolve()

        try:
            if p.is_relative_to(models_root) and not allow_permanent_deletion:
                gc.collect()
                self.reclaim_os_memory()
                return
        except AttributeError:
            if str(models_root) in str(p) and not allow_permanent_deletion:
                gc.collect()
                self.reclaim_os_memory()
                return

        if p in self._active_files:
            self._active_files.remove(p)

        if p.exists() and allow_permanent_deletion:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

        gc.collect()
        self.reclaim_os_memory()

    def wipe_all(self):
        gc.collect()
        self.reclaim_os_memory()

    @staticmethod
    def reclaim_os_memory():
        """Frees working set memory back to Windows OS."""
        gc.collect()
        if sys.platform == "win32":
            try:
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.psapi.EmptyWorkingSet(handle)
            except Exception:
                pass
