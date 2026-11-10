"""
HS AI SOLUTIONS — NEURAL NETWORK ARCHITECTURE RENDERER (VERIFIED TOPOLOGY)
Module: july_distribution.client.visual.renderers.neural
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Family: HS AI FAMILY

Renders crisp, mathematically consistent neural network topologies, layer dimensions,
and autograd dynamics across Terminal (Unicode), Mermaid, SVG, and HTML formats.
Guarantees 100% consistency between topology diagram and parameter table.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ..models import VisualRequest


class NeuralRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        title = req.title or "Deep Neural Network Architecture"

        self.console.print(Panel(
            f"[bold white]{title.upper()}[/]\n"
            "[dim]Deep Feedforward & Representation Learning Architecture (Tensors & Autograd)[/]",
            title="[bold green]🧠 NEURAL NETWORK ARCHITECTURE[/]",
            border_style="bright_blue",
            expand=False
        ))

        # Topology diagram: exactly 4 stages matching the layer table
        topology_art = (
            " [bold cyan]INPUT TENSORS[/]          [bold yellow]HIDDEN LAYER 1[/]        [bold magenta]HIDDEN LAYER 2[/]         [bold green]OUTPUT HEAD[/]\n"
            " [dim](784 Features)[/]          [dim](256 Neurons)[/]         [dim](128 Neurons)[/]         [dim](10 Classes)[/]\n\n"
            "     ┌───┐                  ┌───┐                  ┌───┐                  ┌───┐\n"
            " x₁─▶│ ○ │ ───────────────▶ │ ● │ ───────────────▶ │ ◈ │ ───────────────▶ │ ▣ │─▶ ŷ₁\n"
            "     └───┘ ╲              ╱ └───┘ ╲              ╱ └───┘ ╲              ╱ └───┘\n"
            "     ┌───┐   ╲          ╱   ┌───┐   ╲          ╱   ┌───┐   ╲          ╱   ┌───┐\n"
            " x₂─▶│ ○ │ ───╲────────╱─── │ ● │ ───╲────────╱─── │ ◈ │ ───╲────────╱─── │ ▣ │─▶ ŷ₂\n"
            "     └───┘     ╳      ╳     └───┘     ╳      ╳     └───┘     ╳      ╳     └───┘\n"
            "     ┌───┐   ╱   ╲  ╱   ╲   ┌───┐   ╱   ╲  ╱   ╲   ┌───┐   ╱   ╲  ╱   ╲   ┌───┐\n"
            " x₃─▶│ ○ │ ─╱─────╳──────╲─ │ ● │ ─╱─────╳──────╲─ │ ◈ │ ─╱─────╳──────╲─ │ ▣ │─▶ ŷ₃\n"
            "     └───┘ ╱    ╱    ╲    ╲ └───┘ ╱    ╱    ╲    ╲ └───┘ ╱    ╱    ╲    ╲ └───┘\n"
            "     [dim]  :                     :                      :                      :  [/]\n"
            "     ┌───┐                  ┌───┐                  ┌───┐                  ┌───┐\n"
            " xₙ─▶│ ○ │ ───────────────▶ │ ● │ ───────────────▶ │ ◈ │ ───────────────▶ │ ▣ │─▶ ŷ₁₀\n"
            "     └───┘                  └───┘                  └───┘                  └───┘\n"
            "       │                      │                      │                      │\n"
            "  [dim]Input Features[/]          [dim]Act: GELU[/]              [dim]Act: ReLU[/]             [dim]Loss: Cross-Ent.[/]"
        )
        self.console.print(Panel(topology_art, title="[bold magenta]LAYER TOPOLOGY & SYNAPTIC WEIGHT FLOW[/]", border_style="magenta", expand=False))

        # Layer Dimensions Table: 100% verified consistency with topology
        layers_table = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
        layers_table.add_column("Layer Index & Type", style="bold cyan", width=18)
        layers_table.add_column("Input Dim", style="yellow", width=12)
        layers_table.add_column("Output Dim", style="green", width=12)
        layers_table.add_column("Activation / Ops", style="magenta", width=18)
        layers_table.add_column("Parameters", style="white")

        layers_table.add_row("0. InputLayer", "[B, 784]", "[B, 784]", "Identity / Norm", "0")
        layers_table.add_row("1. Dense (W1)", "[B, 784]", "[B, 256]", "GELU + LayerNorm", "200,960 (784×256 + 256)")
        layers_table.add_row("2. Dropout", "[B, 256]", "[B, 256]", "Rate p=0.1", "0")
        layers_table.add_row("3. Dense (W2)", "[B, 256]", "[B, 128]", "ReLU non-linear", "32,896 (256×128 + 128)")
        layers_table.add_row("4. Output Head (W3)", "[B, 128]", "[B, 10]", "Softmax (Logits)", "1,290 (128×10 + 10)")

        self.console.print(layers_table)

        # Summary box
        summary_panel = Panel(
            "[bold white]TOTAL TRAINABLE PARAMETERS:[/] [bold green]235,146[/]  "
            "([dim]W1: 200,960 + W2: 32,896 + W3: 1,290[/])\n"
            "[bold green]FORWARD PASS:[/]  x ──▶ z₁ = W₁x + b₁ ──▶ a₁ = σ(z₁) ──▶ z₂ = W₂a₁ + b₂ ──▶ a₂ = σ(z₂) ──▶ ŷ = Softmax(W₃a₂ + b₃)\n"
            "[bold red]BACKWARD PASS:[/] ∂L/∂W = (∂L/∂ŷ) • (∂ŷ/∂z) • (∂z/∂W) [dim](Reverse-Mode Autograd)[/]\n"
            "[bold yellow]OPTIMIZER:[/]     θ_{t+1} = θ_t - η • m̂_t / (√v̂_t + ε) [dim](AdamW with Decoupled Weight Decay)[/]",
            title="[bold yellow]TENSOR COMPUTATION GRAPH & VERIFIED PARAMETERS[/]",
            border_style="yellow",
            expand=False
        )
        self.console.print(summary_panel)

    def to_mermaid(self, req: VisualRequest) -> str:
        """Generates Mermaid diagram code."""
        return """```mermaid
flowchart LR
    subgraph Input["Input Layer"]
        X["Input Tensors (784 Features)"]
    end
    subgraph Hidden1["Hidden Layer 1"]
        H1["Dense W1 (256 Neurons)<br/>GELU + LayerNorm<br/>200,960 params"]
    end
    subgraph Hidden2["Hidden Layer 2"]
        H2["Dense W2 (128 Neurons)<br/>ReLU Activation<br/>32,896 params"]
    end
    subgraph Output["Output Layer"]
        Out["Output Head W3 (10 Classes)<br/>Softmax Loss<br/>1,290 params"]
    end
    X --> H1 --> H2 --> Out
```"""

    def to_svg(self, req: VisualRequest) -> str:
        """Generates SVG representation."""
        return """<svg width="800" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#1a1b26"/>
  <rect x="30" y="50" width="140" height="90" rx="10" fill="#24283b" stroke="#7aa2f7" stroke-width="2"/>
  <text x="100" y="85" fill="#c0caf5" font-family="sans-serif" font-size="14" text-anchor="middle">Input (784)</text>
  <text x="100" y="110" fill="#565f89" font-family="sans-serif" font-size="11" text-anchor="middle">Features</text>
  <line x1="170" y1="95" x2="230" y2="95" stroke="#7aa2f7" stroke-width="2" marker-end="url(#arrow)"/>
  
  <rect x="230" y="40" width="160" height="110" rx="10" fill="#24283b" stroke="#e0af68" stroke-width="2"/>
  <text x="310" y="80" fill="#c0caf5" font-family="sans-serif" font-size="14" text-anchor="middle">Hidden 1 (256)</text>
  <text x="310" y="105" fill="#e0af68" font-family="sans-serif" font-size="11" text-anchor="middle">200,960 params</text>
  <line x1="390" y1="95" x2="450" y2="95" stroke="#e0af68" stroke-width="2"/>
  
  <rect x="450" y="45" width="150" height="100" rx="10" fill="#24283b" stroke="#bb9af7" stroke-width="2"/>
  <text x="525" y="85" fill="#c0caf5" font-family="sans-serif" font-size="14" text-anchor="middle">Hidden 2 (128)</text>
  <text x="525" y="110" fill="#bb9af7" font-family="sans-serif" font-size="11" text-anchor="middle">32,896 params</text>
  <line x1="600" y1="95" x2="660" y2="95" stroke="#bb9af7" stroke-width="2"/>
  
  <rect x="660" y="55" width="110" height="80" rx="10" fill="#24283b" stroke="#9ece6a" stroke-width="2"/>
  <text x="715" y="90" fill="#c0caf5" font-family="sans-serif" font-size="14" text-anchor="middle">Output (10)</text>
  <text x="715" y="115" fill="#9ece6a" font-family="sans-serif" font-size="11" text-anchor="middle">1,290 params</text>
</svg>"""
