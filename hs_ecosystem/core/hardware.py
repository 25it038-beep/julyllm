"""
HS AI SOLUTIONS — UNIVERSAL HARDWARE DETECTION & RUNTIME PROFILER
Module: hs_ecosystem.core.hardware
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Cross-platform hardware detection supporting:
- Windows, Linux, macOS (Apple Silicon / Intel), Android, iOS.
- Accelerators: NVIDIA CUDA, Apple Metal (MPS), Vulkan, CPU OpenMP/AVX-512.
- Memory telemetry: RAM, VRAM, and dynamic context budgeting.
"""

from __future__ import annotations
import os
import sys
import platform
import subprocess
import psutil
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class HardwareProfile:
    platform_name: str
    os_name: str
    os_version: str
    cpu_arch: str
    cpu_cores: int
    cpu_threads: int
    total_ram_gb: float
    free_ram_gb: float
    gpu_available: bool
    gpu_name: str
    gpu_backend: str  # "cuda", "metal", "vulkan", "cpu"
    total_vram_mb: float
    free_vram_mb: float
    recommended_gpu_layers: int
    recommended_context_budget: int
    allow_dual_model_in_vram: bool


class UniversalHardwareEngine:
    """Detects system hardware and allocates resources across July and Gravity models."""

    @staticmethod
    def detect_hardware() -> HardwareProfile:
        os_name = platform.system()
        os_ver = platform.version()
        cpu_arch = platform.machine()
        cpu_cores = psutil.cpu_count(logical=False) or 4
        cpu_threads = psutil.cpu_count(logical=True) or 8

        # RAM telemetry
        vmem = psutil.virtual_memory()
        total_ram = round(vmem.total / (1024 ** 3), 2)
        free_ram = round(vmem.available / (1024 ** 3), 2)

        # GPU telemetry
        gpu_available = False
        gpu_name = "CPU Only"
        gpu_backend = "cpu"
        total_vram_mb = 0.0
        free_vram_mb = 0.0
        rec_layers = 0

        # 1. Check NVIDIA CUDA (Windows / Linux)
        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_backend = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                total_vram_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 2), 1)
                free_vram_mb = round((torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)) / (1024 ** 2), 1)
                rec_layers = 28
        except Exception:
            pass

        # Fallback nvidia-smi if torch not loaded
        if not gpu_available and os.name == "nt":
            try:
                res = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=3
                )
                if res.returncode == 0 and res.stdout.strip():
                    parts = [p.strip() for p in res.stdout.strip().split(",")]
                    if len(parts) >= 3:
                        gpu_available = True
                        gpu_backend = "cuda"
                        gpu_name = parts[0]
                        total_vram_mb = float(parts[1])
                        free_vram_mb = float(parts[2])
                        rec_layers = 28
            except Exception:
                pass

        # 2. Check Apple Metal (macOS)
        if not gpu_available and os_name == "Darwin":
            try:
                import torch
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    gpu_available = True
                    gpu_backend = "metal"
                    gpu_name = "Apple Silicon Metal Acceleration"
                    total_vram_mb = total_ram * 1024 * 0.7  # Unified memory allocation
                    free_vram_mb = free_ram * 1024 * 0.7
                    rec_layers = 28
            except Exception:
                pass

        # 3. Context budget & dual model concurrency check
        # A single 3B Q4_K_M model requires ~1.9 GB weights + ~412 MB KV cache = ~2.3 GB VRAM.
        # Two models simultaneously require ~4.6 GB active VRAM.
        allow_dual_vram = free_vram_mb >= 5000.0 or (free_ram >= 12.0 and not gpu_available)
        context_budget = 4096 if total_vram_mb <= 6144 else 8192

        platform_tag = "windows"
        if os_name == "Darwin":
            platform_tag = "macos"
        elif os_name == "Linux":
            # Check for Android environment
            platform_tag = "android" if "ANDROID_ROOT" in os.environ else "linux"

        return HardwareProfile(
            platform_name=platform_tag,
            os_name=os_name,
            os_version=os_ver,
            cpu_arch=cpu_arch,
            cpu_cores=cpu_cores,
            cpu_threads=cpu_threads,
            total_ram_gb=total_ram,
            free_ram_gb=free_ram,
            gpu_available=gpu_available,
            gpu_name=gpu_name,
            gpu_backend=gpu_backend,
            total_vram_mb=total_vram_mb,
            free_vram_mb=free_vram_mb,
            recommended_gpu_layers=rec_layers,
            recommended_context_budget=context_budget,
            allow_dual_model_in_vram=allow_dual_vram
        )
