"""
HS AI SOLUTIONS — UNCERTAINTY ESTIMATION & CONSTRAINT CHECKER
Module: july_distribution.client.reasoning.uncertainty
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Family: JULY AI Family

Calibrates uncertainty, detects missing constraints, flags unverified assumptions,
and prevents hallucinated certainty.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class UncertaintyAssessment:
    confidence_score: float  # 0.0 to 1.0
    has_sufficient_information: bool
    missing_variables: List[str] = field(default_factory=list)
    unstated_assumptions: List[str] = field(default_factory=list)
    uncertainty_reasons: List[str] = field(default_factory=list)
    exact_vs_approx: str = "exact"  # 'exact', 'approximation', 'bounded', 'unconstrained'
    recommended_disclaimer: Optional[str] = None


class UncertaintyEngine:
    """
    Evaluates informational completeness and calibrates response confidence.
    """

    def evaluate(self, query: str, math_info: Optional[Any] = None, logic_info: Optional[Any] = None) -> UncertaintyAssessment:
        missing_vars = []
        assumptions = []
        reasons = []
        sufficient = True
        exact_type = "exact"
        confidence = 0.95

        q_lower = query.lower()

        # Math checks
        if math_info:
            if getattr(math_info, "is_underdetermined", False):
                sufficient = False
                exact_type = "unconstrained"
                confidence = 0.85
                reasons.append("Problem contains underdetermined system of equations or unconstrained free variables.")
                if getattr(math_info, "unconstrained_vars", []):
                    missing_vars.extend(math_info.unconstrained_vars)
                    reasons.append(f"Variables {math_info.unconstrained_vars} do not appear in any constraining equation.")

            if getattr(math_info, "problem_type", "") == "probability_bounds":
                sufficient = False
                exact_type = "bounded"
                confidence = 0.90
                reasons.append("Insufficient data to compute a unique point probability (missing joint distribution or independence assumption).")
                assumptions.append("Assuming independence would be an ungrounded assumption.")

            if getattr(math_info, "is_inconsistent", False):
                sufficient = True
                exact_type = "inconsistent"
                confidence = 0.98
                reasons.append("System is mathematically contradictory (no solution exists).")

        # Logic checks
        if logic_info:
            if not getattr(logic_info, "is_valid", True):
                confidence = 0.90
                reasons.append("Premises contain direct logical contradiction.")

        # Textual clues for underspecified requests
        if re.search(r"\b(what will happen|predict the future|best in the world)\b", q_lower):
            confidence = min(confidence, 0.70)
            reasons.append("Inquiry involves subjective or forward-looking projections.")

        disclaimer = None
        if not sufficient:
            disclaimer = f"Note: Problem is under-specified. {' '.join(reasons)}"

        return UncertaintyAssessment(
            confidence_score=round(confidence, 3),
            has_sufficient_information=sufficient,
            missing_variables=missing_vars,
            unstated_assumptions=assumptions,
            uncertainty_reasons=reasons,
            exact_vs_approx=exact_type,
            recommended_disclaimer=disclaimer
        )
