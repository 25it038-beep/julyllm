"""
HS AI SOLUTIONS — OS & LINUX DISTRIBUTION DETECTOR
Layer: SYSTEM DETECTION (july_distribution.client.os_detector)
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Tails OS (Amnesia) & Native Linux

Specialized detection for:
- Tails OS (Amnesic Incognito Live System)
- Debian GNU/Linux
- Ubuntu Linux
- Kali Linux
- Generic Linux distributions & Windows/macOS
- Tails Persistent Storage detection (/home/amnesia/Persistent, /live/persistence)
"""

from __future__ import annotations
import os
import sys
import getpass
import platform
from pathlib import Path
from typing import Dict, Any, Optional


def detect_os_release(custom_path: Optional[Path] = None) -> Dict[str, str]:
    """Parses /etc/os-release if available on Linux."""
    data: Dict[str, str] = {}
    if custom_path:
        os_release_paths = [custom_path]
    else:
        os_release_paths = [Path("/etc/os-release"), Path("/usr/lib/os-release")]
    for p in os_release_paths:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        data[k] = v
                break
            except Exception:
                pass
    return data


class OSDetector:
    """Provides authoritative system, distribution, and privacy environment telemetry."""

    @staticmethod
    def is_linux() -> bool:
        return sys.platform.startswith("linux")

    @staticmethod
    def is_windows() -> bool:
        return sys.platform == "win32"

    @staticmethod
    def is_macos() -> bool:
        return sys.platform == "darwin"

    @classmethod
    def get_distro_info(cls) -> Dict[str, Any]:
        """Detects distribution name, ID, and version."""
        if not cls.is_linux():
            return {
                "id": sys.platform,
                "name": platform.system(),
                "version": platform.release(),
                "is_tails": False,
                "is_debian": False,
                "is_ubuntu": False,
                "is_kali": False,
            }

        os_rel = detect_os_release()
        distro_id = os_rel.get("ID", "").lower()
        distro_like = os_rel.get("ID_LIKE", "").lower()
        distro_name = os_rel.get("NAME", "Linux")
        version_id = os_rel.get("VERSION_ID", "")
        tails_product = os_rel.get("TAILS_PRODUCT_NAME", "")

        # Tails OS Detection
        is_tails = (
            distro_id == "tails"
            or "tails" in distro_name.lower()
            or bool(tails_product)
            or Path("/etc/amnesia/version").exists()
            or Path("/etc/tails/version").exists()
            or (getpass.getuser() == "amnesia" and Path("/live").exists())
        )

        is_debian = (distro_id == "debian" or "debian" in distro_like) and not is_tails
        is_ubuntu = distro_id == "ubuntu" or "ubuntu" in distro_like
        is_kali = distro_id == "kali" or "kali" in distro_like

        if is_tails:
            distro_name = "Tails (The Amnesic Incognito Live System)"
            if not version_id:
                for vp in [Path("/etc/amnesia/version"), Path("/etc/tails/version")]:
                    if vp.exists():
                        try:
                            version_id = vp.read_text().strip()
                            break
                        except Exception:
                            pass

        return {
            "id": "tails" if is_tails else distro_id or "linux",
            "name": distro_name,
            "version": version_id,
            "is_tails": is_tails,
            "is_debian": is_debian,
            "is_ubuntu": is_ubuntu,
            "is_kali": is_kali,
            "os_release": os_rel,
        }

    @classmethod
    def is_tails(cls) -> bool:
        return cls.get_distro_info().get("is_tails", False)

    @classmethod
    def get_tails_persistence_info(cls) -> Dict[str, Any]:
        """
        Detects Tails Persistent Storage status:
        - Check /live/persistence/TailsData_unlocked
        - Check /home/amnesia/Persistent or $HOME/Persistent
        """
        is_tails = cls.is_tails()
        if not is_tails:
            return {
                "supported": False,
                "unlocked": False,
                "path": None,
                "writable": False,
            }

        candidate_paths = [
            Path("/home/amnesia/Persistent"),
            Path.home() / "Persistent",
            Path("/live/persistence/TailsData_unlocked"),
        ]

        unlocked_path: Optional[Path] = None
        writable = False

        for cp in candidate_paths:
            if cp.exists() and cp.is_dir():
                unlocked_path = cp
                writable = os.access(str(cp), os.W_OK)
                break

        # Also check /live mount
        live_persistence = Path("/live/persistence/TailsData_unlocked").exists()

        return {
            "supported": True,
            "unlocked": bool(unlocked_path) or live_persistence,
            "path": str(unlocked_path) if unlocked_path else None,
            "writable": writable,
        }

    @classmethod
    def get_environment_summary(cls) -> Dict[str, Any]:
        """Returns comprehensive environment dictionary for banners and diagnostics."""
        distro = cls.get_distro_info()
        is_t = distro.get("is_tails", False)
        pers = cls.get_tails_persistence_info() if is_t else {}

        current_user = getpass.getuser()
        hostname = platform.node() or "amnesia" if is_t else platform.node()

        return {
            "system": platform.system(),
            "kernel": platform.release(),
            "python_version": platform.python_version(),
            "distro_id": distro.get("id"),
            "distro_name": distro.get("name"),
            "distro_version": distro.get("version"),
            "is_tails": is_t,
            "is_debian": distro.get("is_debian", False),
            "is_ubuntu": distro.get("is_ubuntu", False),
            "is_kali": distro.get("is_kali", False),
            "persistence": pers,
            "user": current_user,
            "hostname": "amnesia" if is_t else hostname,
            "is_root": os.geteuid() == 0 if hasattr(os, "geteuid") else False,
        }
