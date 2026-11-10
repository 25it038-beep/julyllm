"""
HS AI SOLUTIONS — JULY VISUAL RESPONSE ENGINE
Module: july_distribution.client.visual.engine
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Core On-Demand Visual Response Engine.
Renders high-fidelity diagrams, graphs, circuits, and animations directly inside PowerShell / Windows Terminal.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from rich.console import Console

from .models import VisualRequest
from .router import VisualRouter
from .renderers.scientific import ScientificRenderer
from .renderers.math_plot import MathPlotRenderer
from .renderers.architecture import ArchitectureRenderer
from .renderers.neural import NeuralRenderer
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
        self.circuit_renderer = CircuitRenderer(self.console)
        self.animator = ProcessAnimator(self.console)
        self.uml_renderer = UMLRenderer(self.console)
        self.flowchart_renderer = FlowchartRenderer(self.console)
        self.data_renderer = DataVisRenderer(self.console)

    def render_request(self, req: VisualRequest):
        """Dispatches VisualRequest to the appropriate specialized terminal renderer."""
        vtype = req.visualization_type.lower().strip()

        if vtype in ("scientific", "phase_diagram", "chemical_reaction", "water_cycle"):
            self.scientific_renderer.render(req)
        elif vtype in ("math_plot", "math", "graph", "plot"):
            self.math_renderer.render(req)
        elif vtype in ("architecture", "cpu_architecture", "deadlock", "os_architecture"):
            self.arch_renderer.render(req)
        elif vtype in ("neural", "neural_network", "deep_learning"):
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

    def process_and_render(self, user_prompt: str, model_response: str = "") -> bool:
        """
        Detects if a visual request is present in model response or implied by user prompt,
        and renders it directly to the terminal. Returns True if a visual was rendered.
        """
        # 1. Try to detect structured visual block in model output
        req = VisualRouter.detect_from_text(model_response)
        if not req:
            # 2. Try to detect visual intent from user prompt
            req = VisualRouter.route_user_prompt(user_prompt)

        if req:
            self.render_request(req)
            return True

        return False
