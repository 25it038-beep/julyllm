"""
HS AI SOLUTIONS — JULY CLIENT HARDWARE TELEMETRY & ENGINE DETECTION
Layer: HARDWARE DETECTOR (july_distribution.client.hardware)
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM 3B | Family: HS AI FAMILY

Performs genuine hardware profiling on client machines:
- CPU cores, threads, and utilization.
- Physical RAM total, available, and percentage.
- NVIDIA CUDA detection and GPU VRAM telemetry.
- Dynamic layer offloading recommendations.
"""

from __future__ import annotations
import os
import psutil
from typing import Dict, Any


def detect_client_hardware() -> Dict[str, Any]:
    """Detects CPU, RAM, and GPU capabilities on the host."""
    cpu_count = os.cpu_count() or 4
    ram = psutil.virtual_memory()

    gpu_available = False
    gpu_name = "None (CPU Execution)"
    vram_total_mb = 0.0
    vram_free_mb = 0.0

    # 1. Try PyTorch CUDA if available
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            gpu_name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            vram_total_mb = round(props.total_memory / (1024 * 1024), 2)
            mem_allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)
            vram_free_mb = round(vram_total_mb - mem_allocated, 2)
    except Exception:
        pass

    # Recommended thread count: physical cores or min(cpu_count, 6)
    recommended_threads = max(1, min(cpu_count, 6))

    # Recommended GPU layers: if GPU VRAM >= 4GB, offload 28 layers (entire 3B model)
    # If 2-3 GB, offload 16 layers. If CPU-only, 0 layers.
    if gpu_available and vram_total_mb >= 4000:
        recommended_gpu_layers = 28
    elif gpu_available and vram_total_mb >= 2000:
        recommended_gpu_layers = 14
    else:
        recommended_gpu_layers = 0

    return {
        "cpu_threads": cpu_count,
        "recommended_threads": recommended_threads,
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "ram_available_gb": round(ram.available / (1024**3), 2),
        "ram_used_percent": ram.percent,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "vram_total_mb": vram_total_mb,
        "vram_free_mb": vram_free_mb,
        "recommended_gpu_layers": recommended_gpu_layers
    }


def get_device_identity() -> Dict[str, str]:
    """Generates a stable hardware device identifier on Windows."""
    import platform
    import hashlib
    import socket

    hostname = socket.gethostname()
    system = platform.system()
    release = platform.release()
    proc = platform.processor() or "GenericCPU"

    # Compute deterministic SHA-256 device ID
    raw = f"{hostname}|{system}|{release}|{proc}".encode("utf-8")
    device_id = f"dev_{hashlib.sha256(raw).hexdigest()[:24]}"

    return {
        "device_id": device_id,
        "device_name": hostname,
        "os_version": f"{system} {release}"
    }
