"""
HS AI SOLUTIONS — ELECTRICAL CIRCUIT SCHEMATIC RENDERER (HIGH-CLARITY)
Module: july_distribution.client.visual.renderers.circuit
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders crisp, high-clarity electrical circuit schematics and network equations fitted to terminal width.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ..models import VisualRequest


class CircuitRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        sub = req.data.get("subtype", "").lower()
        title = req.title.lower()

        if "rlc" in sub or "rlc" in title or "ac" in title:
            self.render_rlc_circuit(req)
        elif "logic" in sub or "gate" in title:
            self.render_logic_circuit(req)
        else:
            self.render_dc_series_parallel_circuit(req)

    def render_dc_series_parallel_circuit(self, req: VisualRequest):
        """
        Renders a crystal-clear DC Series-Parallel schematic with current flows.
        """
        self.console.print(Panel(
            "[bold white]DC SERIES-PARALLEL CIRCUIT SCHEMATIC & NETWORK ANALYSIS[/]\n"
            "[dim]Direct Current Lumped Elements, Ohm's Law & Kirchhoff's Circuit Laws[/]",
            title="[bold green]⚡ ELECTRICAL CIRCUIT VISUALIZATION[/]",
            border_style="bright_blue",
            expand=False
        ))

        circuit_art = (
            "   [bold yellow]┌──────────────[ S1: Switch (CLOSED) ]──────────────┐[/]\n"
            "   [bold yellow]│                                                    │[/]\n"
            "   [bold yellow]│                                                    ▼  [green]I_total = 174.5 mA[/][/]\n"
            "   [bold yellow]│                                            ┌───────┴───────┐[/]\n"
            " [bold cyan]┌─┴─┐[/]                                          [bold yellow]│               │[/]\n"
            " [bold cyan]│ + │ DC Voltage[/]                               [bold yellow]│               │[/]\n"
            " [bold cyan]│   │ Source[/]                                   [bold yellow]▼ [green]I₁[/][/]            [bold yellow]▼ [green]I₂[/][/]\n"
            " [bold cyan]│ V │ 12.0 V[/]                               ┌───┴───┐       ┌───┴───┐\n"
            " [bold cyan]│ - │[/]                                      │  R1   │       │  R2   │\n"
            " [bold cyan]└─┬─┘[/]                                      │ 100 Ω │       │ 220 Ω │\n"
            "   [bold yellow]│[/]                                        └───┬───┘       └───┬───┘\n"
            "   [bold yellow]│[/]                                            [bold yellow]│[/]               [bold yellow]│[/]\n"
            "   [bold yellow]│[/]                                            [bold yellow]│[/]           ┌───┴───┐\n"
            "   [bold yellow]│[/]                                            [bold yellow]│[/]           │  C1   │  Capacitor\n"
            "   [bold yellow]│[/]                                            [bold yellow]│[/]           │ 10 µF │  Filtered\n"
            "   [bold yellow]│[/]                                            [bold yellow]│[/]           └───┬───┘\n"
            "   [bold yellow]│[/]                                            [bold yellow]│[/]               [bold yellow]│[/]\n"
            "   [bold yellow]│                                            └───────┬───────┘[/]\n"
            "   [bold yellow]│                                                    │[/]\n"
            "   [bold yellow]└──────────────────────┬─────────────────────────────┘[/]\n"
            "                          [dim]│[/]\n"
            "                        [dim]──┴──  GND (0.0 V Reference)[/]\n"
            "                         [dim]───[/]\n"
            "                          [dim]─[/]"
        )
        self.console.print(Panel(circuit_art, title="[bold yellow]SCHEMATIC TOPOLOGY[/]", border_style="yellow", expand=False))

        # Component Table
        spec_table = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
        spec_table.add_column("Component", style="bold cyan", width=14)
        spec_table.add_column("Nominal Value", style="yellow", width=14)
        spec_table.add_column("Current & Drop", style="green", width=22)
        spec_table.add_column("Governing Law", style="white")

        spec_table.add_row("Vs (DC EMF)", "12.0 V", "Supplies 174.5 mA total", "Electromotive Force")
        spec_table.add_row("R1 (Branch 1)", "100.0 Ω", "V_drop = 12.0V | I₁ = 120mA", "Ohm's Law (I₁ = V/R1)")
        spec_table.add_row("R2 (Branch 2)", "220.0 Ω", "V_drop = 12.0V | I₂ = 54.5mA", "Ohm's Law (I₂ = V/R2)")
        spec_table.add_row("C1 (Branch 2)", "10.0 µF", "Q = C•V = 120 µC", "Capacitance (Q = C•V)")
        spec_table.add_row("GND (Earth)", "0.0 V", "Reference ground node", "Kirchhoff Current Law")

        self.console.print(spec_table)

        kvl_panel = Panel(
            "[bold green]KIRCHHOFF'S CURRENT LAW (KCL):[/]  I_total = I₁ + I₂ = 120.0 mA + 54.5 mA = 174.5 mA\n"
            "[bold yellow]KIRCHHOFF'S VOLTAGE LAW (KVL):[/]  Σ V_loop = Vs - V_branch = 12V - 12V = 0V\n"
            "[bold magenta]EQUIVALENT RESISTANCE (Req):[/]    Req = (R1 • R2) / (R1 + R2) = (100×220)/(320) = 68.75 Ω",
            title="[bold yellow]CIRCUIT GOVERNING FORMULAS[/]",
            border_style="yellow",
            expand=False
        )
        self.console.print(kvl_panel)

    def render_rlc_circuit(self, req: VisualRequest):
        """Renders Series RLC Resonant AC Circuit."""
        rlc_art = (
            "   [bold yellow]┌──────────────[ R: Resistor (50 Ω) ]──────────────[ L: Inductor (10 mH) ]────────┐[/]\n"
            "   [bold yellow]│                                                                                 │[/]\n"
            " [bold cyan]┌─┴─┐[/]                                                                           ┌───┴───┐\n"
            " [bold cyan]│ ~ │ AC Source[/]                                                                 │  C1   │\n"
            " [bold cyan]│   │ 120V RMS @ 60Hz[/]                                                           │ 4.7 µF│\n"
            " [bold cyan]└─┬─┘[/]                                                                           └───┬───┘\n"
            "   [bold yellow]│                                                                                 │[/]\n"
            "   [bold yellow]└───────────────────────────────────────┬─────────────────────────────────────────┘[/]\n"
            "                                           [dim]│\n"
            "                                         ──┴──  GND[/]"
        )
        self.console.print(Panel(rlc_art, title="[bold cyan]⚡ AC SERIES RLC RESONANT CIRCUIT[/]", border_style="cyan", expand=False))

    def render_logic_circuit(self, req: VisualRequest):
        """Renders Digital Logic Gate Circuit."""
        logic_art = (
            "   [bold cyan]A ────┬───────────────────┐[/]\n"
            "         │                   ▼\n"
            "         │                ┌──────┐\n"
            "         │                │ XOR₁ │─────────┬──────────────┐\n"
            "         │           ┌───▶│      │         │              ▼\n"
            "   [bold cyan]B ────┼───────────┤    └──────┘         │           ┌──────┐\n"
            "         │           │                     │      ┌───▶│ XOR₂ │ ────────▶ [bold green]SUM (S)[/]\n"
            "   [bold yellow]Cin ──┼───────────┼─────────────────────┼──────┤    └──────┘\n"
            "         │           │                     │      │\n"
            "         │           │                     ▼      │\n"
            "         │           │                  ┌──────┐  │\n"
            "         │           │                  │ AND₁ │──┼──────┐\n"
            "         │           │                  │      │  │      │\n"
            "         │           ▼                  └──────┘  ▼      ▼\n"
            "         │        ┌──────┐                     ┌──────┐  │\n"
            "         └───────▶│ AND₂ │────────────────────▶│  OR  │◀─┘ ─────────────▶ [bold yellow]CARRY (Cout)[/]\n"
            "                  │      │                     │      │\n"
            "                  └──────┘                     └──────┘"
        )
        self.console.print(Panel(logic_art, title="[bold magenta]🔌 DIGITAL LOGIC: 1-BIT FULL ADDER[/]", border_style="magenta", expand=False))
