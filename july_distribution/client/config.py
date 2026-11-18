"""
HS AI SOLUTIONS â€” JULY CLIENT CONFIGURATION
Layer: CLIENT CONFIGURATION (july_distribution.client.config)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Manages per-user local settings in %USERPROFILE%\\.july\\config.json.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field, fields


def get_default_july_dir() -> Path:
    """Returns local user configuration and state root directory."""
    custom_dir = os.getenv("JULY_CLIENT_HOME")
    if custom_dir:
        p = Path(custom_dir)
    elif os.getenv("JULY_PERSISTENT") == "1":
        # Check standard Tails Persistent Storage locations
        tails_persistent = Path.home() / "Persistent" / ".july"
        amnesia_persistent = Path("/home/amnesia/Persistent/.july")
        if tails_persistent.parent.exists() and os.access(str(tails_persistent.parent), os.W_OK):
            p = tails_persistent
        elif amnesia_persistent.parent.exists() and os.access(str(amnesia_persistent.parent), os.W_OK):
            p = amnesia_persistent
        else:
            p = Path.home() / ".july"
    else:
        p = Path.home() / ".july"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to /tmp if home is restricted
        p = Path("/tmp") / ".july"
        p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class ClientConfig:
    server_url: str = "https://julyllm.onrender.com"
    hardware_mode: str = "auto"  # auto, cuda, cpu
    context_length: int = 4096
    n_threads: int = 4
    n_batch: int = 512
    n_gpu_layers: int = 0
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 0  # 0 indicates unlimited generation up to context length
    enable_web_search: bool = True
    selected_model: str = "july"  # july, gravity, auto
    personality: str = "precision_engineer"
    thinking_mode: str = "expanded"  # expanded, collapsed, hidden
    thinking_level: str = "auto"     # auto, instant, balanced, deep
    adaptive_temperature: bool = True
    flash_attention: bool = True
    system_prompt: str = (
        "You are JULY LLM, an advanced autonomous neural model created by Harshan Seliyan and developed by HS AI Solutions. "
        "Deliver accurate, rigorous, and helpful answers."
    )
    chunk_size_bytes: int = 8 * 1024 * 1024

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "ClientConfig":
        p = config_file or (get_default_july_dir() / "config.json")
        if not p.exists():
            cfg = cls()
            cfg.save(p)
            return cfg

        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            valid_fields = {f.name for f in fields(cls)}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return cls(**filtered)
        except Exception:
            return cls()

    def save(self, config_file: Optional[Path] = None):
        p = config_file or (get_default_july_dir() / "config.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

