"""
HS AI SOLUTIONS — MATHEMATICAL GRAPH RENDERER
Module: july_distribution.client.visual.renderers.math_plot
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders accurate mathematical functions, coordinates, and curve plots directly in terminal via plotext.
"""

from __future__ import annotations
import math
from typing import Dict, Any, Optional, List
import plotext as plt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..models import VisualRequest


class MathPlotRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        plt.clf()
        plt.theme("dark")

        data = req.data
        fn_type = data.get("function_type", "").lower()
        title = req.title or "Mathematical Function Visualization"

        # Check if raw series are provided
        if "x" in data and "y" in data:
            x_vals = data["x"]
            y_vals = data["y"]
            plt.plot(x_vals, y_vals, label=data.get("series_label", "f(x)"), color="cyan")
        elif "sigmoid" in fn_type or "sigmoid" in title.lower():
            # Sigmoid: 1 / (1 + exp(-x))
            x_vals = [i * 0.2 for i in range(-50, 51)]
            y_vals = [1.0 / (1.0 + math.exp(-x)) for x in x_vals]
            plt.plot(x_vals, y_vals, label="σ(x) = 1 / (1 + e^-x)", color="green")
            plt.scatter([0], [0.5], color="red", marker="●", label="Inflection (0, 0.5)")
        elif "relu" in fn_type or "relu" in title.lower():
            # ReLU: max(0, x)
            x_vals = [i * 0.2 for i in range(-50, 51)]
            y_vals = [max(0.0, x) for x in x_vals]
            plt.plot(x_vals, y_vals, label="ReLU(x) = max(0, x)", color="yellow")
        elif "sin" in fn_type or "sine" in title.lower() or "trig" in fn_type:
            x_vals = [i * 0.1 for i in range(-60, 61)]
            y_sin = [math.sin(x) for x in x_vals]
            y_cos = [math.cos(x) for x in x_vals]
            plt.plot(x_vals, y_sin, label="sin(x)", color="cyan")
            plt.plot(x_vals, y_cos, label="cos(x)", color="magenta")
        elif "gaussian" in fn_type or "normal" in title.lower():
            x_vals = [i * 0.1 for i in range(-40, 41)]
            y_vals = [(1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x) for x in x_vals]
            plt.plot(x_vals, y_vals, label="Standard Normal Distribution N(0,1)", color="cyan")
        else:
            # Quadratic / polynomial fallback
            x_vals = [i * 0.2 for i in range(-40, 41)]
            y_vals = [x * x for x in x_vals]
            plt.plot(x_vals, y_vals, label="f(x) = x²", color="cyan")

        w = max(30, min(self.console.width - 24, 54))
        plt.title(title.upper())
        plt.xlabel(data.get("x_label", "x-axis"))
        plt.ylabel(data.get("y_label", "y-axis"))
        plt.plotsize(w, 12)

        chart_str = plt.build()

        from rich.text import Text
        panel = Panel(
            Text.from_ansi(chart_str),
            title=f"[bold green]📐 MATHEMATICAL VISUALIZATION — {title}[/]",
            subtitle="[dim cyan]HS AI Solutions • July Math Plot Engine[/]",
            border_style="cyan",
            expand=False
        )
        self.console.print(panel)
        if req.explanation:
            self.console.print(Panel(f"[bold white]{req.explanation}[/]", title="[bold yellow]Mathematical Analysis[/]", border_style="yellow"))
