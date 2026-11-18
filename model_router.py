"""
HS AI SOLUTIONS — INTELLIGENT MODEL ROUTER
Module: model_router.py
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM CLOUD & GRAVITY CLOUD

Dynamically routes incoming requests across the July AI Family based on intent,
domain taxonomy, complexity scoring, and multimodal markers.
Enforces seamless fallback to July Lite when specialized endpoints are offline.
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple, Union

from modal_config import settings, ModelSpec

logger = logging.getLogger("July.ModelRouter")


@dataclass
class RoutingDecision:
    selected_model: str       # "july-lite", "gravity", "july-vision", "july-code"
    target_model_id: str      # Resolved physical model checkpoint
    domain: str               # "general_conversation", "advanced_reasoning", "vision", "code_engineering"
    confidence: float         # 0.0 to 1.0
    rationale: str
    mode: str                 # "AUTO" or "MANUAL_OVERRIDE"
    fallback_model: str = "july-lite"
    metadata: Dict[str, Any] = None


class JulyModelRouter:
    """
    Intelligent Model Router for HS AI Solutions.
    Routes queries between:
    - July Lite: Fast responses, ordinary conversations, summaries, general queries.
    - Gravity: Complex mathematical proofs, physics simulations, tensor calculus, CAS.
    - July Vision: Image, screenshot, chart, diagram, and visual analysis.
    - July Code: Software engineering, debugging, syntax generation, architectural tasks.
    """

    GRAVITY_KEYWORDS = [
        "proof", "theorem", "lemma", "calculus", "differential equation", "tensor",
        "quantum", "physics simulation", "asymptotic complexity", "formal verification",
        "linear algebra", "eigenvalue", "matrix decomposition", "hamiltonian", "lagrangian",
        "stochastic", "fréchet", "underdetermined system", "fourier transform", "cas",
        "abstract algebra", "topology", "navier-stokes", "thermodynamics"
    ]

    SREE_KEYWORDS = [
        "sree", "dense reasoning", "step-by-step thinking", "multi-step verification",
        "think through", "deep reasoning", "chain-of-thought", "self-correct",
        "formal deduction", "olympiad", "imo math", "putnam", "competition math",
        "vibe thinker", "symbolic logic", "rigorous derivation"
    ]

    CODE_KEYWORDS = [
        "def ", "class ", "function", "refactor", "bug", "traceback", "syntax",
        "sql", "python", "typescript", "javascript", "golang", "rust", "c++",
        "dockerfile", "api endpoint", "regex", "git", "database schema", "unit test",
        "pytest", "asyncio", "fastapi", "react", "nextjs", "algorithm in", "powershell"
    ]

    VISION_KEYWORDS = [
        "image", "picture", "photo", "screenshot", "diagram", "chart", "visualize",
        "infographic", "drawing", "ocr", "layout", "visual representation", "ui design",
        "wireframe", "graph", "plot"
    ]

    def __init__(self):
        self.default_model = "july-lite"

    def analyze_messages(self, messages: List[Dict[str, Any]]) -> Tuple[str, bool]:
        """Concatenates textual context and checks for multimodal payload."""
        combined_text = []
        has_multimodal_content = False

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                combined_text.append(content)
            elif isinstance(content, list):
                # OpenAI format with multimodal content parts
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") in ("image_url", "image"):
                            has_multimodal_content = True
                        elif part.get("type") == "text":
                            combined_text.append(part.get("text", ""))

        return " ".join(combined_text), has_multimodal_content

    def route(
        self,
        prompt_or_messages: Union[str, List[Dict[str, Any]]],
        requested_model: Optional[str] = None
    ) -> RoutingDecision:
        """
        Determines the optimal model destination.
        Honors explicit user model selection if specified (unless AUTO).
        """
        # Parse text and check for multimodal attachments
        if isinstance(prompt_or_messages, str):
            query_text = prompt_or_messages
            has_image = False
        else:
            query_text, has_image = self.analyze_messages(prompt_or_messages)

        query_lower = query_text.lower().strip()

        # -------------------------------------------------------------------
        # 1. Manual Override Handling
        # -------------------------------------------------------------------
        if requested_model:
            norm_requested = requested_model.lower().strip()
            # If explicit model passed and it's not "auto"
            if norm_requested not in ("auto", "default", "july-auto"):
                spec = settings.get_model_spec(norm_requested)
                if spec:
                    target_id = "gravity" if spec.model_id == "gravity" else ("sree" if spec.model_id == "sree" else "july-lite")
                    return RoutingDecision(
                        selected_model=spec.model_id,
                        target_model_id=target_id,
                        domain=f"manual_{spec.model_id}",
                        confidence=1.0,
                        rationale=f"User explicitly designated model '{spec.model_id}'.",
                        mode="MANUAL_OVERRIDE",
                        fallback_model="july-lite"
                    )

        # -------------------------------------------------------------------
        # 2. Multimodal / Vision Detection
        # -------------------------------------------------------------------
        if has_image:
            return RoutingDecision(
                selected_model="july-vision",
                target_model_id="july-lite",
                domain="vision",
                confidence=0.98,
                rationale="Detected image/multimodal attachment in payload. Routed to July Vision.",
                mode="AUTO",
                fallback_model="july-lite"
            )

        vision_matches = sum(1 for kw in self.VISION_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", query_lower))
        if vision_matches >= 2 and any(v in query_lower for v in ["inspect this", "analyze this image", "look at the chart"]):
            return RoutingDecision(
                selected_model="july-vision",
                target_model_id="july-lite",
                domain="vision",
                confidence=0.88,
                rationale="Visual reasoning and diagram interpretation intent detected.",
                mode="AUTO",
                fallback_model="july-lite"
            )

        # -------------------------------------------------------------------
        # 3. Code & Programming Detection
        # -------------------------------------------------------------------
        code_score = 0
        for kw in self.CODE_KEYWORDS:
            if kw in query_lower:
                code_score += 2
        # Check for code blocks or common code constructs
        if "```" in query_text or re.search(r"\b(def\s+\w+|class\s+\w+|import\s+\w+|function\s*\(|console\.log)\b", query_text):
            code_score += 5

        # -------------------------------------------------------------------
        # 4. Dense Reasoning & STEM / SREE Detection
        # -------------------------------------------------------------------
        sree_score = 0
        for kw in self.SREE_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", query_lower):
                sree_score += 3

        # -------------------------------------------------------------------
        # 5. Deep Mathematical / Physics / Gravity Detection
        # -------------------------------------------------------------------
        gravity_score = 0
        for kw in self.GRAVITY_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", query_lower):
                gravity_score += 2
        # Mathematical formulas / LaTeX / calculus notation
        if re.search(r"[\+\-\*\/\^=]{3,}", query_text) or re.search(r"\\(int|frac|partial|sum|prod|alpha|beta|sigma|nabla)\b", query_text):
            gravity_score += 4
        if re.search(r"\b(dx|dy|dt|eigenvalues|schrodinger|lagrangian)\b", query_lower):
            gravity_score += 3

        # -------------------------------------------------------------------
        # 6. Routing Arbitration
        # -------------------------------------------------------------------
        # SREE dense reasoning takes precedence when step-by-step thinking or sree intent is clear
        if sree_score >= 3 and sree_score >= gravity_score:
            return RoutingDecision(
                selected_model="sree",
                target_model_id="sree",
                domain="dense_cognitive_reasoning",
                confidence=min(0.99, 0.70 + (sree_score * 0.05)),
                rationale=(
                    f"Task requires dense cognitive reasoning, step-by-step verification, or STEM problem solving "
                    f"(Score: {sree_score}). Routed to SREE LLM."
                ),
                mode="AUTO",
                fallback_model="july-lite"
            )

        # Threshold checks
        if gravity_score >= 4 and gravity_score > code_score:
            return RoutingDecision(
                selected_model="gravity",
                target_model_id="gravity",
                domain="advanced_reasoning",
                confidence=min(0.99, 0.65 + (gravity_score * 0.05)),
                rationale=(
                    f"Task requires deep mathematical deduction, algorithmic proofs, or physical systems analysis "
                    f"(Score: {gravity_score}). Routed to GRAVITY LLM."
                ),
                mode="AUTO",
                fallback_model="july-lite"
            )

        if code_score >= 4:
            return RoutingDecision(
                selected_model="july-code",
                target_model_id="july-lite",
                domain="code_engineering",
                confidence=min(0.99, 0.65 + (code_score * 0.05)),
                rationale=(
                    f"Task identified as software engineering or code generation "
                    f"(Score: {code_score}). Routed to July Code."
                ),
                mode="AUTO",
                fallback_model="july-lite"
            )

        # Default: July Lite for fast, responsive, high-quality conversational output
        return RoutingDecision(
            selected_model="july-lite",
            target_model_id="july-lite",
            domain="general_conversation",
            confidence=0.95,
            rationale="Fast conversational reasoning and general intelligence. Routed to July Lite.",
            mode="AUTO",
            fallback_model="july-lite"
        )

    def resolve_fallback(self, decision: RoutingDecision, error_reason: str) -> RoutingDecision:
        """Gracefully routes to July Lite if the selected target encountered a fault."""
        logger.warning(
            f"Model '{decision.selected_model}' unavailable ({error_reason}). "
            f"Failing over to resilient foundation model '{decision.fallback_model}'."
        )
        return RoutingDecision(
            selected_model=decision.fallback_model,
            target_model_id="july-lite",
            domain=decision.domain,
            confidence=0.80,
            rationale=f"Fallback invoked: Original target '{decision.selected_model}' offline ({error_reason}).",
            mode="FALLBACK",
            fallback_model="july-lite",
            metadata={"original_model": decision.selected_model, "fault_reason": error_reason}
        )


router = JulyModelRouter()
