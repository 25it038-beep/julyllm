"""
HS AI SOLUTIONS — JULY CLIENT CONFIGURATION
Layer: CLIENT CONFIGURATION (july_distribution.client.config)
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM 3B | Family: HS AI FAMILY

Manages per-user local settings in %USERPROFILE%\\.july\\config.json.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field


def get_default_july_dir() -> Path:
    """Returns local user configuration and state root directory."""
    custom_dir = os.getenv("JULY_CLIENT_HOME")
    if custom_dir:
        p = Path(custom_dir)
    else:
        p = Path.home() / ".july"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class ClientConfig:
    server_url: str = "http://127.0.0.1:8787"
    hardware_mode: str = "auto"  # auto, cuda, cpu
    context_length: int = 2048
    n_threads: int = 4
    n_batch: int = 64
    n_gpu_layers: int = 0
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    personality: str = "precision_engineer"
    system_prompt: str = (
        "You are JULY LLM, an advanced autonomous neural model developed by HS AI Solutions, "
        "founded by Harshan Seliyan. Deliver accurate, rigorous, and helpful answers."
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
            return cls(**data)
        except Exception:
            return cls()

    def save(self, config_file: Optional[Path] = None):
        p = config_file or (get_default_july_dir() / "config.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
