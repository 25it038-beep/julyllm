"""
HS AI SOLUTIONS — UML DIAGRAM RENDERER
Module: july_distribution.client.visual.renderers.uml
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders UML Class diagrams, inheritance hierarchies, and design patterns directly in the terminal.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ..models import VisualRequest


class UMLRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        title = req.title or "UML Class Architecture"

        uml_art = (
            " ┌─────────────────────────────────────────────────────────┐\n"
            " │                 [bold cyan]<<interface / abstract>>[/]                 │\n"
            " │                      [bold yellow]NeuralModel[/]                        │\n"
            " ├─────────────────────────────────────────────────────────┤\n"
            " │ - model_id: UUID                                        │\n"
            " │ - param_count: int                                      │\n"
            " │ - is_quantized: bool                                    │\n"
            " ├─────────────────────────────────────────────────────────┤\n"
            " │ + forward(inputs: Tensor): Tensor                       │\n"
            " │ + backward(loss: Tensor): None                          │\n"
            " │ + save_weights(path: Path): bool                        │\n"
            " └────────────────────────────┬────────────────────────────┘\n"
            "                              │\n"
            "                              ▲ [dim]<<implements / inherits>>[/]\n"
            "              ┌───────────────┴───────────────┐\n"
            "              │                               │\n"
            " ┌────────────┴────────────┐     ┌────────────┴────────────┐\n"
            " │      [bold green]TransformerDecoder[/]  │     │      [bold magenta]ConvolutionalBackbone[/]│\n"
            " ├─────────────────────────┤     ├─────────────────────────┤\n"
            " │ - num_heads: int        │     │ - kernel_size: int      │\n"
            " │ - context_window: int   │     │ - channels: int         │\n"
            " │ - rotary_emb: RoPE      │     │ - stride: int           │\n"
            " ├─────────────────────────┤     ├─────────────────────────┤\n"
            " │ + generate_tokens()     │     │ + extract_features()    │\n"
            " │ + compute_attention()   │     │ + max_pool_2d()         │\n"
            " └─────────────────────────┘     └─────────────────────────┘\n"
            "              │                               │\n"
            "              │ [dim]1[/]                             │ [dim]*[/]\n"
            "              ▼ [dim]<<aggregates>>[/]                 ▼ [dim]<<composed of>>[/]\n"
            " ┌─────────────────────────┐     ┌─────────────────────────┐\n"
            " │      [bold cyan]KVCacheManager[/]     │     │      [bold cyan]ResidualBlock[/]      │\n"
            " ├─────────────────────────┤     ├─────────────────────────┤\n"
            " │ - cache_tensors: list   │     │ - conv1: Conv2d         │\n"
            " │ + evict_oldest()        │     │ - bn1: BatchNorm2d      │\n"
            " └─────────────────────────┘     └─────────────────────────┘"
        )

        self.console.print(Panel(
            f"[bold white]{title.upper()}[/]\n"
            "[dim]Object-Oriented Design, Inheritance & Association Schema[/]",
            title="[bold cyan]📐 UML CLASS ARCHITECTURE[/]",
            border_style="cyan",
            expand=False
        ))

        self.console.print(Panel(uml_art, title="[bold yellow]CLASS SPECIFICATION & HIERARCHY[/]", border_style="yellow", expand=False))

        if req.explanation:
            self.console.print(Panel(f"[bold white]{req.explanation}[/]", title="[bold green]Design Pattern Analysis[/]", border_style="green"))
