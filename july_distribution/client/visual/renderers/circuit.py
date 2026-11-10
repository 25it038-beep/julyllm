"""
HS AI SOLUTIONS — ELECTRICAL CIRCUIT SCHEMATIC RENDERER
Module: july_distribution.client.visual.renderers.circuit
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders electrical circuits, RLC networks, logic gates, and circuit schematics directly in terminal.
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
        title = req.title or "Electrical Circuit Schematic"
        sub = req.data.get("subtype", "").lower()

        if "rlc" in sub or "rlc" in title.lower() or "ac" in title.lower():
            self.render_rlc_circuit(req)
        elif "logic" in sub or "gate" in title.lower():
            self.render_logic_circuit(req)
        else:
            self.render_dc_series_parallel_circuit(req)

    def render_dc_series_parallel_circuit(self, req: VisualRequest):
        """
        Renders a classic Series-Parallel DC Circuit with:
        - DC Voltage Source (Vs = 12V)
        - Switch (S1)
        - Resistors (R1, R2, R3)
        - Capacitor (C1)
        - Current flow indicators (I_total, I1, I2)
        - Ground (GND)
        """
        circuit_art = """
        [bold yellow]   ┌──────────────[ S1: Switch (CLOSED) ]──────────────┐[/]
        [bold yellow]   │                                                    │[/]
        [bold yellow]   │                                                    ▼  [green]I_total ──▶[/][/]
        [bold yellow]   │                                            ┌───────┴───────┐[/]
        [bold cyan] ┌─┴─┐                                          │               │[/]
        [bold cyan] │ + │ DC Voltage                               │               │[/]
        [bold cyan] │   │ Source                                   ▼ [green]I₁[/]            ▼ [green]I₂[/][/]
        [bold cyan] │ V │ 12.0 V                               ┌───┴───┐       ┌───┴───┐[/]
        [bold cyan] │ - │                                      │  R1   │       │  R2   │[/]
        [bold cyan] └─┬─┘                                      │ 100 Ω │       │ 220 Ω │[/]
        [bold yellow]   │                                        └───┬───┘       └───┬───┘[/]
        [bold yellow]   │                                            │               │[/]
        [bold yellow]   │                                            │           ┌───┴───┐[/]
        [bold yellow]   │                                            │           │  C1   │  Capacitor[/]
        [bold yellow]   │                                            │           │ 10 µF │  Filtered[/]
        [bold yellow]   │                                            │           └───┬───┘[/]
        [bold yellow]   │                                            │               │[/]
        [bold yellow]   │                                            └───────┬───────┘[/]
        [bold yellow]   │                                                    │[/]
        [bold yellow]   └──────────────────────┬─────────────────────────────┘[/]
        [dim]                          │[/]
        [dim]                        ──┴──  GND (0.0 V)[/]
        [dim]                         ───[/]
        [dim]                          ─[/]
        """

        # Circuit Calculations & Specs Table
        spec_table = Table(box=box.ROUNDED, border_style="cyan", expand=True)
        spec_table.add_column("Component", style="bold cyan", width=18)
        spec_table.add_column("Nominal Value", style="yellow", width=16)
        spec_table.add_column("Current / Voltage Drop", style="green", width=24)
        spec_table.add_column("Governing Physical Law", style="white")

        spec_table.add_row("Vs (DC Source)", "12.0 V", "Provides I_total = 174.5 mA", "EMF Electromotive Force")
        spec_table.add_row("S1 (Power Switch)", "SPST Closed", "V_drop ≈ 0.0 V (Ideal)", "Ohmic Contact")
        spec_table.add_row("R1 (Branch 1)", "100.0 Ω", "V_R1 = 12.0 V | I₁ = 120.0 mA", "Ohm's Law: I₁ = V / R1")
        spec_table.add_row("R2 (Branch 2)", "220.0 Ω", "V_R2 = 12.0 V | I₂ = 54.5 mA", "Ohm's Law: I₂ = V / R2")
        spec_table.add_row("C1 (Branch 2)", "10.0 µF", "Q = C•V = 120 µC (Steady State)", "i(t) = C • (dv/dt)")
        spec_table.add_row("GND (Reference)", "0.0 V", "Common node zero potential", "Kirchhoff's Current Law (ΣI = 0)")

        kvl_panel = Panel(
            "[bold green]KIRCHHOFF'S CURRENT LAW (KCL):[/]  I_total = I₁ + I₂ = 120.0 mA + 54.5 mA = 174.5 mA\n"
            "[bold yellow]KIRCHHOFF'S VOLTAGE LAW (KVL):[/]  Σ V_loop = Vs - V_branch = 12V - 12V = 0V\n"
            "[bold magenta]EQUIVALENT RESISTANCE (Req):[/]    Req = (R1 • R2) / (R1 + R2) = (100×220)/(320) = 68.75 Ω",
            title="[bold yellow]CIRCUIT ANALYSIS EQUATIONS[/]",
            border_style="yellow"
        )

        self.console.print(Panel(
            f"[bold white]{req.title.upper()}[/]\n"
            "[dim]Direct Current (DC) Lumped Element Schematic & Network Analysis[/]",
            title="[bold green]⚡ ELECTRICAL CIRCUIT SCHEMATIC[/]",
            border_style="green"
        ))

        self.console.print(Panel(circuit_art, title="[bold yellow]SCHEMATIC DIAGRAM & COMPONENT TOPOLOGY[/]", border_style="yellow"))
        self.console.print(spec_table)
        self.console.print(kvl_panel)

        if req.explanation:
            self.console.print(Panel(f"[bold white]{req.explanation}[/]", title="[bold cyan]Electronics Context[/]", border_style="cyan"))

    def render_rlc_circuit(self, req: VisualRequest):
        """Renders Series RLC Resonant AC Circuit."""
        rlc_art = """
        [bold yellow]   ┌──────────────[ R: Resistor (50 Ω) ]──────────────[ L: Inductor (10 mH) ]────────┐[/]
        [bold yellow]   │                                                                                 │[/]
        [bold yellow]   │                                                                                 │[/]
        [bold cyan] ┌─┴─┐                                                                           ┌───┴───┐[/]
        [bold cyan] │ ~ │ AC Source                                                                 │  C1   │  Capacitor[/]
        [bold cyan] │   │ V(t) = V₀ sin(ωt)                                                         │ 4.7 µF│  (4.7 µF)[/]
        [bold cyan] │   │ 120V RMS @ 60Hz                                                           └───┬───┘[/]
        [bold cyan] └─┬─┘                                                                               │[/]
        [bold yellow]   │                                                                                 │[/]
        [bold yellow]   └───────────────────────────────────────┬─────────────────────────────────────────┘[/]
        [dim]                                           │[/]
        [dim]                                         ──┴──  GND[/]
        """
        self.console.print(Panel(rlc_art, title="[bold cyan]⚡ AC SERIES RLC RESONANT CIRCUIT[/]", border_style="cyan"))

    def render_logic_circuit(self, req: VisualRequest):
        """Renders Digital Logic Gate Circuit (e.g. Full Adder)."""
        logic_art = """
        [bold cyan]A ────┬───────────────────┐[/]
              │                   ▼
              │                ┌──────┐
              │                │ XOR₁ │─────────┬──────────────┐
              │           ┌───▶│      │         │              ▼
        [bold cyan]B ────┼───────────┤    └──────┘         │           ┌──────┐
              │           │                     │      ┌───▶│ XOR₂ │ ────────▶ [bold green]SUM (S)[/]
        [bold yellow]Cin ──┼───────────┼─────────────────────┼──────┤    └──────┘
              │           │                     │      │
              │           │                     ▼      │
              │           │                  ┌──────┐  │
              │           │                  │ AND₁ │──┼──────┐
              │           │                  │      │  │      │
              │           ▼                  └──────┘  ▼      ▼
              │        ┌──────┐                     ┌──────┐  │
              └───────▶│ AND₂ │────────────────────▶│  OR  │◀─┘ ─────────────▶ [bold yellow]CARRY (Cout)[/]
                       │      │                     │      │
                       └──────┘                     └──────┘
        """
        self.console.print(Panel(logic_art, title="[bold magenta]🔌 DIGITAL LOGIC CIRCUIT: 1-BIT FULL ADDER[/]", border_style="magenta"))
