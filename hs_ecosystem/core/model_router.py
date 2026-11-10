"""
HS AI SOLUTIONS — DUAL MODEL INTELLIGENT ROUTER (AUTO MODE)
Module: hs_ecosystem.core.model_router
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Dynamically routes user tasks to JULY LLM or GRAVITY LLM based on task taxonomy,
algorithmic depth requirements, and hardware memory budgeting.
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .model_manager import UniversalModelManager


@dataclass
class RoutingDecision:
    selected_model: str  # "july" or "gravity"
    mode: str            # "AUTO" or "MANUAL_OVERRIDE"
    rationale: str
    confidence: float
    detected_domain: str
    hardware_notes: str


class IntelligentModelRouter:
    """
    Evaluates prompts and assigns either July or Gravity model with transparent reasoning.
    """

    GRAVITY_DOMAINS = [
        "calculus", "differential equation", "linear algebra", "tensor",
        "mechanics", "quantum", "physics simulation", "algorithm proof",
        "asymptotic complexity", "low-level c", "assembly", "formal verification",
        "underdetermined system", "fourier transform", "matrix decomposition"
    ]

    JULY_DOMAINS = [
        "general knowledge", "conversational", "summary", "creative writing",
        "fullstack", "javascript", "typescript", "python scripting", "powershell",
        "visual representation", "flowchart", "uml", "diagram", "web search"
    ]

    def __init__(self, manager: UniversalModelManager):
        self.manager = manager

    def route_prompt(self, prompt: str, requested_mode: str = "AUTO") -> RoutingDecision:
        """
        Routes the prompt to July or Gravity.
        If requested_mode is 'JULY' or 'GRAVITY', honors manual override.
        """
        mode_norm = requested_mode.upper()
        if mode_norm in ("JULY", "GRAVITY"):
            mid = mode_norm.lower()
            return RoutingDecision(
                selected_model=mid,
                mode="MANUAL_OVERRIDE",
                rationale=f"User explicitly locked execution to {mid.upper()} LLM.",
                confidence=1.0,
                detected_domain="user_specified",
                hardware_notes="Explicit allocation."
            )

        # AUTO MODE Evaluation
        p_lower = prompt.lower()
        score_gravity = 0
        score_july = 0

        for kw in self.GRAVITY_DOMAINS:
            if kw in p_lower:
                score_gravity += 2

        # Math and physics indicators
        if re.search(r"[\+\-\*\/\^=]{3,}", p_lower) or re.search(r"\b(dx|dy|integral|dt|eigen|matrix|latex|proof)\b", p_lower):
            score_gravity += 3

        for kw in self.JULY_DOMAINS:
            if kw in p_lower:
                score_july += 2

        if re.search(r"\b(who are you|hello|hi|explain simply|summarize|diagram|draw|powershell)\b", p_lower):
            score_july += 3

        # Memory / Warm Model Affinity bonus:
        # If one model is already active in memory on constrained hardware, prefer keeping it if task is balanced
        active = self.manager.active_model_id
        if active == "july":
            score_july += 1
        elif active == "gravity":
            score_gravity += 1

        if score_gravity > score_july:
            selected = "gravity"
            domain = "deep_mathematics_and_systems"
            rationale = (
                "Task requires rigorous mathematical deduction, algorithmic proofs, or physical systems analysis. "
                "Assigned to GRAVITY LLM for high-precision computation."
            )
            conf = min(0.98, 0.70 + 0.05 * (score_gravity - score_july))
        else:
            selected = "july"
            domain = "conversational_and_multidisciplinary"
            rationale = (
                "Task benefits from multi-disciplinary synthesis, software engineering, visual rendering, or conversational fluency. "
                "Assigned to JULY LLM."
            )
            conf = min(0.98, 0.70 + 0.05 * (score_july - score_gravity))

        hw = self.manager.hardware
        hw_notes = f"Allocated on {hw.gpu_name} ({hw.gpu_backend.upper()})."

        return RoutingDecision(
            selected_model=selected,
            mode="AUTO",
            rationale=rationale,
            confidence=round(conf, 2),
            detected_domain=domain,
            hardware_notes=hw_notes
        )
