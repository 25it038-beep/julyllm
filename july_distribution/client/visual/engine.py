"""
HS AI SOLUTIONS — JULY VISUAL RESPONSE ENGINE (MULTI-MODAL FORMAT)
Module: july_distribution.client.visual.engine
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Family: HS AI FAMILY

Core Universal Visual Response Engine.
Renders high-fidelity diagrams, graphs, circuits, neural networks, transformers, and animations
across Terminal (Unicode / ANSI), Mermaid, SVG, and HTML / Canvas formats.
Not restricted to PowerShell: works in bash, cmd, IDEs, and browser sidecars.
"""

from __future__ import annotations
import os
import sys
from typing import Optional, Dict, Any
from rich.console import Console

from .models import VisualRequest
from .router import VisualRouter
from .renderers.scientific import ScientificRenderer
from .renderers.math_plot import MathPlotRenderer
from .renderers.architecture import ArchitectureRenderer
from .renderers.neural import NeuralRenderer
from .renderers.transformer import TransformerRenderer
from .renderers.circuit import CircuitRenderer
from .renderers.animator import ProcessAnimator
from .renderers.uml import UMLRenderer
from .renderers.flowchart import FlowchartRenderer
from .renderers.data_vis import DataVisRenderer


class VisualResponseEngine:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.scientific_renderer = ScientificRenderer(self.console)
        self.math_renderer = MathPlotRenderer(self.console)
        self.arch_renderer = ArchitectureRenderer(self.console)
        self.neural_renderer = NeuralRenderer(self.console)
        self.transformer_renderer = TransformerRenderer(self.console)
        self.circuit_renderer = CircuitRenderer(self.console)
        self.animator = ProcessAnimator(self.console)
        self.uml_renderer = UMLRenderer(self.console)
        self.flowchart_renderer = FlowchartRenderer(self.console)
        self.data_renderer = DataVisRenderer(self.console)

    def determine_output_format(self, user_prompt: str) -> str:
        """Determines best output format: terminal, mermaid, svg, or html."""
        p = user_prompt.lower()
        if "mermaid" in p:
            return "mermaid"
        if "svg" in p:
            return "svg"
        if "html" in p or "browser" in p or "canvas" in p:
            return "html"
        return "terminal"

    def render_request(self, req: VisualRequest, output_format: str = "terminal") -> Optional[str]:
        """Dispatches VisualRequest to the appropriate specialized renderer and format."""
        vtype = req.visualization_type.lower().strip()

        if output_format == "mermaid":
            if vtype in ("neural", "neural_network", "deep_learning"):
                code = self.neural_renderer.to_mermaid(req)
                print(f"\n{code}\n")
                return code
            elif "mermaid_code" in req.data:
                code = f"```mermaid\n{req.data['mermaid_code']}\n```"
                print(f"\n{code}\n")
                return code

        if output_format == "svg":
            if vtype in ("neural", "neural_network", "deep_learning"):
                svg = self.neural_renderer.to_svg(req)
                print(f"\n{svg}\n")
                return svg

        # Terminal-native rendering (Universal across PowerShell, Linux Bash, Windows Terminal, macOS)
        if vtype in ("scientific", "phase_diagram", "chemical_reaction", "water_cycle"):
            self.scientific_renderer.render(req)
        elif vtype in ("math_plot", "math", "graph", "plot"):
            self.math_renderer.render(req)
        elif vtype in ("architecture", "cpu_architecture", "deadlock", "os_architecture"):
            self.arch_renderer.render(req)
        elif vtype in ("transformer", "transformer_block", "attention", "rope"):
            self.transformer_renderer.render(req)
        elif vtype in ("neural", "neural_network", "deep_learning", "mlp"):
            self.neural_renderer.render(req)
        elif vtype in ("circuit", "electrical_circuit", "rlc"):
            self.circuit_renderer.render(req)
        elif vtype in ("animator", "binary_search", "os_scheduling", "animation"):
            self.animator.render(req)
        elif vtype in ("uml", "class_diagram"):
            self.uml_renderer.render(req)
        elif vtype in ("data_chart", "data_vis", "bar_chart"):
            self.data_renderer.render(req)
        else:
            self.flowchart_renderer.render(req)

        return None

    def process_and_render(self, user_prompt: str, model_response: str = "") -> bool:
        """
        Detects if a visual request is present in model response or implied by user prompt,
        determines appropriate format, and renders it directly. Returns True if rendered.
        """
        fmt = self.determine_output_format(user_prompt)

        # 1. Try to detect structured visual block in model output
        req = VisualRouter.detect_from_text(model_response)
        if not req:
            # 2. Try to detect visual intent from user prompt
            req = VisualRouter.route_user_prompt(user_prompt)

        if req:
            self.render_request(req, output_format=fmt)
            return True

        return False
