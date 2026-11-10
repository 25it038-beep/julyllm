"""
HS AI SOLUTIONS — TRANSFORMER ARCHITECTURE RENDERER
Module: july_distribution.client.visual.renderers.transformer
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Family: HS AI FAMILY

Renders Transformer Block topology (Multi-Head Attention, RoPE, SwiGLU, RMSNorm, Residuals).
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ..models import VisualRequest


class TransformerRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        title = req.title or "Transformer Layer Architecture (JULY LLM 3B / Llama 3.2)"

        self.console.print(Panel(
            f"[bold white]{title.upper()}[/]\n"
            "[dim]Decoder-Only Autoregressive Transformer Block with GQA, RoPE & SwiGLU[/]",
            title="[bold green]⚡ TRANSFORMER BLOCK TOPOLOGY[/]",
            border_style="bright_blue",
            expand=False
        ))

        art = (
            "                [bold cyan]INPUT TOKENS / HIDDEN STATE x_l[/]\n"
            "                              │\n"
            "            ┌─────────────────┴─────────────────┐  (Residual Skip)\n"
            "            │                                   │\n"
            "            ▼                                   │\n"
            "    ┌───────────────┐                           │\n"
            "    │    RMSNorm    │                           │\n"
            "    └───────┬───────┘                           │\n"
            "            ▼                                   │\n"
            "   ┌─────────────────┐                          │\n"
            "   │ Grouped-Query   │ [Q: 24 heads, KV: 8 heads]│\n"
            "   │ Attention (GQA) │ [RoPE Base: 500,000.0]   │\n"
            "   └────────┬────────┘                          │\n"
            "            ▼                                   │\n"
            "            └─────────────────┬─────────────────┘\n"
            "                              ▼  [Residual Addition]\n"
            "            ┌─────────────────┴─────────────────┐  (Residual Skip)\n"
            "            │                                   │\n"
            "            ▼                                   │\n"
            "    ┌───────────────┐                           │\n"
            "    │    RMSNorm    │                           │\n"
            "    └───────┬───────┘                           │\n"
            "            ▼                                   │\n"
            "   ┌─────────────────┐                          │\n"
            "   │ SwiGLU FFN      │ [d_model: 3072, d_ff: 8192]│\n"
            "   │ (Gate * Up -> Dn│                          │\n"
            "   └────────┬────────┘                          │\n"
            "            ▼                                   │\n"
            "            └─────────────────┬─────────────────┘\n"
            "                              ▼  [Residual Addition]\n"
            "                [bold green]OUTPUT TO NEXT BLOCK x_{l+1}[/]"
        )
        self.console.print(Panel(art, title="[bold magenta]TENSOR DATAFLOW & ATTENTION HEADS[/]", border_style="magenta", expand=False))

        t = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
        t.add_column("Sublayer", style="bold cyan")
        t.add_column("Configuration", style="yellow")
        t.add_column("Dimensions", style="green")
        t.add_column("Math Formulation", style="white")

        t.add_row("Pre-Attn Norm", "RMSNorm (eps=1e-5)", "[B, T, 3072]", "x_norm = x / RMS(x)")
        t.add_row("GQA Attention", "24 Q-heads, 8 KV-heads (3:1 ratio)", "q:[B,T,24,128], k,v:[B,T,8,128]", "Softmax(Q K^T / sqrt(d) + Mask) V")
        t.add_row("Positional Encoding", "Rotary Positional Embeddings (RoPE)", "Dim=128, Base=500000", "R_theta * [x1, x2]^T")
        t.add_row("Pre-FFN Norm", "RMSNorm (eps=1e-5)", "[B, T, 3072]", "x_norm2 = x / RMS(x)")
        t.add_row("SwiGLU FFN", "Swish-Gated Linear Unit", "Hidden: 8192", "(Swish(x W_gate) * (x W_up)) W_down")

        self.console.print(t)
