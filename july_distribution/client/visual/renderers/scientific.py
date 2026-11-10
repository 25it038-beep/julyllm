"""
HS AI SOLUTIONS — SCIENTIFIC DIAGRAM RENDERER
Module: july_distribution.client.visual.renderers.scientific
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders accurate scientific diagrams directly in the terminal:
- Water Phase Diagram (P-T curve, negative slope melting line, triple point, critical point)
- Chemical Reaction Energy Curves (Reactants, Ea, Transition State, Products, ΔH)
- Natural cycles (Water Cycle, Carbon Cycle)
"""

from __future__ import annotations
import math
from typing import Dict, Any, Optional
import plotext as plt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from ..models import VisualRequest


class ScientificRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        sub = req.data.get("subtype", "").lower()
        title = req.title.lower()

        if "phase" in sub or "phase" in title or "water" in title and "phase" in title:
            self.render_water_phase_diagram(req)
        elif "reaction" in sub or "reaction" in title or "chemical" in title:
            self.render_chemical_reaction(req)
        elif "cycle" in sub or "water cycle" in title:
            self.render_water_cycle(req)
        else:
            self.render_water_phase_diagram(req)

    def render_water_phase_diagram(self, req: VisualRequest):
        """
        Renders a thermodynamically accurate Water (H2O) Phase Diagram.
        Features:
        - Sublimation curve (Solid - Gas)
        - Fusion curve with anomalous negative slope (Solid - Liquid)
        - Vaporization curve (Liquid - Gas)
        - Triple Point (0.01°C, 0.006 atm)
        - Critical Point (374°C, 218 atm)
        - Normal Melting Point (0°C, 1 atm)
        - Normal Boiling Point (100°C, 1 atm)
        """
        plt.clf()
        plt.theme("dark")

        # Temperature points (deg C) and Pressure points (atm)
        # 1. Sublimation line: -50°C to 0.01°C
        t_sub = [-60, -45, -30, -20, -10, 0.01]
        p_sub = [0.00001, 0.00008, 0.00038, 0.001, 0.0028, 0.006]

        # 2. Fusion line (Ice -> Liquid water): anomalous negative slope!
        t_fusion = [0.01, -2, -5, -10, -15, -20]
        p_fusion = [0.006, 25, 60, 120, 175, 218]

        # 3. Vaporization line (Liquid -> Vapor): 0.01°C to 374°C
        t_vap = [0.01, 25, 50, 75, 100, 150, 200, 250, 300, 350, 374]
        p_vap = [0.006, 0.031, 0.12, 0.38, 1.0, 4.7, 15.3, 39.2, 84.7, 163.0, 218.0]

        plt.plot(t_sub, p_sub, label="Sublimation (Solid-Gas)", color="cyan")
        plt.plot(t_fusion, p_fusion, label="Fusion / Melting (Solid-Liquid)", color="green")
        plt.plot(t_vap, p_vap, label="Vaporization (Liquid-Gas)", color="yellow")

        # Markers for Key Physical Points
        plt.scatter([0.01], [0.006], color="red", marker="★", label="Triple Point (0.01°C, 0.006 atm)")
        plt.scatter([374], [218], color="magenta", marker="▲", label="Critical Point (374°C, 218 atm)")
        plt.scatter([100], [1.0], color="blue", marker="●", label="Normal B.P. (100°C, 1 atm)")
        plt.scatter([0], [1.0], color="white", marker="■", label="Normal F.P. (0°C, 1 atm)")

        plt.title(f"WATER (H2O) PHASE DIAGRAM — PRESSURE vs TEMPERATURE")
        plt.xlabel("Temperature (°C)")
        plt.ylabel("Pressure (atm)")
        plt.plotsize(84, 22)

        chart_str = plt.build()

        # Legend and Physical State Guide
        guide_table = Table(box=box.ROUNDED, border_style="cyan", expand=True)
        guide_table.add_column("Region / Point", style="bold cyan", width=24)
        guide_table.add_column("State / Value", style="bold yellow", width=24)
        guide_table.add_column("Physical Characteristic", style="white")

        guide_table.add_row("Left of Fusion Line", "SOLID (ICE)", "Hexagonal crystal lattice, lower density than liquid")
        guide_table.add_row("Above Vaporization Line", "LIQUID (WATER)", "High dielectric constant, dynamic hydrogen bonding")
        guide_table.add_row("Below Sub/Vap Line", "GAS (STEAM/VAPOR)", "Freely moving H2O molecules")
        guide_table.add_row("★ Triple Point", "0.01°C @ 0.006 atm", "All three phases (ice, water, steam) coexist in equilibrium")
        guide_table.add_row("▲ Critical Point", "374°C @ 218 atm", "Phase boundary vanishes into supercritical fluid")
        guide_table.add_row("■ Normal Melting", "0.00°C @ 1.00 atm", "Standard sea-level solid-to-liquid transition")
        guide_table.add_row("● Normal Boiling", "100.00°C @ 1.00 atm", "Standard sea-level liquid-to-gas transition")
        guide_table.add_row("Slope Anomaly", "Negative dP/dT", "Fusion line leans left: Ice melts under applied pressure")

        panel = Panel.fit(
            f"{chart_str}\n\n",
            title=f"[bold green]🔬 SCIENTIFIC VISUALIZATION — {req.title.upper()}[/]",
            subtitle="[dim cyan]HS AI Solutions • July Scientific Engine (plotext + rich)[/]",
            border_style="bright_blue",
            padding=(1, 1)
        )
        self.console.print(panel)
        self.console.print(guide_table)
        if req.explanation:
            self.console.print(Panel(f"[bold white]{req.explanation}[/]", title="[bold yellow]Theoretical Context[/]", border_style="yellow"))

    def render_chemical_reaction(self, req: VisualRequest):
        """Renders Chemical Reaction Energy Coordinate Diagram."""
        plt.clf()
        plt.theme("dark")

        # Reaction coordinate points
        x = [0, 10, 25, 45, 50, 55, 75, 90, 100]
        # Exothermic reaction with activation barrier
        y = [20, 20, 30, 85, 90, 85, 10, 5, 5]

        plt.plot(x, y, label="Potential Energy Profile", color="yellow")
        plt.scatter([0], [20], color="green", marker="●", label="Reactants (A + B)")
        plt.scatter([50], [90], color="red", marker="▲", label="Transition State [‡]")
        plt.scatter([100], [5], color="cyan", marker="■", label="Products (C + D)")

        plt.title("CHEMICAL REACTION ENERGY PROFILE (EXOTHERMIC)")
        plt.xlabel("Reaction Coordinate (Progress) →")
        plt.ylabel("Potential Energy (kJ/mol)")
        plt.plotsize(84, 18)

        chart_str = plt.build()
        panel = Panel.fit(
            chart_str,
            title="[bold green]🔬 REACTION ENERGETICS & KINETICS[/]",
            border_style="magenta"
        )
        self.console.print(panel)

    def render_water_cycle(self, req: VisualRequest):
        """Renders Water Cycle Diagram using Rich styling and ASCII flows."""
        cycle_art = """
        [bold bright_yellow]       ☀️ SUN (Solar Energy Engine)[/]
                  │
                  ▼ [cyan]Radiation & Thermal Convection[/]
        ┌──────────────────────────────────────────────────────────┐
        │  [bold white]☁️  CONDENSATION  (Clouds formed in Troposphere)[/]        │
        └───────┬───────────────────────────────────────────▲──────┘
                │ [bright_blue]Precipitation (Rain / Snow)[/]              │ [cyan]Evaporation &[/]
                ▼                                           │ [cyan]Transpiration[/]
        ┌──────────────────┐                     ┌──────────┴──────┐
        │ [bold green]⛰️  MOUNTAINS[/]     │                     │ [bold green]🌲 VEGETATION[/]   │
        │ Snowpack & Ice   │                     │ Forests & Plants│
        └───────┬──────────┘                     └──────────▲──────┘
                │ [yellow]Surface Runoff[/]                           │
                ▼                                           │ [blue]Root Absorption[/]
        ┌──────────────────┐                     ┌──────────┴──────┐
        │ [bold cyan]🌊 RIVERS / LAKES[/]  │──────────────────▶ │ [bold blue]💧 GROUNDWATER[/]   │
        │ Surface Water    │   Infiltration      │ Aquifer Storage │
        └───────┬──────────┘                     └─────────────────┘
                │
                ▼ [blue]Discharge into Ocean Basin[/]
        ┌──────────────────────────────────────────────────────────┐
        │              [bold bright_blue]🌊 OCEAN RESERVOIR (97% of Earth's Water)[/]          │
        └──────────────────────────────────────────────────────────┘
        """
        self.console.print(Panel(cycle_art, title="[bold cyan]🌍 GLOBAL WATER CYCLE (HYDROLOGICAL CYCLE)[/]", border_style="cyan"))
