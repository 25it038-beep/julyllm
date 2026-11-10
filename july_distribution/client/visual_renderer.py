"""
HS AI SOLUTIONS — JULY VISUAL REPRESENTATION ENGINE
Layer: VISUAL ARTIFACTS & IN-CLI RENDERING (july_distribution.client.visual_renderer)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Provides high-clarity visual representations directly inside the CLI terminal:
- In-CLI Unicode box flowcharts, sequence diagrams, and data graphs.
- Direct parsing of Mermaid diagrams to styled console visuals.
- Zero external dependencies.
- Optional browser preview file generation.
"""

from __future__ import annotations
import os
import re
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

STUDIO_URL = "https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/"


class CLIColor:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"


def clean_node_label(raw: str) -> str:
    """Extracts human-readable label from Mermaid node syntax."""
    raw = raw.strip()
    # Match A["Label"] or A[Label] or A(Label) or A{Label}
    m = re.search(r'\[["\']?(.*?)["\']?\]', raw)
    if m:
        return m.group(1).strip()
    m = re.search(r'\(["]?(.*?)["]?\)', raw)
    if m:
        return m.group(1).strip()
    m = re.search(r'\{["]?(.*?)["]?\}', raw)
    if m:
        return m.group(1).strip()
    return raw.strip()


def render_mermaid_to_cli(code: str) -> str:
    """Parses Mermaid diagram code and renders a styled Unicode visual diagram in the CLI."""
    lines = [l.strip() for l in code.strip().splitlines() if l.strip()]
    if not lines:
        return ""

    first_line = lines[0].lower()
    edges: List[Tuple[str, str, str]] = []  # (src, edge_label, dst)
    node_names = []

    # Sequence Diagram
    if "sequencediagram" in first_line:
        seq_events: List[Tuple[str, str, str]] = []
        participants = []
        for line in lines[1:]:
            if line.lower().startswith("participant"):
                parts = line.split(maxsplit=1)
                if len(parts) > 1:
                    p = clean_node_label(parts[1])
                    if p not in participants:
                        participants.append(p)
            elif "->>" in line or "-->>" in line or "->" in line:
                m = re.split(r"\s*(?:->>|-->>|->)\s*", line, maxsplit=1)
                if len(m) == 2:
                    src = clean_node_label(m[0])
                    rest = m[1].split(":", maxsplit=1)
                    dst = clean_node_label(rest[0])
                    msg = rest[1].strip() if len(rest) > 1 else ""
                    seq_events.append((src, dst, msg))
                    if src not in participants:
                        participants.append(src)
                    if dst not in participants:
                        participants.append(dst)

        out = [
            f" {CLIColor.MAGENTA}┌── 🎨 IN-CLI VISUAL SEQUENCE DIAGRAM ──────────────────────────────────────┐{CLIColor.RESET}"
        ]
        if participants:
            header_str = "   " + "   │   ".join(f"{CLIColor.BOLD}{CLIColor.CYAN}{p[:15]}{CLIColor.RESET}" for p in participants[:4])
            out.append(f" {CLIColor.GRAY}│{CLIColor.RESET} {header_str}")
            out.append(f" {CLIColor.GRAY}│   " + ("┼───────" * len(participants[:4])) + f"│{CLIColor.RESET}")

        for i, (src, dst, msg) in enumerate(seq_events[:8], 1):
            lbl = f"({i}) {src} ──▶ {dst}: {msg}"
            out.append(f" {CLIColor.GRAY}│{CLIColor.RESET}   {CLIColor.GREEN}•{CLIColor.RESET} {lbl[:68]}")

        out.append(f" {CLIColor.MAGENTA}└───────────────────────────────────────────────────────────────────────────┘{CLIColor.RESET}")
        return "\n".join(out)

    # Pie Chart
    if "pie" in first_line:
        pie_data = []
        for line in lines[1:]:
            m = re.findall(r'["\']?(.*?)["\']?\s*:\s*([0-9.]+)', line)
            if m:
                label, val = m[0]
                try:
                    pie_data.append((label.strip(), float(val)))
                except ValueError:
                    pass

        if pie_data:
            total = sum(v for _, v in pie_data) or 1.0
            out = [
                f" {CLIColor.MAGENTA}┌── 🎨 IN-CLI DATA VISUALIZATION (BAR GRAPH) ──────────────────────────────┐{CLIColor.RESET}"
            ]
            for label, val in pie_data[:6]:
                pct = int((val / total) * 100)
                bar_len = int(pct / 4)
                bar = "█" * bar_len + "░" * (25 - bar_len)
                out.append(f" {CLIColor.GRAY}│{CLIColor.RESET}  {CLIColor.BOLD}{label[:18]:<18}{CLIColor.RESET} [{CLIColor.CYAN}{bar}{CLIColor.RESET}] {CLIColor.YELLOW}{pct:>3}%{CLIColor.RESET} ({val:g})")
            out.append(f" {CLIColor.MAGENTA}└───────────────────────────────────────────────────────────────────────────┘{CLIColor.RESET}")
            return "\n".join(out)

    # Standard Graph / Flowchart
    for line in lines[1:]:
        if line.startswith("style ") or line.startswith("classDef ") or line.startswith("subgraph") or line == "end":
            continue

        # Pattern: A[Label] -->|text| B[Label] or A --> B
        match = re.split(r"\s*(?:-->|->|-.->|==>)\s*", line)
        if len(match) >= 2:
            src = clean_node_label(match[0])
            dst_part = match[1]
            edge_lbl = ""
            if dst_part.startswith("|"):
                lbl_end = dst_part.find("|", 1)
                if lbl_end != -1:
                    edge_lbl = dst_part[1:lbl_end].strip()
                    dst_part = dst_part[lbl_end + 1:]
            dst = clean_node_label(dst_part)
            if src and dst:
                edges.append((src, edge_lbl, dst))
                if src not in node_names:
                    node_names.append(src)
                if dst not in node_names:
                    node_names.append(dst)

    if not edges:
        return ""

    out = [
        f" {CLIColor.MAGENTA}┌── 🎨 IN-CLI VISUAL FLOWCHART ─────────────────────────────────────────────┐{CLIColor.RESET}"
    ]

    # Render flowchart sequential blocks
    for i, (src, edge_lbl, dst) in enumerate(edges[:7], 1):
        arrow_str = f"──[{edge_lbl}]──▶" if edge_lbl else "───────▶"
        s_card = f"{CLIColor.CYAN}{src[:28]}{CLIColor.RESET}"
        d_card = f"{CLIColor.GREEN}{dst[:28]}{CLIColor.RESET}"
        out.append(f" {CLIColor.GRAY}│{CLIColor.RESET}  ┌─ [Step {i}] ────────────────────────────────────────────────────────┐")
        out.append(f" {CLIColor.GRAY}│{CLIColor.RESET}  │  {s_card:<38} {CLIColor.YELLOW}{arrow_str}{CLIColor.RESET} {d_card:<38} │")
        out.append(f" {CLIColor.GRAY}│{CLIColor.RESET}  └────────────────────────────────────────────────────────────────────┘")
        if i < min(len(edges), 7):
            out.append(f" {CLIColor.GRAY}│                                     │                                │{CLIColor.RESET}")
            out.append(f" {CLIColor.GRAY}│                                     ▼                                │{CLIColor.RESET}")

    out.append(f" {CLIColor.MAGENTA}└───────────────────────────────────────────────────────────────────────────┘{CLIColor.RESET}")
    return "\n".join(out)


def detect_visual_content(text: str) -> Optional[Tuple[str, str]]:
    """
    Detects if the response text contains a visual representation:
    Returns (visual_type, raw_code) or None.
    Types: 'mermaid', 'svg', 'html'
    """
    # 1. Mermaid code block
    m = re.search(r"```mermaid\s*\n([\s\S]*?)\n```", text, re.IGNORECASE)
    if m:
        return ("mermaid", m.group(1).strip())

    # 2. Raw SVG code block
    m = re.search(r"```svg\s*\n([\s\S]*?)\n```", text, re.IGNORECASE)
    if m:
        return ("svg", m.group(1).strip())

    # 3. Inline <svg> element
    m = re.search(r"(<svg[\s\S]*?</svg>)", text, re.IGNORECASE)
    if m:
        return ("svg", m.group(1).strip())

    # 4. HTML code block
    m = re.search(r"```html\s*\n([\s\S]*?)\n```", text, re.IGNORECASE)
    if m:
        code = m.group(1).strip()
        if any(tag in code.lower() for tag in ("<svg", "<canvas", "<table", "<div", "<style", "chart")):
            return ("html", code)

    return None


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JULY LLM — Visual Representation</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #111827;
      --border: #1f2937;
      --cyan: #06b6d4;
      --cyan-light: #22d3ee;
      --green: #10b981;
      --text: #f3f4f6;
      --muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px;
    }
    header {
      width: 100%;
      max-width: 1000px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-bottom: 20px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .badge {
      background: linear-gradient(135deg, var(--cyan), var(--green));
      color: #000;
      font-weight: 800;
      font-size: 13px;
      padding: 4px 10px;
      border-radius: 6px;
      letter-spacing: 0.5px;
    }
    .title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text);
    }
    .subtitle {
      font-size: 12px;
      color: var(--muted);
    }
    .portal-link {
      color: var(--cyan-light);
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border: 1px solid rgba(6, 182, 212, 0.3);
      border-radius: 6px;
      transition: all 0.2s ease;
    }
    .portal-link:hover {
      background: rgba(6, 182, 212, 0.1);
      border-color: var(--cyan);
    }
    .container {
      width: 100%;
      max-width: 1000px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 32px 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 400px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      position: relative;
    }
    .visual-content {
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      overflow-x: auto;
      padding: 10px;
    }
    .mermaid {
      background: transparent !important;
      display: flex;
      justify-content: center;
      width: 100%;
    }
    svg {
      max-width: 100%;
      height: auto;
    }
    footer {
      margin-top: 20px;
      font-size: 12px;
      color: var(--muted);
      text-align: center;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="badge">HS AI</span>
      <div>
        <div class="title">JULY LLM — Visual Representation</div>
        <div class="subtitle">Autonomous Neural Runtime Graphical Output</div>
      </div>
    </div>
    <a href="__STUDIO_URL__" target="_blank" class="portal-link">
      <span>HS AI Studio Portal</span> ↗
    </a>
  </header>

  <main class="container">
    <div class="visual-content">
      __CONTENT__
    </div>
  </main>

  <footer>
    Generated by JULY LLM • HS AI SOLUTIONS • Zero-Persistence Ephemeral Preview
  </footer>

  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        darkMode: true,
        background: '#111827',
        primaryColor: '#06b6d4',
        primaryTextColor: '#f3f4f6',
        primaryBorderColor: '#0891b2',
        lineColor: '#22d3ee',
        secondaryColor: '#10b981',
        tertiaryColor: '#1f2937'
      }
    });
  </script>
</body>
</html>
"""


def render_visual_html(visual_type: str, raw_code: str) -> Path:
    """Renders the visual content into a standalone HTML preview file."""
    if visual_type == "mermaid":
        content_html = f'<div class="mermaid">\n{raw_code}\n</div>'
    elif visual_type == "svg":
        content_html = raw_code
    elif visual_type == "html":
        content_html = raw_code
    else:
        content_html = f"<pre><code>{raw_code}</code></pre>"

    page = HTML_TEMPLATE.replace("__STUDIO_URL__", STUDIO_URL).replace("__CONTENT__", content_html)

    temp_dir = Path(tempfile.gettempdir()) / "july_ephemeral_runtime"
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_file = temp_dir / "visual_preview.html"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(page)

    return out_file


def open_visual_in_browser(file_path: Path):
    """Launches the rendered visual artifact in default web browser."""
    try:
        url = file_path.resolve().as_uri()
        webbrowser.open(url)
    except Exception:
        pass
