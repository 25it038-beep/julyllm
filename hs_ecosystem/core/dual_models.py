"""
HS AI SOLUTIONS — DUAL MODEL INDEPENDENT CORES (JULY & GRAVITY)
Module: hs_ecosystem.core.dual_models
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Defines independent model personalities, prompt templates, and streaming interfaces
for JULY LLM and GRAVITY LLM. Preserves strict identity isolation.
"""

from __future__ import annotations
import time
from typing import Dict, Any, Generator, Optional, List
from pathlib import Path

from .model_manager import UniversalModelManager
from july_distribution.client.reasoning import JulyReasoningOrchestrator, OrchestratedReasoningResult


class JulyModelCore:
    """
    Dedicated Core for JULY LLM.
    Identity: JULY LLM | Founder: Harshan Seliyan | HS AI Solutions.
    Domain: Conversational fluency, multi-disciplinary synthesis, software engineering, and visual intelligence.
    """

    MODEL_ID = "july"
    DISPLAY_NAME = "JULY LLM"

    SYSTEM_PROMPT = (
        "You are JULY LLM, an advanced intelligent AI model developed and maintained by HS AI Solutions, "
        "founded by Harshan Seliyan. You belong to the JULY AI Family.\n\n"
        "PERMANENT IDENTITY:\n"
        "- MODEL: JULY LLM\n"
        "- DEVELOPER: HS AI Solutions\n"
        "- FOUNDER: Harshan Seliyan\n"
        "- MISSION: Developing intelligent AI systems.\n"
        "- PERSONALITY: Analytical, Technically capable, Curious, Adaptive, Honest, Creative, Direct, Consistent.\n\n"
        "GUIDELINES:\n"
        "- Avoid unnecessary introductions or conversational filler; deliver practical, actionable explanations.\n"
        "- Provide rigorous technical and mathematical solutions when required.\n"
        "- For underdetermined systems or insufficient probabilities, state degrees of freedom and Fréchet bounds explicitly."
    )

    def __init__(self, manager: UniversalModelManager):
        self.manager = manager
        self.orchestrator = JulyReasoningOrchestrator()

    def format_chat_prompt(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        prompt = f"<|start_header_id|>system<|end_header_id|>\n\n{self.SYSTEM_PROMPT}<|eot_id|>"
        if history:
            for m in history:
                prompt += f"<|start_header_id|>{m['role']}<|end_header_id|>\n\n{m['content']}<|eot_id|>"
        prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|>"
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return prompt

    def generate_stream(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.6
    ) -> Generator[str, None, None]:
        llm = self.manager.get_instance("july")
        if not llm:
            yield "[Error: JULY LLM could not be initialized in memory.]"
            return

        formatted = self.format_chat_prompt(user_message, history)
        stream = llm(
            formatted,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["<|eot_id|>", "<|end_of_text|>", "<|endoftext|>"],
            stream=True
        )

        full_resp = []
        t0 = time.time()
        for chunk in stream:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("text", "")
                if delta:
                    full_resp.append(delta)
                    yield delta

        elapsed = max(0.001, time.time() - t0)
        tps = len(full_resp) / elapsed
        self.manager.states["july"].last_inference_speed_tps = round(tps, 1)

    def generate_verified(self, user_message: str) -> OrchestratedReasoningResult:
        tokens = list(self.generate_stream(user_message))
        raw_text = "".join(tokens)
        return self.orchestrator.validate_and_synthesize_response(user_message, raw_text)


class GravityModelCore:
    """
    Dedicated Core for GRAVITY LLM.
    Identity: GRAVITY LLM | Founder: Harshan Seliyan | HS AI Solutions.
    Domain: Deep mathematical proofs, formal systems, physical algorithms, and computational mechanics.
    """

    MODEL_ID = "gravity"
    DISPLAY_NAME = "GRAVITY LLM"

    SYSTEM_PROMPT = (
        "You are GRAVITY LLM, a frontier mathematical and algorithmic language model developed and maintained by "
        "HS AI Solutions, founded by Harshan Seliyan. You belong to the GRAVITY AI Family.\n\n"
        "PERMANENT IDENTITY:\n"
        "- MODEL: GRAVITY LLM\n"
        "- DEVELOPER: HS AI Solutions\n"
        "- FOUNDER: Harshan Seliyan\n"
        "- MISSION: Pushing the boundaries of mathematical and physical computing.\n"
        "- PERSONALITY: Deeply mathematical, Algorithmic, First-principles oriented, Exhaustive, Robust, Precise.\n\n"
        "SPECIALIZATION & GUIDELINES:\n"
        "- Focus on axiomatic mathematical deductions, tensor mechanics, and formal algorithmic proofs.\n"
        "- Distinguish exact analytical solutions from numerical approximations.\n"
        "- Analyze problem constraints with extreme boundary rigor."
    )

    def __init__(self, manager: UniversalModelManager):
        self.manager = manager
        self.orchestrator = JulyReasoningOrchestrator()

    def format_chat_prompt(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        prompt = f"<|start_header_id|>system<|end_header_id|>\n\n{self.SYSTEM_PROMPT}<|eot_id|>"
        if history:
            for m in history:
                prompt += f"<|start_header_id|>{m['role']}<|end_header_id|>\n\n{m['content']}<|eot_id|>"
        prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|>"
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return prompt

    def generate_stream(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.4
    ) -> Generator[str, None, None]:
        llm = self.manager.get_instance("gravity")
        if not llm:
            yield "[Error: GRAVITY LLM could not be initialized in memory.]"
            return

        formatted = self.format_chat_prompt(user_message, history)
        stream = llm(
            formatted,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["<|eot_id|>", "<|end_of_text|>", "<|endoftext|>"],
            stream=True
        )

        full_resp = []
        t0 = time.time()
        for chunk in stream:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("text", "")
                if delta:
                    full_resp.append(delta)
                    yield delta

        elapsed = max(0.001, time.time() - t0)
        tps = len(full_resp) / elapsed
        self.manager.states["gravity"].last_inference_speed_tps = round(tps, 1)

    def generate_verified(self, user_message: str) -> OrchestratedReasoningResult:
        tokens = list(self.generate_stream(user_message))
        raw_text = "".join(tokens)
        return self.orchestrator.validate_and_synthesize_response(user_message, raw_text)
