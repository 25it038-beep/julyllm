"""
HS AI SOLUTIONS — DATA VISUALIZATION RENDERER
Module: july_distribution.client.visual.renderers.data_vis
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders bar charts, distribution histograms, and tabular comparisons directly in terminal.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
import plotext as plt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..models import VisualRequest


class DataVisRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        data = req.data
        labels = data.get("labels", ["Token Gen", "Memory Bus", "CUDA Compute", "Latency"])
        values = data.get("values", [85, 92, 98, 45])
        title = req.title or "Data Metric Comparison"

        plt.clf()
        plt.theme("dark")

        plt.bar(labels, values, color="cyan")
        plt.title(title.upper())
        plt.ylabel("Score / Performance (%)")
        plt.plotsize(80, 16)

        chart_str = plt.build()

        panel = Panel.fit(
            chart_str,
            title=f"[bold green]📊 DATA VISUALIZATION — {title}[/]",
            subtitle="[dim cyan]HS AI Solutions • July Data Engine[/]",
            border_style="cyan"
        )
        self.console.print(panel)
