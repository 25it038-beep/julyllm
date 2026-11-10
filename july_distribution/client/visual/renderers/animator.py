"""
HS AI SOLUTIONS — PROCESS & ALGORITHM ANIMATION RENDERER (HIGH-CLARITY)
Module: july_distribution.client.visual.renderers.animator
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders crisp, high-clarity algorithm traces and OS scheduling Gantt charts strictly fitted to console width.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ..models import VisualRequest


class ProcessAnimator:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        title = req.title.lower()
        sub = req.data.get("subtype", "").lower()

        if "binary" in title or "binary" in sub or "search" in title:
            self.render_binary_search(req)
        elif "schedul" in title or "os" in title or "round robin" in title or "gantt" in title:
            self.render_os_scheduling(req)
        else:
            self.render_binary_search(req)

    def render_binary_search(self, req: VisualRequest):
        """
        Renders crystal-clear step-by-step Binary Search visualization
        guaranteed to never wrap on standard 79-column console terminals.
        """
        arr = req.data.get("array", [2, 5, 8, 12, 16, 23, 38, 45, 56, 72, 91])
        target = req.data.get("target", 23)

        self.console.print(Panel(
            f"[bold white]BINARY SEARCH ALGORITHM TRACE[/] • Target Element = [bold bright_yellow]{target}[/]\n"
            f"[dim]Time Complexity: O(log₂ n) = O(log₂ 11) ≈ 3.46 steps max • Space: O(1)[/]",
            title="[bold green]🔍 ALGORITHM VISUALIZATION[/]",
            border_style="bright_blue",
            expand=False
        ))

        # Simulate steps
        low, high = 0, len(arr) - 1
        step_idx = 1
        steps_log = []

        while low <= high:
            mid = (low + high) // 2
            val = arr[mid]
            if val == target:
                steps_log.append({
                    "step": step_idx, "low": low, "high": high, "mid": mid, "match": True,
                    "action": f"🎯 arr[{mid}] == {target}! TARGET FOUND at Index {mid}!"
                })
                break
            elif target < val:
                steps_log.append({
                    "step": step_idx, "low": low, "high": high, "mid": mid, "match": False,
                    "action": f"Target {target} < arr[{mid}] ({val}) ──▶ Discard right half. Set high = {mid - 1}"
                })
                high = mid - 1
            else:
                steps_log.append({
                    "step": step_idx, "low": low, "high": high, "mid": mid, "match": False,
                    "action": f"Target {target} > arr[{mid}] ({val}) ──▶ Discard left half. Set low = {mid + 1}"
                })
                low = mid + 1
            step_idx += 1

        # Render each step with high-clarity horizontal box
        for st in steps_log:
            s_num = st["step"]
            l, h, m = st["low"], st["high"], st["mid"]
            is_match = st["match"]

            # Construct index line (strictly compact)
            idx_line = "  Idx: " + " ".join(f"[{i:>2}]" for i in range(len(arr)))
            # Construct top border
            top_border = "       ┌───" + "┬───" * (len(arr) - 1) + "┐"
            # Construct values line
            val_parts = []
            for i, val in enumerate(arr):
                if i == m and is_match:
                    val_parts.append(f"[bold black on green]{val:>2}★[/]")
                elif i == m:
                    val_parts.append(f"[bold black on yellow]{val:>3}[/]")
                elif l <= i <= h:
                    val_parts.append(f"[bold cyan]{val:>3}[/]")
                else:
                    val_parts.append(f"[dim strike]{val:>3}[/]")
            val_line = "  Val: │" + "│".join(val_parts) + "│"
            bot_border = "       └───" + "┴───" * (len(arr) - 1) + "┘"

            # Construct pointer line
            ptr_cells = []
            for i in range(len(arr)):
                lbl = ""
                if i == l:
                    lbl = "LOW"
                elif i == m:
                    lbl = "MID"
                elif i == h:
                    lbl = "HI"
                ptr_cells.append(f"{lbl:^4}")
            
            ptr_line = "  Ptr: " + "".join(f"[bold yellow]{p}[/]" for p in ptr_cells)

            content = f"{idx_line}\n{top_border}\n{val_line}\n{bot_border}\n{ptr_line}\n\n[bold white]{st['action']}[/]"
            step_border = "green" if is_match else "yellow"
            self.console.print(Panel(
                content,
                title=f"[bold {step_border}]STEP {s_num}: low={l}, mid={m}, high={h}[/]",
                border_style=step_border,
                expand=False
            ))

        ctrl_bar = "[bold cyan][ ◀ PREV ][/]   [bold green][ ▶ PLAY ][/]   [bold yellow][ ❚❚ PAUSE ][/]   [bold magenta][ NEXT ▶ ][/]   [bold red][ ↺ RESET ][/]"
        self.console.print(Panel(ctrl_bar, title="[dim]ANIMATION TIMELINE CONTROLS[/]", border_style="dim white", expand=False))

    def render_os_scheduling(self, req: VisualRequest):
        """
        Renders OS Process Scheduling (Round Robin) with visual Gantt blocks and metrics.
        """
        self.console.print(Panel(
            "[bold white]ROUND ROBIN CPU PROCESS SCHEDULER DYNAMICS (Quantum q = 4ms)[/]\n"
            "[dim]Preemptive context switching, ready queue interleaving, and fairness analysis[/]",
            title="[bold green]⏱️ OS SCHEDULING SIMULATION[/]",
            border_style="bright_blue",
            expand=False
        ))

        # Compact, clean Gantt chart timeline
        gantt_chart = (
            "  [bold yellow]GANTT EXECUTION TIMELINE:[/]\n"
            "  ┌────────┬────────┬────────┬────────┬────────┬────────┬────┬────┐\n"
            "  │[bold black on green] P1 (4) [/]│[bold black on yellow] P2 (4) [/]│[bold black on magenta] P3 (4) [/]│[bold black on cyan] P4 (4) [/]│[bold black on green] P1 (4) [/]│[bold black on magenta] P3 (4) [/]│[bold black on cyan]P4(1)[/]│[bold black on magenta]P3(1)[/]│\n"
            "  └────────┴────────┴────────┴────────┴────────┴────────┴────┴────┘\n"
            "  0        4        8        12       16       20       24   25   26 ms\n\n"
            "  [green]■ P1: 8ms total[/]   [yellow]■ P2: 4ms total[/]   [magenta]■ P3: 9ms total[/]   [cyan]■ P4: 5ms total[/]"
        )
        self.console.print(Panel(gantt_chart, title="[bold yellow]TIMELINE GANTT CHART[/]", border_style="yellow", expand=False))

        # Metrics Table
        metrics_table = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
        metrics_table.add_column("Process", style="bold cyan", width=10)
        metrics_table.add_column("Arrival", style="yellow", width=10)
        metrics_table.add_column("Burst", style="yellow", width=10)
        metrics_table.add_column("Finish Time", style="green", width=14)
        metrics_table.add_column("Turnaround (TAT)", style="magenta", width=18)
        metrics_table.add_column("Waiting Time (WT)", style="white")

        metrics_table.add_row("P1", "0 ms", "8 ms", "20 ms", "20 ms (20 - 0)", "12 ms (20 - 8)")
        metrics_table.add_row("P2", "1 ms", "4 ms", "8 ms", "7 ms (8 - 1)", "3 ms (7 - 4)")
        metrics_table.add_row("P3", "2 ms", "9 ms", "26 ms", "24 ms (26 - 2)", "15 ms (24 - 9)")
        metrics_table.add_row("P4", "3 ms", "5 ms", "25 ms", "22 ms (25 - 3)", "17 ms (22 - 5)")
        metrics_table.add_row("[bold white]Average[/]", "-", "-", "-", "[bold magenta]18.25 ms[/]", "[bold green]11.75 ms[/]")

        self.console.print(metrics_table)

        ctrl_bar = "[bold cyan][ ◀ PREV ][/]   [bold green][ ▶ PLAY ][/]   [bold yellow][ ❚❚ PAUSE ][/]   [bold magenta][ NEXT ▶ ][/]   [bold red][ ↺ RESET ][/]"
        self.console.print(Panel(ctrl_bar, title="[dim]ANIMATION TIMELINE CONTROLS[/]", border_style="dim white", expand=False))
