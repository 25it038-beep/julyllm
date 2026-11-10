"""
HS AI SOLUTIONS — SCIENTIFIC DIAGRAM RENDERER (HIGH-CLARITY)
Module: july_distribution.client.visual.renderers.scientific
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders crisp, high-clarity scientific diagrams fitted to terminal width:
- Water Phase Diagram (Thermodynamically labeled regions, negative slope fusion line, triple point, critical point)
- Chemical Reaction Energy Profiles (Reactants, Ea, Transition State, Products, ΔH)
- Global Hydrological Water Cycle
"""

from __future__ import annotations
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

        if "phase" in sub or "phase" in title:
            self.render_water_phase_diagram(req)
        elif "reaction" in sub or "reaction" in title or "chemical" in title:
            self.render_chemical_reaction(req)
        elif "cycle" in sub or "water cycle" in title:
            self.render_water_cycle(req)
        else:
            self.render_water_phase_diagram(req)

    def render_water_phase_diagram(self, req: VisualRequest):
        """
        Renders a crystal-clear, properly proportioned Water (H2O) Phase Diagram:
        - Geometric phase boundaries with anomalous negative-slope fusion line.
        - Numerical P-T plot scaled to console width.
        - Thermodynamic state classification table.
        """
        w = max(40, min(self.console.width - 4, 75))

        # 1. Structural Schematic Map (Guaranteed readable on any terminal >= 60 cols)
        schematic = (
            "[bold yellow]PRESSURE (P)[/]\n"
            "   ▲\n"
            "218├─────────────────────────────────────────────────▲ [bold magenta]Critical Point[/]\n"
            "atm│                                                │ [dim](374°C, 218 atm)[/]\n"
            "   │       [bold cyan]SOLID (ICE)[/]             [bold green]LIQUID (WATER)[/]     │\n"
            "   │                            │                   │\n"
            " 1 ├────────────────────────────┼───────────●───────┤ [bold white]Normal B.P.[/]\n"
            "atm│                            │         (100°C)   │ [dim](1.0 atm, 100°C)[/]\n"
            "   │   [dim]Negative Fusion Line ──▶[/] ╱                   │\n"
            "   │   [dim](Ice melts with press.)[/] ╱                    │\n"
            "0.0├──────────────────────────★─────────────────────┘\n"
            "06 │   [bold red]★ TRIPLE POINT[/]        ╱ [dim]Vaporization Line[/]\n"
            "atm│   [bold red](0.01°C, 0.006 atm)[/]   ╱\n"
            "   │                         ╱\n"
            "   │   [dim]Sublimation Line ──▶[/] ╱         [bold yellow]GAS (WATER VAPOR / STEAM)[/]\n"
            " 0 └─────────────────────────┴─────────────┴─────────┴────────▶ [bold yellow]TEMP (T)[/]\n"
            "   -50°C                    0.01°C        100°C     374°C\n"
            "                         [dim]Freezing[/]      [dim]Boiling[/]   [dim]Critical[/]"
        )

        header = Panel(
            "[bold white]WATER (H2O) THERMODYNAMIC PHASE DIAGRAM[/]\n"
            "[dim]Pressure-Temperature (P-T) State Boundaries & Critical Phenomena[/]",
            title="[bold green]🔬 SCIENTIFIC VISUALIZATION[/]",
            border_style="bright_blue",
            expand=False
        )
        self.console.print(header)

        # Print the structural schematic
        self.console.print(Panel(schematic, title="[bold cyan]PHASE MAP & EQUILIBRIUM BOUNDARIES[/]", border_style="cyan", expand=False))

        # 2. Numerical Plotext Curve (Strictly calibrated to console width)
        try:
            plt.clf()
            plt.theme("dark")

            # Points for vaporization curve
            t_vap = [0.01, 25, 50, 75, 100, 150, 200, 250, 300, 374]
            p_vap = [0.006, 0.03, 0.12, 0.38, 1.0, 4.7, 15.3, 39.2, 84.7, 218.0]

            # Fusion curve (negative slope: temp decreases as pressure rises)
            t_fus = [0.01, -2, -5, -10, -15, -20]
            p_fus = [0.006, 25, 60, 120, 175, 218]

            plt.plot(t_vap, p_vap, label="Vaporization (Liq-Gas)", color="yellow")
            plt.plot(t_fus, p_fus, label="Fusion (Solid-Liq)", color="green")
            plt.scatter([0.01], [0.006], color="red", marker="★", label="Triple Pt")
            plt.scatter([374], [218], color="magenta", marker="▲", label="Critical Pt")
            plt.scatter([100], [1.0], color="white", marker="●", label="Normal BP")

            w = max(30, min(self.console.width - 24, 54))
            plt.title("VAPOR PRESSURE & PHASE EQUILIBRIUM CURVE")
            plt.xlabel("Temperature (°C)")
            plt.ylabel("Pressure (atm)")
            plt.plotsize(w, 11)

            plot_text = plt.build()
            self.console.print(Panel(Text.from_ansi(plot_text), title="[bold yellow]NUMERICAL P-T PHASE EQUILIBRIUM PLOT[/]", border_style="yellow", expand=False))
        except Exception:
            pass

        # 3. Thermodynamic Classification Table
        guide = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
        guide.add_column("Phase / Point", style="bold cyan", width=18)
        guide.add_column("Coordinates", style="bold yellow", width=18)
        guide.add_column("Thermodynamic Significance", style="white")

        guide.add_row("Solid (Ice Ih)", "Left of fusion line", "Hexagonal open crystal lattice (density = 0.917 g/cm³)")
        guide.add_row("Liquid (Water)", "Between fus & vap", "High dielectric constant; maximum density at 3.98°C")
        guide.add_row("Gas (Steam)", "Below sub & vap line", "Monomeric H2O vapor obeying real gas equation")
        guide.add_row("★ Triple Point", "0.01°C, 0.006 atm", "Zero degrees of freedom (F = 0 via Gibbs Phase Rule)")
        guide.add_row("▲ Critical Point", "374.0°C, 218.0 atm", "Meniscus vanishes; gas and liquid densities equalize")
        guide.add_row("● Normal Boiling", "100.0°C, 1.00 atm", "Vapor pressure equals 1 atm atmospheric pressure")
        guide.add_row("Negative Slope", "dP/dT < 0", "Anomalous ΔV_fus < 0: Ice melts upon compression")

        self.console.print(guide)

    def render_chemical_reaction(self, req: VisualRequest):
        """Renders Chemical Reaction Energy Coordinate Diagram."""
        w = max(30, min(self.console.width - 24, 54))
        try:
            plt.clf()
            plt.theme("dark")

            x = [0, 10, 25, 45, 50, 55, 75, 90, 100]
            y = [20, 20, 30, 85, 90, 85, 10, 5, 5]

            plt.plot(x, y, label="Energy Profile", color="yellow")
            plt.scatter([0], [20], color="green", marker="●", label="Reactants")
            plt.scatter([50], [90], color="red", marker="▲", label="Trans. State [‡]")
            plt.scatter([100], [5], color="cyan", marker="■", label="Products")

            plt.title("EXOTHERMIC REACTION ENERGY PROFILE")
            plt.xlabel("Reaction Coordinate →")
            plt.ylabel("Potential Energy (kJ/mol)")
            plt.plotsize(w, 11)

            plot_text = plt.build()
            self.console.print(Panel(Text.from_ansi(plot_text), title="[bold green]🔬 REACTION ENERGETICS & ACTIVATION BARRIER[/]", border_style="green", expand=False))
        except Exception:
            pass

    def render_water_cycle(self, req: VisualRequest):
        """Renders Water Cycle Diagram."""
        cycle_art = (
            "         [bold bright_yellow]☀️ SUN (Solar Thermal Driving Force)[/]\n"
            "                   │\n"
            "                   ▼ [cyan]Radiation & Heating[/]\n"
            "   ┌────────────────────────────────────────────────────────┐\n"
            "   │  [bold white]☁️  CONDENSATION  (Cloud & Droplet Formation)[/]          │\n"
            "   └───────┬────────────────────────────────────────▲───────┘\n"
            "           │ [bright_blue]Precipitation (Rain/Snow)[/]              │ [cyan]Evaporation &[/]\n"
            "           ▼                                        │ [cyan]Transpiration[/]\n"
            "   ┌─────────────────┐                    ┌─────────┴───────┐\n"
            "   │ [bold green]⛰️  MOUNTAINS[/]    │                    │ [bold green]🌲 FORESTS[/]       │\n"
            "   │ Snowpack & Glac.│                    │ Plant Biosphere │\n"
            "   └───────┬─────────┘                    └─────────▲───────┘\n"
            "           │ [yellow]Surface Runoff[/]                          │\n"
            "           ▼                                        │ [blue]Soil Moisture[/]\n"
            "   ┌─────────────────┐                    ┌─────────┴───────┐\n"
            "   │ [bold cyan]🌊 RIVERS / LAKES[/] │───────────────────▶ │ [bold blue]💧 GROUNDWATER[/]  │\n"
            "   │ Freshwater Flow │    Infiltration    │ Deep Aquifers   │\n"
            "   └───────┬─────────┘                    └─────────────────┘\n"
            "           │\n"
            "           ▼ [blue]Discharge to Ocean Basin[/]\n"
            "   ┌────────────────────────────────────────────────────────┐\n"
            "   │           [bold bright_blue]🌊 OCEAN BASIN (97% of Global Hydrosphere)[/]           │\n"
            "   └────────────────────────────────────────────────────────┘"
        )
        self.console.print(Panel(cycle_art, title="[bold cyan]🌍 GLOBAL HYDROLOGICAL WATER CYCLE[/]", border_style="cyan", expand=False))
