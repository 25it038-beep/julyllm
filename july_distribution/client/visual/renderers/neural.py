"""
HS AI SOLUTIONS — NEURAL NETWORK ARCHITECTURE RENDERER
Module: july_distribution.client.visual.renderers.neural
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders multilayer neural networks, deep learning architectures, tensor shapes, activations, and weight flows.
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

        # 1. Structural Layer Overview Table
        layers_table = Table(box=box.ROUNDED, border_style="cyan", expand=True)
        layers_table.add_column("Layer Index & Type", style="bold cyan", width=22)
        layers_table.add_column("Input Shape", style="yellow", width=16)
        layers_table.add_column("Output Shape", style="green", width=16)
        layers_table.add_column("Activation / Ops", style="magenta", width=20)
        layers_table.add_column("Parameters (W + b)", style="white")

        layers_table.add_row("0. InputLayer", "[B, 784]", "[B, 784]", "Identity / Normalize", "0 (Sensory Data)")
        layers_table.add_row("1. Dense (Linear_1)", "[B, 784]", "[B, 256]", "GELU + LayerNorm", "200,960 (784×256 + 256)")
        layers_table.add_row("2. Dropout (p=0.1)", "[B, 256]", "[B, 256]", "Inverted Inactive Mask", "0")
        layers_table.add_row("3. Dense (Linear_2)", "[B, 256]", "[B, 128]", "ReLU / Swish", "32,896 (256×128 + 128)")
        layers_table.add_row("4. Dense (Linear_3)", "[B, 128]", "[B, 64]", "ReLU", "8,256 (128×64 + 64)")
        layers_table.add_row("5. Output Head", "[B, 64]", "[B, 10]", "Softmax (Categorical)", "650 (64×10 + 10)")

        # 2. ASCII Connected Topology Diagram
        topology_art = """
   [bold cyan]INPUT LAYER[/]            [bold yellow]HIDDEN LAYER 1[/]        [bold magenta]HIDDEN LAYER 2[/]         [bold green]OUTPUT LAYER[/]
   [dim](784 Features)[/]          [dim](256 Neurons)[/]         [dim](128 Neurons)[/]         [dim](10 Classes)[/]

       ┌───┐                  ┌───┐                  ┌───┐                  ┌───┐
  x₁ ─▶│ ○ │ ───────────────▶ │ ● │ ───────────────▶ │ ◈ │ ───────────────▶ │ ▣ │ ─▶ ŷ₁ (P)
       └───┘ ╲              ╱ └───┘ ╲              ╱ └───┘ ╲              ╱ └───┘
       ┌───┐   ╲          ╱   ┌───┐   ╲          ╱   ┌───┐   ╲          ╱   ┌───┐
  x₂ ─▶│ ○ │ ───╲────────╱─── │ ● │ ───╲────────╱─── │ ◈ │ ───╲────────╱─── │ ▣ │ ─▶ ŷ₂ (P)
       └───┘     ╳      ╳     └───┘     ╳      ╳     └───┘     ╳      ╳     └───┘
       ┌───┐   ╱   ╲  ╱   ╲   ┌───┐   ╱   ╲  ╱   ╲   ┌───┐   ╱   ╲  ╱   ╲   ┌───┐
  x₃ ─▶│ ○ │ ─╱─────╳──────╲─ │ ● │ ─╱─────╳──────╲─ │ ◈ │ ─╱─────╳──────╲─ │ ▣ │ ─▶ ŷ₃ (P)
       └───┘ ╱    ╱    ╲    ╲ └───┘ ╱    ╱    ╲    ╲ └───┘ ╱    ╱    ╲    ╲ └───┘
       [dim]  :                     :                      :                      :  [/]
       ┌───┐                  ┌───┐                  ┌───┐                  ┌───┐
  xₙ ─▶│ ○ │ ───────────────▶ │ ● │ ───────────────▶ │ ◈ │ ───────────────▶ │ ▣ │ ─▶ ŷ₁₀
       └───┘                  └───┘                  └───┘                  └───┘
         │                      │                      │                      │
    [dim]Raw Sensory[/]             [dim]W₁•x + b₁[/]              [dim]W₂•h₁ + b₂[/]            [dim]Softmax Logits[/]
    [dim]Tensor Vectors[/]          [dim]Act: GELU[/]              [dim]Act: ReLU[/]             [dim]Loss: Cross-Entropy[/]
        """

        # 3. Forward & Backward Flow Summary
        flow_panel = Panel(
            "[bold green]FORWARD PASS:[/]  x ──▶ z₁ = W₁x + b₁ ──▶ a₁ = σ(z₁) ──▶ ... ──▶ ŷ = Softmax(z_L) ──▶ Loss(y, ŷ)\n"
            "[bold red]BACKWARD PASS:[/] ∂L/∂W = (∂L/∂ŷ) • (∂ŷ/∂z) • (∂z/∂W) [dim](Automatic Reverse-Mode Differentiation)[/]\n"
            "[bold yellow]OPTIMIZER:[/]     θ_{t+1} = θ_t - η • m̂_t / (√v̂_t + ε) [dim](AdamW with Decoupled Weight Decay)[/]",
            title="[bold yellow]TENSOR COMPUTATION GRAPH (AUTOGRAD DYNAMICS)[/]",
            border_style="yellow",
            box=box.ROUNDED
        )

        self.console.print(Panel(
            f"[bold white]{title.upper()}[/]\n"
            "[dim]Deep Feedforward & Representation Learning Architecture[/]",
            title="[bold cyan]🧠 NEURAL NETWORK ARCHITECTURE[/]",
            border_style="cyan"
        ))

        self.console.print(Panel(topology_art, title="[bold magenta]LAYER TOPOLOGY & SYNAPTIC WEIGHT INTERCONNECTS[/]", border_style="magenta"))
        self.console.print(layers_table)
        self.console.print(flow_panel)

        if req.explanation:
            self.console.print(Panel(f"[bold white]{req.explanation}[/]", title="[bold green]Deep Learning Principles[/]", border_style="green"))
