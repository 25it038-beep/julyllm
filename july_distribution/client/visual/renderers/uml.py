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

        uml_art = """
        ┌─────────────────────────────────────────────────────────┐
        │                 [bold cyan]<<interface / abstract>>[/]                 │
        │                      [bold yellow]NeuralModel[/]                        │
        ├─────────────────────────────────────────────────────────┤
        │ - model_id: UUID                                        │
        │ - param_count: int                                      │
        │ - is_quantized: bool                                    │
        ├─────────────────────────────────────────────────────────┤
        │ + forward(inputs: Tensor): Tensor                       │
        │ + backward(loss: Tensor): None                          │
        │ + save_weights(path: Path): bool                        │
        └────────────────────────────┬────────────────────────────┘
                                     │
                                     ▲ [dim]<<implements / inherits>>[/]
                     ┌───────────────┴───────────────┐
                     │                               │
        ┌────────────┴────────────┐     ┌────────────┴────────────┐
        │      [bold green]TransformerDecoder[/]  │     │      [bold magenta]ConvolutionalBackbone[/]│
        ├─────────────────────────┤     ├─────────────────────────┤
        │ - num_heads: int        │     │ - kernel_size: int      │
        │ - context_window: int   │     │ - channels: int         │
        │ - rotary_emb: RoPE      │     │ - stride: int           │
        ├─────────────────────────┤     ├─────────────────────────┤
        │ + generate_tokens()     │     │ + extract_features()    │
        │ + compute_attention()   │     │ + max_pool_2d()         │
        └─────────────────────────┘     └─────────────────────────┘
                     │                               │
                     │ [dim]1[/]                             │ [dim]*[/]
                     ▼ [dim]<<aggregates>>[/]                 ▼ [dim]<<composed of>>[/]
        ┌─────────────────────────┐     ┌─────────────────────────┐
        │      [bold cyan]KVCacheManager[/]     │     │      [bold cyan]ResidualBlock[/]      │
        ├─────────────────────────┤     ├─────────────────────────┤
        │ - cache_tensors: list   │     │ - conv1: Conv2d         │
        │ + evict_oldest()        │     │ - bn1: BatchNorm2d      │
        └─────────────────────────┘     └─────────────────────────┘
        """

        self.console.print(Panel(
            f"[bold white]{title.upper()}[/]\n"
            "[dim]Object-Oriented Design, Inheritance & Association Schema[/]",
            title="[bold cyan]📐 UML CLASS ARCHITECTURE[/]",
            border_style="cyan"
        ))

        self.console.print(Panel(uml_art, title="[bold yellow]CLASS SPECIFICATION & HIERARCHY[/]", border_style="yellow"))

        if req.explanation:
            self.console.print(Panel(f"[bold white]{req.explanation}[/]", title="[bold green]Design Pattern Analysis[/]", border_style="green"))
