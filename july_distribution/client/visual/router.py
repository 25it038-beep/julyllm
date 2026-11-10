"""
HS AI SOLUTIONS — INTELLIGENT VISUAL ROUTER
Module: july_distribution.client.visual.router
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Identifies when visual representation is requested or required, resolves intent,
and constructs structured VisualRequest objects for the terminal engine.
"""

from __future__ import annotations
import re
import json
from typing import Optional, Tuple, Dict, Any

from .models import VisualRequest


class VisualRouter:
    @staticmethod
    def detect_from_text(text: str) -> Optional[VisualRequest]:
        """
        Inspects model response or prompt text for structured <visual>...</visual>
        or ```visual ... ``` blocks.
        """
        # 1. Look for <visual> JSON block or <visual { ... }>
        m = re.search(r"<visual>([\s\S]*?)</visual>", text, re.IGNORECASE)
        if m:
            req = VisualRequest.from_json(m.group(1).strip())
            if req:
                return req

        m2 = re.search(r"<visual\s*(\{[^{}]*\"visualization_type\"[^{}]*\})", text, re.IGNORECASE)
        if m2:
            req = VisualRequest.from_json(m2.group(1).strip())
            if req:
                return req

        # 2. Look for ```visual JSON block
        m = re.search(r"```visual\s*\n([\s\S]*?)\n```", text, re.IGNORECASE)
        if m:
            req = VisualRequest.from_json(m.group(1).strip())
            if req:
                return req

        # 3. Look for ```mermaid block
        m = re.search(r"```mermaid\s*\n([\s\S]*?)\n```", text, re.IGNORECASE)
        if m:
            code = m.group(1).strip()
            return VisualRequest(
                visualization_type="flowchart",
                title="Mermaid Visual Graph",
                data={"mermaid_code": code}
            )

        return None

    @staticmethod
    def route_user_prompt(prompt: str) -> Optional[VisualRequest]:
        """
        Analyzes the user's prompt to determine if on-demand visual explanation was requested.
        """
        p = prompt.lower().strip()

        # 1. Binary Search
        if ("binary search" in p and any(w in p for w in ["visual", "explain", "draw", "show", "step", "animate", "trace"])) or p == "explain binary search visually" or "binary search visualization" in p:
            return VisualRequest(
                visualization_type="animator",
                title="Binary Search Step-by-Step Visualization",
                explanation="Binary search operates on sorted arrays in O(log n) time by continually halving the search interval.",
                data={"subtype": "binary_search", "target": 23, "array": [2, 5, 8, 12, 16, 23, 38, 45, 56, 72, 91]}
            )

        # 2. Water Phase Diagram
        if ("phase diagram" in p) or ("water phase" in p) or ("phase transition" in p and "water" in p):
            return VisualRequest(
                visualization_type="scientific",
                title="Water (H2O) Phase Diagram",
                explanation="Water exhibits an anomalous negative fusion slope (dP/dT < 0), meaning ice melts under increasing pressure.",
                data={"subtype": "phase_diagram"}
            )

        # 3. CPU Architecture
        if ("cpu architecture" in p) or ("cpu internal" in p) or ("von neumann" in p and "architecture" in p) or ("show cpu" in p):
            return VisualRequest(
                visualization_type="architecture",
                title="Von Neumann & Modern CPU Microarchitecture",
                explanation="Instruction cycle executes via Control Unit sequencing, Arithmetic Logic Unit computation, Register file buffering, and multi-tier Cache hierarchy.",
                data={"subtype": "cpu_architecture"}
            )

        # 4. Neural Network Architecture
        if ("neural network architecture" in p) or ("deep learning architecture" in p) or ("draw neural network" in p) or ("neural network" in p and any(w in p for w in ["draw", "show", "architecture", "visual"])):
            return VisualRequest(
                visualization_type="neural",
                title="Deep Multilayer Perceptron & Neural Representation",
                explanation="Tensors flow forward through linear transformations and non-linear activations; gradients propagate backward via autograd chain rule.",
                data={"subtype": "neural_network"}
            )

        # 4b. Transformer Architecture
        if ("transformer" in p and any(w in p for w in ["architecture", "draw", "show", "visual", "block", "layer"])) or "attention mechanism" in p or "gqa" in p:
            return VisualRequest(
                visualization_type="transformer",
                title="Decoder-Only Transformer Block (GQA, RoPE & SwiGLU)",
                explanation="Grouped-Query Attention with Rotary Embeddings followed by RMSNorm and SwiGLU Feed-Forward Networks.",
                data={"subtype": "transformer"}
            )

        # 5. Electrical Circuit
        if ("circuit" in p and any(w in p for w in ["draw", "show", "explain", "diagram", "electrical", "schematic"])) or "electrical circuit" in p:
            subtype = "rlc" if "rlc" in p or "ac" in p else ("logic" if "logic" in p or "gate" in p else "dc")
            return VisualRequest(
                visualization_type="circuit",
                title="Electrical Circuit Schematic & Network Analysis",
                explanation="Governed by Kirchhoff's Voltage Law (KVL: ΣV = 0) and Kirchhoff's Current Law (KCL: ΣI = 0).",
                data={"subtype": subtype}
            )

        # 6. OS Scheduling Animation
        if ("scheduling" in p and any(w in p for w in ["os", "process", "algorithm", "round robin", "cpu", "visualize", "animate"])) or "os scheduling" in p or "round robin" in p:
            return VisualRequest(
                visualization_type="animator",
                title="Operating System Process Scheduling (Round Robin)",
                explanation="Preemptive scheduling allocates fixed time quantum (q=4ms) across ready queue processes to ensure low latency and fair sharing.",
                data={"subtype": "os_scheduling"}
            )

        # 7. Deadlock
        if ("deadlock" in p and any(w in p for w in ["explain", "visual", "draw", "diagram", "show"])) or "resource allocation graph" in p:
            return VisualRequest(
                visualization_type="architecture",
                title="OS Deadlock & Resource Allocation Graph",
                explanation="A circular wait cycle across non-preemptible, mutually exclusive resources leads to permanent process starvation.",
                data={"subtype": "deadlock"}
            )

        # 8. Chemical Reaction
        if "chemical reaction" in p and any(w in p for w in ["draw", "visual", "energy", "profile", "explain"]):
            return VisualRequest(
                visualization_type="scientific",
                title="Chemical Reaction Potential Energy Profile",
                explanation="Molecules must surmount the activation energy barrier (Ea) to reach the transition state before forming products.",
                data={"subtype": "chemical_reaction"}
            )

        # 9. Water Cycle
        if "water cycle" in p and any(w in p for w in ["draw", "visual", "diagram", "show", "explain"]):
            return VisualRequest(
                visualization_type="scientific",
                title="Global Hydrological (Water) Cycle",
                explanation="Continuous mass transport of water via evaporation, condensation, precipitation, and runoff driven by solar radiation.",
                data={"subtype": "water_cycle"}
            )

        # 10. Math Graph / Plot
        if ("plot" in p and any(w in p for w in ["function", "math", "curve", "sin", "sigmoid", "relu"])) or "mathematical function" in p:
            fn_type = "sigmoid" if "sigmoid" in p else ("relu" if "relu" in p else ("sin" if "sin" in p else "standard"))
            return VisualRequest(
                visualization_type="math_plot",
                title=f"Mathematical Plot: {fn_type.upper()}",
                explanation="Terminal-native continuous functional mapping using plotext braille and ASCII character rendering.",
                data={"function_type": fn_type}
            )

        # 11. UML
        if "uml" in p or "class diagram" in p:
            return VisualRequest(
                visualization_type="uml",
                title="UML Class Diagram & System Architecture",
                explanation="Structural representation of classes, encapsulated fields, operational methods, and inheritance/aggregation hierarchies.",
                data={"subtype": "uml"}
            )

        return None
