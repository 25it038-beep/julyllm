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

        # 2. Check for DEEP complexity signals (Algorithms, formal proofs, concurrency, red-black trees, dijkstra)
        for pat in cls.DEEP_KEYWORDS:
            if re.search(pat, p_lower):
                return ThinkingLevel.DEEP, f"Detected deep algorithmic / formal constraint: {pat}"

        # 3. Check for BALANCED multi-component signals (Full-stack, multi-file, architecture)
        for pat in cls.BALANCED_KEYWORDS:
            if re.search(pat, p_lower):
                return ThinkingLevel.BALANCED, f"Detected multi-file / architectural scope: {pat}"

        # 4. Check for direct code tasks
        for pat in cls.INSTANT_KEYWORDS:
            if re.search(pat, p_lower):
                return ThinkingLevel.INSTANT, "Detected straightforward coding implementation task"

        # 5. Distinguish general CODING tasks from CONVERSATIONAL / INFORMATIONAL inquiries
        coding_signals = [
            r"\b(code|coding|script|scripting|program|programming|function|class|method|module|component|app|api|endpoint|algorithm|data\s+structure)\b",
            r"\b(write|create|implement|build|develop|generate|draft)\b",
            r"\b(fix|debug|refactor|optimize|compile|run|benchmark|traceback|syntax\s+error|bug|issue|exception)\b",
            r"\b(python|javascript|typescript|c\+\+|rust|golang|java|html|css|sql|bash|powershell|react|vue|node)\b",
            r"\b(def\s+|class\s+|import\s+|const\s+|let\s+|function\s+|<script|<div)\b",
        ]
        is_coding_task = any(re.search(pat, p_lower) for pat in coding_signals)

        if is_coding_task:
            return ThinkingLevel.INSTANT, "Concise coding scope — defaulted to INSTANT for maximum speed"

        # Non-coding queries (general knowledge, conversation, identity, explanations) -> CONVERSATIONAL
        return ThinkingLevel.CONVERSATIONAL, "Conversational / general knowledge / identity inquiry"

    @classmethod
    def generate_dynamic_thought(
        cls,
        prompt: str,
        level: ThinkingLevel,
        user_name: str = "Harshan",
        opp_persona: str = "female"
    ) -> str:
        """
        Synthesizes an ultra-concise, context-aware 1-line thought.
        Prefilling this thought inside a CLOSED <think>...</think> block allows
        the UI to render the thinking process cleanly in ~0.05s while instructing
        llama.cpp to immediately start generating the answer with zero hidden token lag!
        """
        p_clean = (prompt or "").strip()
        p_lower = p_clean.lower()

        if level == ThinkingLevel.CONVERSATIONAL:
            if any(w in p_lower for w in ["who is", "who created", "who made", "founder"]):
                return "Founder & Creator query: State verified facts crediting creator Harshan Seliyan and HS AI Solutions."
            elif any(w in p_lower for w in ["time", "clock", "date"]):
                return f"Temporal inquiry: Retrieve verified local time/date and communicate in {opp_persona} tone."
            elif any(w in p_lower for w in ["location", "where am i", "city", "country"]):
                return "Geolocation inquiry: State accurate local coordinate and city context."
            elif any(w in p_lower for w in ["who am i", "my name"]):
                return f"User identity: Greet {user_name} respectfully with appropriate {opp_persona} persona."
            else:
                words = p_clean.split()
                summary = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
                return f"Conversational query: '{summary}' -> Formulate direct, accurate, and articulate response."

        elif level == ThinkingLevel.INSTANT:
            words = p_clean.split()
            summary = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
            return f"Instant execution: '{summary}' -> Deliver clean, production-ready code directly."

        elif level == ThinkingLevel.BALANCED:
            return "Multi-component task -> Structure solution cleanly with verified interfaces."

        else:  # DEEP
            return "Algorithmic analysis -> Verify invariants, edge cases, and computational bounds."

    @classmethod
    def get_steering(
        cls,
        model_id: str,
        level: ThinkingLevel,
        rationale: str = "",
        is_first_turn: bool = True,
        prompt: str = ""
    ) -> AdaptiveSteeringConfig:
        """
        Produces optimal model steering, prefill tokens, and inference hyper-parameters.
        Prefills a closed, dynamic 1-line thought for reasoning models so llama.cpp
        begins generating the actual answer immediately without hidden token delay.
        """
        is_reasoning_model = any(x in (model_id or "").lower() for x in ("sree", "gravity", "qwen"))

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
            greeting_pref = t.get("greeting", "Hello")
        except Exception:
            user_name = "Harshan"
            opp_persona = "female"
            tone_summary = "Feminine, graceful, charming, warm, and deeply respectful"
            time_str = "Now"
            date_str = "Today"
            loc_str = "Chennai, Tamil Nadu, India"
            greeting_pref = "Hello"

        thought = cls.generate_dynamic_thought(prompt, level, user_name=user_name, opp_persona=opp_persona)
        # SREE & Gravity Dynamic Reasoning: Prompt with open <think> so models formulate real thoughts dynamically
        prefill_assistant = "<think>\n" if is_reasoning_model else None

        mid_lower = (model_id or "").lower()
        if "gravity" in mid_lower:
            active_model_name = "GRAVITY"
        elif "sree" in mid_lower:
            active_model_name = "SREE"
        elif "mini-omni" in mid_lower or "omni" in mid_lower:
            active_model_name = "MINI-OMNI"
        else:
            active_model_name = "JULY"

        if level == ThinkingLevel.CONVERSATIONAL:
            if is_first_turn:
                sys_dir = (
                    f"[DIRECTIVE: First turn: You are {active_model_name} LLM. Greet {user_name} warmly ('{greeting_pref} {user_name}!') in your {opp_persona} voice ({tone_summary}). Note: Your model name is strictly {active_model_name}. {user_name} is your male creator. State verified time/date/location if asked, check any provided web search context and cite sources, then answer prompt directly. Do NOT output unrequested coding solutions.]"
                )
            else:
                sys_dir = (
                    f"[DIRECTIVE: Multi-turn continuation: NO RE-GREETINGS. You are {active_model_name} LLM. Jump directly into answering the prompt in your {opp_persona} voice. Note: Your model name is strictly {active_model_name}. {user_name} is your male creator. Switch topics cleanly. Check any provided web search context and cite sources. Do NOT output unrequested coding solutions.]"
                )

            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.7,
                top_p=0.9,
                max_thinking_tokens=40,
                prefill_assistant=prefill_assistant,
                system_directive=sys_dir,
                rationale=rationale or ("First-turn greeting with opposite-gender tone" if is_first_turn else "Multi-turn direct response without re-greeting")
            )

        elif level == ThinkingLevel.INSTANT:
            sys_dir = (
                "[EXECUTION DIRECTIVE: INSTANT CODE-FIRST MODE]\n"
                "- Goal: Exercise full freedom of reasoning inside <think>...</think>, then produce correct, functional, production-quality code.\n"
                "- Produce the required code blocks, modules, or fixes directly.\n"
                "- Follow all system instructions and check any provided web search context."
            )
            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.15,
                top_p=0.9,
                max_thinking_tokens=35,
                prefill_assistant=prefill_assistant,
                system_directive=sys_dir,
                rationale=rationale or "Ultra-fast code delivery"
            )

        elif level == ThinkingLevel.BALANCED:
            sys_dir = (
                "[EXECUTION DIRECTIVE: BALANCED IMPLEMENTATION MODE]\n"
                "- Goal: Deliberate freely inside <think>...</think>, then execute clean and robust implementation.\n"
                "- Follow all system instructions and check any provided web search context."
            )
            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.25,
                top_p=0.9,
                max_thinking_tokens=50,
                prefill_assistant=prefill_assistant,
                system_directive=sys_dir,
                rationale=rationale or "Focused reasoning with fast generation"
            )

        else:  # DEEP
            sys_dir = (
                "[EXECUTION DIRECTIVE: DEEP ACCURACY & COGNITIVE REASONING MODE]\n"
                "- Goal: Exercise full freedom of deep reasoning, formal logic, and verification inside <think>...</think>.\n"
                "- Deliver complete, verified code or answers with proofs and complexity analysis.\n"
                "- Follow all system instructions and check any provided web search context."
            )
            return AdaptiveSteeringConfig(
                level=level,
                temperature=0.5,
                top_p=0.9,
                max_thinking_tokens=80,
                prefill_assistant=prefill_assistant,
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


class StreamLoopDetector:
    """
    Monitors live token streams to detect and break degenerate repetitive loops.
    Detects repeated sentences, repeated markdown blocks, and cyclic n-grams.
    """

    def __init__(self, max_history_chars: int = 500, repeat_threshold: int = 3):
        self.history = ""
        self.max_history_chars = max_history_chars
        self.repeat_threshold = repeat_threshold

    def check(self, delta: str) -> bool:
        if not delta:
            return False
        self.history += delta
        if len(self.history) > self.max_history_chars:
            self.history = self.history[-self.max_history_chars:]

        # 1. Check for identical non-trivial lines repeated >= repeat_threshold
        lines = [line.strip() for line in self.history.splitlines() if len(line.strip()) >= 12]
        if len(lines) >= self.repeat_threshold:
            if sum(1 for line in lines if line == lines[-1]) >= self.repeat_threshold:
                return True

        # 2. Check for multi-line or block-level cyclic repeats (length 15 to 140 chars)
        buf_len = len(self.history)
        for plen in range(15, min(140, buf_len // self.repeat_threshold + 1)):
            candidate = self.history[-plen:]
            repeats = 1
            pos = buf_len - plen
            while pos >= plen:
                if self.history[pos - plen:pos] == candidate:
                    repeats += 1
                    pos -= plen
                    if repeats >= self.repeat_threshold:
                        return True
                else:
                    break

        return False

    def reset(self):
        self.history = ""

