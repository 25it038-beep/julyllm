"""
HS AI SOLUTIONS — CLI TERMINAL UI & STATUS BOX RENDERER
Layer: TERMINAL USER EXPERIENCE (july_distribution.client.ui_renderer)
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AI CLI (Persistent Dual-Model AI Environment)
"""

from __future__ import annotations
from typing import Dict, Any, Optional


def make_progress_bar(pct: float, width: int = 16) -> str:
    """Generates a solid UTF-8 progress bar (████████░░░░)."""
    clamped = max(0.0, min(100.0, pct))
    filled_len = int(round(width * clamped / 100.0))
    empty_len = width - filled_len
    return "█" * filled_len + "░" * empty_len


def render_cli_status_box(
    active_model: str = "JULY",
    gravity_status: str = "Ready",
    download_pct: float = 0.0,
    speed_mb: float = 0.0,
    ram_used_gb: float = 0.0,
    ram_total_gb: float = 16.0,
    vram_used_gb: float = 0.0,
    vram_total_gb: float = 6.0,
    voice_stt: bool = False,
    voice_tts: bool = False,
    voice_gender: str = "Female",
    width: int = 48
) -> str:
    """
    Renders the signature clean premium terminal card:
    ╭──────────────────────────────────────────────╮
    │               JULY AI CLI                    │
    │                                              │
    │ Active Model: JULY                           │
    │ Gravity: Downloading                         │
    │ Download: ███████████░░░░ 68%                │
    │ Speed: 3.2 MB/s                              │
    │ RAM: 5.4 / 16 GB                             │
    │ VRAM: 2.1 / 6 GB                             │
    │ Voice: Whisper + TTS (Female)                │
    ╰──────────────────────────────────────────────╯
    """
    inner_width = width - 2
    top = "╭" + "─" * inner_width + "╮"
    bottom = "╰" + "─" * inner_width + "╯"

    def format_row(content: str) -> str:
        padded = content + " " * max(0, inner_width - len(content))
        return f"│ {padded[:inner_width - 2]} │"

    def center_row(title: str) -> str:
        pad_left = (inner_width - len(title)) // 2
        pad_right = inner_width - len(title) - pad_left
        return "│" + " " * pad_left + title + " " * pad_right + "│"

    lines = [
        top,
        center_row("JULY AI CLI"),
        "│" + " " * inner_width + "│",
        format_row(f"Active Model: {active_model.upper()}"),
        format_row(f"Gravity: {gravity_status}"),
    ]

    # Show download metrics if Gravity is downloading
    if "download" in gravity_status.lower() or download_pct > 0.0 and download_pct < 100.0:
        bar = make_progress_bar(download_pct, width=15)
        lines.append(format_row(f"Download: {bar} {download_pct:.0f}%"))
        lines.append(format_row(f"Speed: {speed_mb:.1f} MB/s"))

    lines.append(format_row(f"RAM: {ram_used_gb:.1f} / {ram_total_gb:.0f} GB"))
    lines.append(format_row(f"VRAM: {vram_used_gb:.1f} / {vram_total_gb:.0f} GB"))

    # Voice status
    voice_parts = []
    if voice_stt:
        voice_parts.append("Whisper")
    else:
        voice_parts.append("Whisper [OFF]")

    tts_label = f"TTS ({voice_gender})" if voice_gender else "TTS"
    if voice_tts:
        voice_parts.append(tts_label)
    else:
        voice_parts.append(f"{tts_label} [OFF]")

    voice_summary = " + ".join(voice_parts)
    lines.append(format_row(f"Voice: {voice_summary}"))
    lines.append(bottom)

    return "\n".join(lines)


def render_hardware_card(telemetry: Dict[str, Any], width: int = 62) -> str:
    """Renders formatted /hardware telemetry report."""
    inner = width - 2
    top = "╭" + "─" * inner + "╮"
    div = "├" + "─" * inner + "┤"
    bottom = "╰" + "─" * inner + "╯"

    def row(label: str, val: str) -> str:
        txt = f"  {label:<24}: {val}"
        pad = max(0, inner - len(txt))
        return f"│{txt}{' ' * pad}│"

    def title(t: str) -> str:
        pad_l = (inner - len(t)) // 2
        pad_r = inner - len(t) - pad_l
        return "│" + " " * pad_l + t + " " * pad_r + "│"

    gpu_str = f"{telemetry.get('gpu_name', 'None')} ({telemetry.get('gpu_util_percent', 0.0):.1f}% util)"
    vram_str = f"{telemetry.get('vram_used_gb', 0.0):.2f} / {telemetry.get('vram_total_gb', 0.0):.2f} GB (Avail: {telemetry.get('vram_available_gb', 0.0):.2f} GB)"
    ram_str = f"{telemetry.get('ram_used_gb', 0.0):.2f} / {telemetry.get('ram_total_gb', 0.0):.2f} GB (Avail: {telemetry.get('ram_available_gb', 0.0):.2f} GB)"
    cpu_str = f"{telemetry.get('cpu_util_percent', 0.0):.1f}% ({telemetry.get('cpu_threads', 4)} threads)"
    model_str = f"{telemetry.get('active_model', 'JULY')} ({telemetry.get('model_memory_gb', 0.0):.2f} GB RAM RSS)"
    offload_str = f"{telemetry.get('offload_strategy', 'CPU')} ({telemetry.get('recommended_gpu_layers', 0)}/{telemetry.get('total_layers', 28)} layers)"

    lines = [
        top,
        title("JULY AI HARDWARE TELEMETRY & RESOURCE PROFILE"),
        div,
        row("Active Inference Model", model_str),
        row("Model Memory RSS", f"{telemetry.get('model_memory_gb', 0.0):.2f} GB"),
        row("CPU Utilization", cpu_str),
        row("System RAM Usage", ram_str),
        row("GPU Device", gpu_str),
        row("GPU VRAM Usage", vram_str),
        row("GPU Offloading", offload_str),
        row("Context Window", f"{telemetry.get('context_length', 4096):,} tokens"),
        bottom
    ]
    return "\n".join(lines)


def render_memory_card(telemetry: Dict[str, Any], persistent_count: int = 0, width: int = 60) -> str:
    """Renders formatted /memory report."""
    inner = width - 2
    top = "╭" + "─" * inner + "╮"
    div = "├" + "─" * inner + "┤"
    bottom = "╰" + "─" * inner + "╯"

    def row(label: str, val: str) -> str:
        txt = f"  {label:<24}: {val}"
        pad = max(0, inner - len(txt))
        return f"│{txt}{' ' * pad}│"

    def title(t: str) -> str:
        pad_l = (inner - len(t)) // 2
        pad_r = inner - len(t) - pad_l
        return "│" + " " * pad_l + t + " " * pad_r + "│"

    ram_str = f"{telemetry.get('ram_used_gb', 0.0):.2f} / {telemetry.get('ram_total_gb', 0.0):.2f} GB (Free: {telemetry.get('ram_available_gb', 0.0):.2f} GB)"
    vram_str = f"{telemetry.get('vram_used_gb', 0.0):.2f} / {telemetry.get('vram_total_gb', 0.0):.2f} GB (Free: {telemetry.get('vram_available_gb', 0.0):.2f} GB)"
    model_str = f"{telemetry.get('model_memory_gb', 0.0):.2f} GB active RSS ({telemetry.get('active_model', 'JULY')})"

    lines = [
        top,
        title("JULY RUNTIME MEMORY & VRAM PROFILE"),
        div,
        row("Total System RAM", f"{telemetry.get('ram_total_gb', 0.0):.2f} GB"),
        row("Used System RAM", f"{telemetry.get('ram_used_gb', 0.0):.2f} GB"),
        row("Available System RAM", f"{telemetry.get('ram_available_gb', 0.0):.2f} GB"),
        row("Total GPU VRAM", f"{telemetry.get('vram_total_gb', 0.0):.2f} GB"),
        row("Used GPU VRAM", f"{telemetry.get('vram_used_gb', 0.0):.2f} GB"),
        row("Available GPU VRAM", f"{telemetry.get('vram_available_gb', 0.0):.2f} GB"),
        row("Active Model Footprint", model_str),
        row("Persistent Memories", f"{persistent_count} stored items"),
        bottom
    ]
    return "\n".join(lines)


def render_gpu_card(telemetry: Dict[str, Any], width: int = 60) -> str:
    """Renders formatted /gpu report."""
    inner = width - 2
    top = "╭" + "─" * inner + "╮"
    div = "├" + "─" * inner + "┤"
    bottom = "╰" + "─" * inner + "╯"

    def row(label: str, val: str) -> str:
        txt = f"  {label:<24}: {val}"
        pad = max(0, inner - len(txt))
        return f"│{txt}{' ' * pad}│"

    def title(t: str) -> str:
        pad_l = (inner - len(t)) // 2
        pad_r = inner - len(t) - pad_l
        return "│" + " " * pad_l + t + " " * pad_r + "│"

    lines = [
        top,
        title("NVIDIA CUDA & GPU ACCELERATION PROFILE"),
        div,
        row("GPU Hardware Name", str(telemetry.get("gpu_name", "None"))),
        row("GPU Utilization", f"{telemetry.get('gpu_util_percent', 0.0):.1f}%"),
        row("Total GPU VRAM", f"{telemetry.get('vram_total_gb', 0.0):.2f} GB"),
        row("Used GPU VRAM", f"{telemetry.get('vram_used_gb', 0.0):.2f} GB"),
        row("Available GPU VRAM", f"{telemetry.get('vram_available_gb', 0.0):.2f} GB"),
        row("Offload Strategy", str(telemetry.get("offload_strategy", "CPU"))),
        row("Offloaded GPU Layers", f"{telemetry.get('recommended_gpu_layers', 0)} / {telemetry.get('total_layers', 28)} layers"),
        row("Max Context Window", f"{telemetry.get('context_length', 4096):,} tokens"),
        bottom
    ]
    return "\n".join(lines)
