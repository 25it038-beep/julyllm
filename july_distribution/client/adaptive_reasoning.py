"""
HS AI SOLUTIONS — ADAPTIVE COGNITIVE REASONING & ACCELERATION ENGINE
Layer: ADAPTIVE REASONING & CODING ACCELERATOR (july_distribution.client.adaptive_reasoning)
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: SREE LLM & JULY AI CODING AGENT | Family: HS AI Family

Optimizes SREE LLM for minimum thinking overhead and maximum execution speed.
Implements:
1. Adaptive Thinking Levels: INSTANT, BALANCED, DEEP
2. Zero-Overhead Task Classification
3. Sree ChatML <think> Fast-Path Prefill Steering
4. Inference Pipeline Tuning (Temperature, Top-P, Stop Sequences, Flash Attention)
5. Anti-Loop Guards & Progress Tracking
6. Execution-First Coding Agent Pipeline
"""

from __future__ import annotations
import re
import time
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List, Set
from dataclasses import dataclass, field


class ThinkingLevel(str, Enum):
    INSTANT = "instant"            # Minimal/zero thinking overhead. Direct code implementation.
    CONVERSATIONAL = "conversational"  # Conversational dialogue with time, name, location, and opposite-gender tone.
    BALANCED = "balanced"          # Focused, concise reasoning (< 3 steps). Multi-file, APIs, components.
    DEEP = "deep"                  # Rigorous deep thinking. Complex algorithms, formal proofs, security.


@dataclass
class AdaptiveSteeringConfig:
    level: ThinkingLevel
    temperature: float
    top_p: float
    max_thinking_tokens: Optional[int]
    prefill_assistant: Optional[str]
    system_directive: str
    rationale: str


class AdaptiveReasoningEngine:
    """
    Intelligent Adaptive Reasoning Engine for SREE LLM & JULY AI.
    Selects the lowest sufficient reasoning level to maximize coding speed while preserving intelligence.
    """

    # Indicators for DEEP reasoning (Complex algorithms, formal proofs, security, race conditions)
    DEEP_KEYWORDS = [
        r"\b(dijkstra|a\*|bellman-ford|floyd-warshall|kruskal|prim)\b",
        r"\b(dynamic programming|memoization table|knapsack|levenshtein)\b",
        r"\b(red-black tree|avl tree|b-tree|trie|segment tree|fenwick)\b",
        r"\b(cryptography|rsa|elliptic curve|ecdsa|aes-gcm|zero-knowledge|diffie-hellman)\b",
        r"\b(formal proof|mathematical induction|theorem prover|invariant proof)\b",
        r"\b(distributed consensus|raft|paxos|byzantine|vector clock)\b",
        r"\b(concurrency race condition|deadlock prevention|mutex lock-free|memory barrier)\b",
        r"\b(security audit|exploit analysis|reverse engineering|buffer overflow|kernel driver)\b",
    ]

    # Indicators for BALANCED reasoning (Multi-file, API integrations, full component architecture)
    BALANCED_KEYWORDS = [
        r"\b(multi-file|multiple files|full stack|microservice|architecture refactor)\b",
        r"\b(api integration|oauth2|webhook|websocket|graphql schema)\b",
        r"\b(react component with state|redux|zustand|next\.js app router)\b",
        r"\b(database migration|sqlalchemy relationships|prisma schema|indexing strategy)\b",
        r"\b(integration test suite|mocking service|end-to-end test|docker compose)\b",
        r"\b(debug this complex error|trace stack trace|intermittent failure)\b",
    ]

    # Indicators for INSTANT execution (Direct functions, small fixes, scripts, basic queries)
    INSTANT_KEYWORDS = [
        r"\b(write a function|create a function|implement a function|write a script|create a script)\b",
        r"\b(write python code|write javascript|write typescript|write bash|write powershell|write sql)\b",
        r"\b(fix this typo|fix this bug|fix syntax error|one-liner|regex for|sql query for)\b",
        r"\b(create a component|button component|modal component|navbar component)\b",
        r"\b(convert.*to.*|parse.*to.*|format.*as.*|calculate.*|sort array|reverse string)\b",
        r"\b(write unit test|test case for|boilerplate for|template for)\b",
    ]

    # Indicators for CONVERSATIONAL dialogue, time, location, user identity, and greetings
    CONVERSATIONAL_TRIGGERS = [
        r"\b(hi|hello|hey|greetings|hola|namaste|sup|yo)\b",
        r"\b(good morning|good afternoon|good evening|good night)\b",
        r"\b(how are you|how do you do|how'?s it going|what'?s up)\b",
        r"\b(who am i|what is my name|what'?s my name|my name|do you know me|who is speaking)\b",
        r"\b(who are you|what are you|tell me about yourself|what is your name)\b",
        r"\b(what time is it|what is the time|current time|tell me the time|time now|what'?s the time)\b",
        r"\b(what is today'?s date|today'?s date|current date|what date is it|what is the date|what'?s the date)\b",
        r"\b(where am i|what is my location|my location|my timezone|my city|my country|where are we)\b",
        r"\b(time and location|time and date|who am i and where am i)\b",
        r"\b(how do you look|what do you look like|who created you|tell me a joke)\b",
    ]

    @classmethod
    def classify_task(cls, prompt: str, user_override: Optional[str] = None) -> Tuple[ThinkingLevel, str]:
        """
        Classifies the incoming programming task into INSTANT, BALANCED, or DEEP.
        Automatically selects the lowest sufficient reasoning level.
        """
        # 1. User manual override
        if user_override:
            u_clean = user_override.lower().strip()
            if u_clean in ("instant", "fast", "speed", "quick", "1"):
                return ThinkingLevel.INSTANT, "User explicitly selected INSTANT speed mode"
            if u_clean in ("conversational", "chat", "talk"):
                return ThinkingLevel.CONVERSATIONAL, "User explicitly selected CONVERSATIONAL mode"
            if u_clean in ("balanced", "medium", "normal", "standard", "2"):
                return ThinkingLevel.BALANCED, "User explicitly selected BALANCED mode"
            if u_clean in ("deep", "thorough", "complex", "reasoning", "3"):
                return ThinkingLevel.DEEP, "User explicitly selected DEEP reasoning mode"

        # Check prompt prefixes
        p_lower = prompt.lower().strip()
        if p_lower.startswith("[instant]") or p_lower.startswith("--instant") or p_lower.startswith("/instant"):
            return ThinkingLevel.INSTANT, "Task tagged with [INSTANT] flag"
        if p_lower.startswith("[deep]") or p_lower.startswith("--deep") or p_lower.startswith("/deep"):
            return ThinkingLevel.DEEP, "Task tagged with [DEEP] flag"
        if p_lower.startswith("[balanced]") or p_lower.startswith("--balanced") or p_lower.startswith("/balanced"):
            return ThinkingLevel.BALANCED, "Task tagged with [BALANCED] flag"

        # 2. Check for CONVERSATIONAL / TEMPORAL / IDENTITY dialogue signals
        is_explicit_code = any(re.search(pat, p_lower) for pat in [
            r"\b(write\s+(a\s+)?(function|script|code|program|class|method|component|app|algorithm|test))\b",
            r"\b(fix\s+(this\s+)?(error|bug|code|issue|exception|traceback|syntax))\b",
            r"\b(implement|refactor|debug|compile|benchmark|optimize\s+code)\b",
            r"\b(def\s+|class\s+|import\s+|const\s+|let\s+|function\s+)\b",
        ])
        if not is_explicit_code:
            for pat in cls.CONVERSATIONAL_TRIGGERS:
                if re.search(pat, p_lower):
                    return ThinkingLevel.CONVERSATIONAL, "Conversational / temporal / identity dialogue"

        # 3. Check for DEEP complexity signals
        for pat in cls.DEEP_KEYWORDS:
            if re.search(pat, p_lower):
                return ThinkingLevel.DEEP, f"Detected deep algorithmic / formal constraint: {pat}"

        # 4. Check for BALANCED multi-component signals
        for pat in cls.BALANCED_KEYWORDS:
            if re.search(pat, p_lower):
                return ThinkingLevel.BALANCED, f"Detected multi-file / architectural scope: {pat}"

        # 5. Check for direct code tasks
        for pat in cls.INSTANT_KEYWORDS:
            if re.search(pat, p_lower):
                return ThinkingLevel.INSTANT, "Detected straightforward coding implementation task"

        # 6. Short prompts (< 60 words without complex keywords) are INSTANT by default
        words = p_lower.split()
        if len(words) < 60 and not any(kw in p_lower for kw in ["compare architectures", "design system", "security audit"]):
            return ThinkingLevel.INSTANT, "Concise task scope — defaulted to INSTANT for maximum speed"

        return ThinkingLevel.BALANCED, "Standard programming task — assigned BALANCED reasoning"

    @classmethod
    def get_steering(cls, model_id: str, level: ThinkingLevel, rationale: str = "") -> AdaptiveSteeringConfig:
        """
        Produces optimal model steering, prefill tokens, and inference hyper-parameters.
        """
        is_sree = "sree" in (model_id or "").lower()

        if level == ThinkingLevel.CONVERSATIONAL:
            try:
                from .context_provider import RuntimeContextProvider
                u = RuntimeContextProvider.get_user_context()
                t = RuntimeContextProvider.get_temporal_context()
                l = RuntimeContextProvider.get_location_context()
                user_name = u.get("preferred_name", "Friend")
                opp_persona = u.get("opposite_gender_persona", "female")
                tone_summary = u.get("tone_summary", "Feminine, graceful, charming, warm, and deeply respectful")
                time_str = t.get("time_short", t.get("time", "Now"))
                date_str = t.get("date", "Today")
                loc_str = f"{l.get('city')}, {l.get('region')}, {l.get('country')}"
            except Exception:
                user_name = "Harshan"
                opp_persona = "female"
                tone_summary = "Feminine, graceful, charming, warm, and deeply respectful"
                time_str = "Now"
                date_str = "Today"
                loc_str = "Chennai, Tamil Nadu, India"

            sys_dir = (
                "[EXECUTION DIRECTIVE: CONVERSATIONAL OPPOSITE-GENDER ADAPTIVE MODE]\n"
                f"- Interaction Goal: Natural spoken dialogue, identity recognition, and temporal/geographical awareness.\n"
                f"- User Addressing: Naturally greet and address the user by name ('{user_name}').\n"
                f"- Opposite-Gender Tone Dynamic: You MUST speak in the {opp_persona.upper()} tone ({tone_summary}) based on user's name ({user_name}).\n"
                f"- Live Time, Date & Location: If asked or if greeting/needed in conversation, state the accurate local time ({time_str}), date ({date_str}), and location ({loc_str}).\n"
                f"- Dialogue Style: Warm, engaging, charming, and intelligent. Do NOT output code blocks or pseudocode."
            )
            prefill = f"<think>\nRespond conversationally to {user_name} with time, location, and {opp_persona} tone.\n</think>\n" if is_sree else None
            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.7,
                top_p=0.95,
                max_thinking_tokens=30,
                prefill_assistant=prefill,
                system_directive=sys_dir,
                rationale=rationale or "Conversational response with identity, time, location, and opposite-gender tone"
            )

        elif level == ThinkingLevel.INSTANT:
            sys_dir = (
                "[EXECUTION DIRECTIVE: INSTANT CODE-FIRST MODE]\n"
                "- Goal: Produce correct, functional, production-quality code with minimum reasoning overhead and maximum speed.\n"
                "- Do not deliberate on obvious programming decisions or spend time in lengthy internal analysis.\n"
                "- Immediately output the required code blocks, modules, or fixes.\n"
                "- Include necessary error handling, edge cases, and typing directly in the code."
            )
            # In ChatML format for Sree: Prefilling closed think tags eliminates reasoning delay!
            prefill = "<think>\nDirect implementation.\n</think>\n" if is_sree else None
            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.15,
                top_p=0.95,
                max_thinking_tokens=15,
                prefill_assistant=prefill,
                system_directive=sys_dir,
                rationale=rationale or "Zero-overhead instant code delivery"
            )

        elif level == ThinkingLevel.BALANCED:
            sys_dir = (
                "[EXECUTION DIRECTIVE: BALANCED CODING MODE]\n"
                "- Goal: Execute multi-component implementation with concise, focused planning.\n"
                "- Keep any internal analysis strictly under 3 brief points inside <think>.\n"
                "- Jump directly into complete, robust code implementation without repetitive explanation."
            )
            prefill = None
            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.25,
                top_p=0.95,
                max_thinking_tokens=120,
                prefill_assistant=prefill,
                system_directive=sys_dir,
                rationale=rationale or "Focused reasoning with fast code generation"
            )

        else:  # DEEP
            sys_dir = (
                "[EXECUTION DIRECTIVE: DEEP REASONING & ACCURACY MODE]\n"
                "- Goal: Solve complex algorithmic, architectural, or security-sensitive challenges with verified correctness.\n"
                "- Use rigorous step-by-step thinking inside <think> to verify invariants, bounds, and failure modes.\n"
                "- Deliver complete, verified code with proofs and complexity analysis."
            )
            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.55,
                top_p=0.95,
                max_thinking_tokens=None,
                prefill_assistant=None,
                system_directive=sys_dir,
                rationale=rationale or "Full cognitive reasoning for complex algorithmic depth"
            )


class LoopGuard:
    """
    Prevents coding agents from entering repetitive planning, duplicate tool execution,
    or infinite thinking loops.
    """

    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
        self.iteration_count = 0
        self.executed_tools: List[str] = []
        self.inspected_files: Set[str] = set()
        self.modified_files: Set[str] = set()

    def record_tool_call(self, tool_name: str, args_summary: str) -> bool:
        """
        Records a tool execution. Returns False if a duplicate call is detected in succession.
        """
        signature = f"{tool_name}:{args_summary}"
        self.iteration_count += 1

        if len(self.executed_tools) >= 2 and self.executed_tools[-1] == signature:
            return False  # Immediate duplicate call detected

        self.executed_tools.append(signature)
        return self.iteration_count <= self.max_iterations

    def record_file_inspect(self, path: str) -> bool:
        """
        Tracks file inspection. Returns False if inspecting the same file repeatedly without changes.
        """
        norm_path = path.lower().strip()
        if norm_path in self.inspected_files and norm_path not in self.modified_files:
            return False  # Already inspected and not yet modified
        self.inspected_files.add(norm_path)
        return True

    def record_file_modify(self, path: str):
        self.modified_files.add(path.lower().strip())

    def should_terminate(self) -> bool:
        return self.iteration_count >= self.max_iterations
