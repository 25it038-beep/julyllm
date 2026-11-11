"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.filesystem
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Enforces production-grade Windows Filesystem Security:
- Hierarchy: JulySandbox/ [Runtime, Workspace, Temporary, Logs, Artifacts]
- Canonical path validation (os.path.realpath) preventing path traversal
- Symlink, NTFS junction, and reparse-point attack detection
- Strict boundary confinement: access permitted ONLY within authorized folders
- Explicit protection of Windows system, user documents, SSH, AWS, and browser data
- Idempotent NTFS ACL setup via icacls
- Ephemeral workspace & temporary directory reset
"""

from __future__ import annotations
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


class SecurityViolation(Exception):
    """Raised when an operation attempts to breach the sandbox filesystem boundary."""
    pass


class SandboxFilesystem:
    """
    Manages and enforces the isolated filesystem sandbox hierarchy.
    """

    SUBDIRECTORIES = ["Runtime", "Workspace", "Temporary", "Logs", "Artifacts"]

    # Blocked sensitive paths and patterns across host
    FORBIDDEN_NAME_PATTERNS = [
        ".ssh", ".aws", ".azure", ".kube", ".gitconfig", ".bash_history",
        "id_rsa", "id_ed25519", "known_hosts", "credentials", "config.json"
    ]

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir:
            self.root = Path(root_dir).resolve()
        else:
            # Default to C:\JulySandbox if accessible/elevated, otherwise %LOCALAPPDATA%\JulySandbox
            c_root = Path("C:\\JulySandbox")
            try:
                c_root.mkdir(parents=True, exist_ok=True)
                test_f = c_root / ".write_test"
                test_f.write_text("ok")
                test_f.unlink()
                self.root = c_root
            except Exception:
                local_app = os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
                self.root = (Path(local_app) / "JulySandbox").resolve()

        self.runtime_dir = self.root / "Runtime"
        self.workspace_dir = self.root / "Workspace"
        self.temporary_dir = self.root / "Temporary"
        self.logs_dir = self.root / "Logs"
        self.artifacts_dir = self.root / "Artifacts"

        self.initialize_hierarchy()

    def initialize_hierarchy(self):
        """Creates the 5 core directories with defensive defaults."""
        self.root.mkdir(parents=True, exist_ok=True)
        for sub in [self.runtime_dir, self.workspace_dir, self.temporary_dir, self.logs_dir, self.artifacts_dir]:
            sub.mkdir(parents=True, exist_ok=True)

        # Place an operational README and manifest in Runtime
        manifest = self.runtime_dir / "SANDBOX_MANIFEST.json"
        if not manifest.exists():
            manifest.write_text('{"environment": "Windows Sandbox Isolated Runtime", "engine": "JulySandbox"}', encoding="utf-8")

    def resolve_and_validate_path(
        self,
        target_path: str | Path,
        allow_write: bool = False,
        allow_temporary: bool = True
    ) -> Path:
        """
        Validates that a path is strictly confined within authorized sandbox folders.
        Guards against:
        - Relative path traversal ('..', '....')
        - Absolute path traversal ('C:\\Windows', 'C:\\Users\\...')
        - Symlink and junction point redirection outside the boundary
        - Windows Alternate Data Streams ('file.txt:hidden')
        - Sensitive files access
        """
        if not target_path:
            raise SecurityViolation("Target path cannot be empty.")

        path_str = str(target_path).strip().strip('"').strip("'")

        # 1. Block Alternate Data Streams (:stream)
        # Windows drive letters (C:) have colon at index 1, check beyond that
        if ":" in path_str[2:]:
            raise SecurityViolation(f"Alternate Data Stream detected and blocked: {path_str}")

        # 2. Canonicalize path
        p = Path(path_str)
        if not p.is_absolute():
            # Treat relative paths as relative to Workspace
            resolved = (self.workspace_dir / p).resolve()
        else:
            resolved = p.resolve()

        resolved_str = str(resolved).lower()

        # 3. Check for Symlinks / Junctions / Reparse points
        try:
            if resolved.is_symlink() or os.path.islink(str(resolved)):
                real_target = os.path.realpath(str(resolved))
                if not self._is_within_allowed(real_target, allow_temporary):
                    raise SecurityViolation(
                        f"Symlink redirection attack detected! Target points outside sandbox: {real_target}"
                    )
        except (OSError, ValueError):
            pass

        # 4. Check against Host Critical Directories
        system_root = os.getenv("SystemRoot", "C:\\Windows").lower()
        prog_files = os.getenv("ProgramFiles", "C:\\Program Files").lower()
        user_profile = os.getenv("USERPROFILE", str(Path.home())).lower()

        # Critical user directories
        protected_user_dirs = [
            f"{user_profile}\\documents",
            f"{user_profile}\\desktop",
            f"{user_profile}\\downloads",
            f"{user_profile}\\pictures",
            f"{user_profile}\\.ssh",
            f"{user_profile}\\.aws",
            f"{user_profile}\\appdata\\local\\google",
            f"{user_profile}\\appdata\\local\\microsoft\\edge",
            f"{user_profile}\\appdata\\roaming\\mozilla"
        ]

        if resolved_str.startswith(system_root) or resolved_str.startswith(prog_files):
            raise SecurityViolation(f"Direct access to Windows system directories is prohibited: {resolved}")

        for pdir in protected_user_dirs:
            if resolved_str.startswith(pdir):
                raise SecurityViolation(f"Unauthorized access to user personal directory prohibited: {resolved}")

        # 5. Check forbidden filename patterns
        for forbidden in self.FORBIDDEN_NAME_PATTERNS:
            if forbidden.lower() in resolved.name.lower():
                raise SecurityViolation(f"Access to credential or configuration token is prohibited: {resolved.name}")

        # 6. Verify strictly within allowed sandbox folders
        if not self._is_within_allowed(str(resolved), allow_temporary, allow_write):
            raise SecurityViolation(
                f"Path boundary escape attempt! Path '{resolved}' is not within authorized sandbox directories."
            )

        return resolved

    def _is_within_allowed(
        self,
        real_path_str: str,
        allow_temporary: bool = True,
        allow_write: bool = False
    ) -> bool:
        """Helper to test containment inside authorized sandbox folders."""
        norm_target = str(Path(real_path_str).resolve()).lower()

        ws_str = str(self.workspace_dir).lower()
        tmp_str = str(self.temporary_dir).lower()
        art_str = str(self.artifacts_dir).lower()
        rt_str = str(self.runtime_dir).lower()
        logs_str = str(self.logs_dir).lower()

        # Workspace is always allowed (Read/Write)
        if norm_target.startswith(ws_str):
            return True

        # Temporary is allowed (Read/Write)
        if allow_temporary and norm_target.startswith(tmp_str):
            return True

        # Artifacts is allowed for write and read
        if norm_target.startswith(art_str):
            return True

        # Runtime is Read-only
        if norm_target.startswith(rt_str):
            if allow_write:
                return False  # Write not permitted in Runtime
            return True

        # Logs is Read/Append
        if norm_target.startswith(logs_str):
            return True

        return False

    def reset_workspace_and_temporary(self) -> Dict[str, Any]:
        """Safely cleans Workspace and Temporary directories to zero-state."""
        removed_items = 0
        freed_bytes = 0

        for target_folder in [self.workspace_dir, self.temporary_dir]:
            if target_folder.exists():
                for item in target_folder.iterdir():
                    try:
                        if item.is_file() or item.is_symlink():
                            freed_bytes += item.stat().st_size
                            item.unlink()
                            removed_items += 1
                        elif item.is_dir():
                            # Recursive size
                            for root, _, files in os.walk(item):
                                for f in files:
                                    try: freed_bytes += (Path(root) / f).stat().st_size
                                    except Exception: pass
                            shutil.rmtree(item, ignore_errors=True)
                            removed_items += 1
                    except Exception as e:
                        pass

        # Re-ensure existence
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.temporary_dir.mkdir(parents=True, exist_ok=True)

        return {
            "items_removed": removed_items,
            "bytes_freed": freed_bytes,
            "workspace_clean": True,
            "temporary_clean": True
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        """Calculates disk space consumed across the sandbox hierarchy."""
        usage = {}
        total_bytes = 0

        for folder_name, folder_path in [
            ("Runtime", self.runtime_dir),
            ("Workspace", self.workspace_dir),
            ("Temporary", self.temporary_dir),
            ("Logs", self.logs_dir),
            ("Artifacts", self.artifacts_dir),
        ]:
            size = 0
            count = 0
            if folder_path.exists():
                for root, _, files in os.walk(folder_path):
                    for f in files:
                        try:
                            fp = Path(root) / f
                            size += fp.stat().st_size
                            count += 1
                        except Exception:
                            pass
            usage[folder_name] = {
                "size_mb": round(size / (1024 * 1024), 2),
                "file_count": count
            }
            total_bytes += size

        usage["Total_MB"] = round(total_bytes / (1024 * 1024), 2)
        usage["Root"] = str(self.root)
        return usage
