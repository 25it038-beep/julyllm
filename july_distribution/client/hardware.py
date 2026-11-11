"""
HS AI SOLUTIONS â€” JULY CLIENT HARDWARE TELEMETRY & ENGINE DETECTION
Layer: HARDWARE DETECTOR (july_distribution.client.hardware)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
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


def get_detailed_hardware_telemetry(active_model_id: str = "july", runtime: Any = None) -> Dict[str, Any]:
    """
    Produces complete live hardware and resource consumption metrics:
    - Total, Available, and Used System RAM.
    - Total, Available, and Used VRAM.
    - GPU utilization percentage.
    - CPU utilization percentage.
    - Active Model identification and RAM/VRAM consumption.
    - Dynamic offload strategy and context length.
    """
    import subprocess
    ram = psutil.virtual_memory()
    total_ram_gb = round(ram.total / (1024**3), 2)
    avail_ram_gb = round(ram.available / (1024**3), 2)
    used_ram_gb = round((ram.total - ram.available) / (1024**3), 2)
    cpu_percent = psutil.cpu_percent(interval=0.05)
    cpu_threads = os.cpu_count() or 4

    gpu_name = "CPU Only"
    gpu_available = False
    vram_total_gb = 0.0
    vram_used_gb = 0.0
    vram_avail_gb = 0.0
    gpu_util_percent = 0.0

    # Query nvidia-smi for real-time telemetry if available
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split("\n")[0].split(",")]
            if len(parts) >= 5:
                gpu_name = parts[0]
                gpu_util_percent = float(parts[1])
                vram_total_gb = round(float(parts[2]) / 1024, 2)
                vram_used_gb = round(float(parts[3]) / 1024, 2)
                vram_avail_gb = round(float(parts[4]) / 1024, 2)
                gpu_available = True
    except Exception:
        pass

    # Fallback to PyTorch CUDA telemetry
    if not gpu_available:
        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(0)
                free_b, total_b = torch.cuda.mem_get_info(0)
                vram_total_gb = round(total_b / (1024**3), 2)
                vram_avail_gb = round(free_b / (1024**3), 2)
                vram_used_gb = round((total_b - free_b) / (1024**3), 2)
                gpu_util_percent = 0.0
        except Exception:
            pass

    # Model process memory consumption
    process_mem_gb = 0.0
    try:
        proc = psutil.Process()
        process_mem_gb = round(proc.memory_info().rss / (1024**3), 2)
    except Exception:
        pass

    # Model parameters & offload strategy
    model_norm = (active_model_id or "july").lower()
    if model_norm == "gravity":
        model_title = "GRAVITY (Heavyweight 7B+ Reasoning Model)"
        model_size_bytes = 5629108096
        total_layers = 32
        context_len = 4096
    else:
        model_title = "JULY (Lightweight 3B Fast AI)"
        model_size_bytes = 2019377888
        total_layers = 28
        context_len = 4096

    from .lifecycle import HardwareMemoryBudgeter
    budget = HardwareMemoryBudgeter.profile_and_budget(
        model_size_bytes=model_size_bytes,
        total_layers=total_layers,
        target_context=context_len,
        force_cpu=(not gpu_available)
    )

    return {
        "ram_total_gb": total_ram_gb,
        "ram_available_gb": avail_ram_gb,
        "ram_used_gb": used_ram_gb,
        "cpu_util_percent": cpu_percent,
        "cpu_threads": cpu_threads,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "gpu_util_percent": gpu_util_percent,
        "vram_total_gb": vram_total_gb,
        "vram_used_gb": vram_used_gb,
        "vram_available_gb": vram_avail_gb,
        "active_model": active_model_id.upper(),
        "active_model_title": model_title,
        "model_memory_gb": process_mem_gb,
        "offload_strategy": budget["offload_strategy"],
        "recommended_gpu_layers": budget["recommended_gpu_layers"],
        "total_layers": total_layers,
        "context_length": context_len,
        "recommended_threads": budget["recommended_threads"]
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

