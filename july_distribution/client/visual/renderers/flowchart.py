"""
HS AI SOLUTIONS — FLOWCHART, MINDMAP & TIMELINE RENDERER
Module: july_distribution.client.visual.renderers.flowchart
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders crisp Unicode flowcharts, mind maps, and timelines directly in terminal.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich import box

from ..models import VisualRequest


class FlowchartRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        title = req.title or "Process Flowchart"
        sub = req.data.get("subtype", "").lower()

        if "mind" in sub or "mind" in title.lower():
            self.render_mindmap(req)
        elif "time" in sub or "timeline" in title.lower():
            self.render_timeline(req)
        else:
            self.render_flowchart(req)

    def render_flowchart(self, req: VisualRequest):
        comps = req.components
        conns = req.connections

        if not comps and not conns:
            # Fallback high-clarity generic flowchart
            art = """
            ┌────────────────────────────────────────┐
            │          [bold green]START: Receive User Prompt[/]          │
            └───────────────────┬────────────────────┘
                                │
                                ▼
            ┌────────────────────────────────────────┐
            │ [bold cyan]Syntax & Semantics Parsing (July Engine)[/] │
            └───────────────────┬────────────────────┘
                                │
                                ▼
                        ╱───────────────╲
                       ╱                 ╲
                      ╱   Need Visual?    ╲ ─── No ──▶ [bold white][ Fast Streaming Text ][/]
                      ╲                   ╱
                       ╲                 ╱
                        ╲───────────────╱
                                │
                               │ Yes
                                ▼
            ┌────────────────────────────────────────┐
            │ [bold yellow]Visual Dispatcher: Select Renderer[/]     │
            │ (Scientific, Neural, Circuit, Algorith)│
            └───────────────────┬────────────────────┘
                                │
                                ▼
            ┌────────────────────────────────────────┐
            │   [bold magenta]Render Directly into PowerShell TUI[/]    │
            └───────────────────┬────────────────────┘
                                │
                                ▼
            ┌────────────────────────────────────────┐
            │          [bold green]END: Display AI Response[/]            │
            └────────────────────────────────────────┘
            """
            self.console.print(Panel(art, title=f"[bold green]📊 FLOWCHART — {title.upper()}[/]", border_style="cyan"))
            return

        # Render custom components if supplied
        tbl = Table(box=box.ROUNDED, border_style="cyan", title=f"[bold cyan]{title.upper()}[/]")
        tbl.add_column("Step", style="bold yellow", width=10)
        tbl.add_column("Component / Action", style="bold white", width=35)
        tbl.add_column("Next Transition / Edge", style="green")

        for i, c in enumerate(comps, 1):
            name = c.get("name", f"Step {i}")
            typ = c.get("type", "Process")
            # find matching connection
            next_step = "-"
            for conn in conns:
                if conn.get("source") == c.get("id"):
                    next_step = f"──▶ {conn.get('target')} ({conn.get('label', '')})"
            tbl.add_row(f"Step {i}", f"[{typ}] {name}", next_step)

        self.console.print(tbl)

    def render_mindmap(self, req: VisualRequest):
        tree = Tree(f"[bold cyan]🧠 {req.title}[/]")
        branches = req.data.get("branches", {
            "Core Foundations": ["Mathematics", "Logic", "Computer Architecture"],
            "Machine Learning": ["Supervised", "Self-Supervised", "Reinforcement Learning"],
            "Systems & Hardware": ["CUDA Acceleration", "RAM Ephemeral Buffers", "Bus Bandwidth"]
        })

        for cat, items in branches.items():
            branch = tree.add(f"[bold yellow]{cat}[/]")
            for item in items:
                branch.add(f"[green]{item}[/]")

        self.console.print(Panel(tree, title="[bold magenta]MIND MAP VISUALIZATION[/]", border_style="magenta"))

    def render_timeline(self, req: VisualRequest):
        events = req.data.get("events", [
            ("Phase 1: Ingestion", "Tokenize prompt & parse semantic tokens"),
            ("Phase 2: Intent Analysis", "Identify query modality (Text, Code, Visual)"),
            ("Phase 3: Execution", "Compute answers or trigger specialized visual engine"),
            ("Phase 4: Synthesis", "Stream Rich formatted response to PowerShell TUI")
        ])

        tbl = Table(box=box.SIMPLE_HEAD, border_style="bright_blue", title=f"[bold cyan]⏳ {req.title}[/]")
        tbl.add_column("Milestone / Time", style="bold yellow", width=25)
        tbl.add_column("Status & Description", style="white")

        for time_str, desc in events:
            tbl.add_row(f"🔹 {time_str}", desc)

        self.console.print(tbl)
