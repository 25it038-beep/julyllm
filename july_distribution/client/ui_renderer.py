"""
HS AI SOLUTIONS — CLI TERMINAL UI & STATUS BOX RENDERER
Layer: TERMINAL USER EXPERIENCE (july_distribution.client.ui_renderer)
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AI CLI (Persistent Dual-Model AI Environment)
"""

from __future__ import annotations
import math
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


def make_audio_waveform(level: float, length: int = 24, phase: float = 0.0) -> str:
    """Generates an animated audio waveform string reacting to real-time RMS energy levels."""
    chars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    wave = []
    boosted = min(1.0, max(0.0, level * 5.5 + (0.05 if level > 0.005 else 0.0)))
    for i in range(length):
        sine = 0.5 + 0.5 * math.sin(phase + i * 0.42) * math.cos(phase * 0.6 + i * 0.28)
        scaled = min(1.0, max(0.0, sine * boosted))
        idx = int(scaled * (len(chars) - 1))
        wave.append(chars[idx])
    return "".join(wave)


def render_live_box(
    state: str = "Listening",
    active_model: str = "JULY",
    voice_engine: str = "TTS (Female)",
    recognition_engine: str = "Whisper",
    language: str = "Auto Detect",
    style: str = "Natural",
    user_prompt: str = "",
    ai_response: str = "",
    level: float = 0.0,
    waveform_phase: float = 0.0,
    metrics: Optional[Dict[str, float]] = None,
    audio_state: str = "Listening",
    width: int = 54
) -> str:
    """
    Renders signature live voice conversational terminal interface card:
    ╭──────────────────────────────────────────────────╮
    │                 JULY LIVE                        │
    │                                                  │
    │  ● LIVE [LISTENING]                              │
    │                                                  │
    │  Active Model: JULY                              │
    │  Voice: TTS (Female)                             │
    │  Recognition: Whisper                            │
    │  Language: Auto Detect                           │
    │  Style: Natural                                  │
    │                                                  │
    │              Listening...                        │
    │                                                  │
    │        ▂▃▅▆██▆▅▃▂   ▂▃▄▅▃▂                       │
    │                                                  │
    │  You: ...                                        │
    │                                                  │
    │  July: ...                                       │
    │                                                  │
    │  Latency: 0.8s                                   │
    │  Audio: Playing                                  │
    ╰──────────────────────────────────────────────────╯
    """
    inner = width - 2
    top = "╭" + "─" * inner + "╮"
    bottom = "╰" + "─" * inner + "╯"

    def row(txt: str) -> str:
        padded = txt + " " * max(0, inner - len(txt) - 2)
        return f"│ {padded[:inner - 2]} │"

    def center(txt: str) -> str:
        pad_l = (inner - len(txt)) // 2
        pad_r = inner - len(txt) - pad_l
        return "│" + " " * max(0, pad_l) + txt + " " * max(0, pad_r) + "│"

    lines = [
        top,
        center("JULY LIVE"),
        "│" + " " * inner + "│",
        row(f" ● LIVE [{state.upper()}]"),
        "│" + " " * inner + "│",
        row(f" Active Model: {active_model.upper()}"),
        row(f" Voice: {voice_engine}"),
        row(f" Recognition: {recognition_engine}"),
        row(f" Language: {language}"),
        row(f" Style: {style}"),
        "│" + " " * inner + "│",
    ]

    # Status caption
    caption = f"{state}..."
    lines.append(center(caption))

    # Animated waveform
    waveform = make_audio_waveform(level, length=min(28, inner - 8), phase=waveform_phase)
    lines.append(center(f"[{waveform}]"))
    lines.append("│" + " " * inner + "│")

    # User speech preview
    if user_prompt:
        u_txt = user_prompt if len(user_prompt) <= inner - 8 else user_prompt[:inner - 11] + "..."
        lines.append(row(f" You: {u_txt}"))
        lines.append("│" + " " * inner + "│")

    # AI response preview
    if ai_response:
        ai_clean = ai_response.replace("\n", " ").strip()
        a_txt = ai_clean if len(ai_clean) <= inner - 9 else ai_clean[:inner - 12] + "..."
        model_name = "Gravity" if active_model.lower() == "gravity" else "July"
        lines.append(row(f" {model_name}: {a_txt}"))
        lines.append("│" + " " * inner + "│")

    # Metrics
    m = metrics or {}
    tot_lat = m.get("total_latency_sec", 0.0)
    ft_lat = m.get("first_token_sec", 0.0)
    fa_lat = m.get("first_audio_sec", 0.0)
    if tot_lat > 0.0:
        lat_str = f"Latency: {tot_lat:.2f}s (Token: {ft_lat:.2f}s, Audio: {fa_lat:.2f}s)"
    elif fa_lat > 0.0:
        lat_str = f"Latency: {fa_lat:.2f}s (First Audio)"
    else:
        lat_str = "Latency: --"

    lines.append(row(f" {lat_str}"))
    lines.append(row(f" Audio: {audio_state}"))
    lines.append(bottom)

    return "\n".join(lines)
