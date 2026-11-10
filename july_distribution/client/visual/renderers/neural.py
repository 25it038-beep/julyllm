"""
HS AI SOLUTIONS — NEURAL NETWORK ARCHITECTURE RENDERER (HIGH-CLARITY)
Module: july_distribution.client.visual.renderers.neural
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders crisp, high-clarity neural network topologies, layer dimensions, and autograd dynamics.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
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

        # Layer Dimensions Table
        layers_table = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
        layers_table.add_column("Layer Index & Type", style="bold cyan", width=18)
        layers_table.add_column("Input Dim", style="yellow", width=12)
        layers_table.add_column("Output Dim", style="green", width=12)
        layers_table.add_column("Activation / Ops", style="magenta", width=18)
        layers_table.add_column("Parameters", style="white")

        layers_table.add_row("0. InputLayer", "[B, 784]", "[B, 784]", "Identity / Norm", "0")
        layers_table.add_row("1. Dense (W1)", "[B, 784]", "[B, 256]", "GELU + LayerNorm", "200,960 (784×256+256)")
        layers_table.add_row("2. Dropout", "[B, 256]", "[B, 256]", "Rate p=0.1", "0")
        layers_table.add_row("3. Dense (W2)", "[B, 256]", "[B, 128]", "ReLU non-linear", "32,896 (256×128+128)")
        layers_table.add_row("4. Dense (W3)", "[B, 128]", "[B, 64]", "ReLU non-linear", "8,256 (128×64+64)")
        layers_table.add_row("5. Output Head", "[B, 64]", "[B, 10]", "Softmax (Logits)", "650 (64×10+10)")

        self.console.print(layers_table)

        flow_panel = Panel(
            "[bold green]FORWARD PASS:[/]  x ──▶ z₁ = W₁x + b₁ ──▶ a₁ = σ(z₁) ──▶ ... ──▶ ŷ = Softmax(z_L)\n"
            "[bold red]BACKWARD PASS:[/] ∂L/∂W = (∂L/∂ŷ) • (∂ŷ/∂z) • (∂z/∂W) [dim](Reverse-Mode Autograd)[/]\n"
            "[bold yellow]OPTIMIZER:[/]     θ_{t+1} = θ_t - η • m̂_t / (√v̂_t + ε) [dim](AdamW with Decoupled Decay)[/]",
            title="[bold yellow]TENSOR COMPUTATION GRAPH[/]",
            border_style="yellow",
            expand=False
        )
        self.console.print(flow_panel)
