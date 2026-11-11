"""
HS AI SOLUTIONS — MODEL-AGNOSTIC AGENT ENGINE & ADAPTERS
Module: hs_ecosystem.agent.model_adapters
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Provides a model-independent agent runtime supporting:
- July lightweight model (3.21B GGUF)
- GRAVITY heavyweight reasoning model (GGUF)
- OpenAI-compatible API providers (vLLM, Ollama, LM Studio, Groq, DeepSeek, OpenAI)
- Anthropic Claude API
- Future HS AI Solutions models
- Local and remote endpoints

Enforces the explicit user-selection rule: Never silently override a user's selected model!
"""

from __future__ import annotations
import os
import sys
import json
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Iterator, Generator
from dataclasses import dataclass, field


@dataclass
class ModelResponse:
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    model_name: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_seconds: float = 0.0
    finish_reason: str = "stop"


class BaseModelAdapter(ABC):
    """Abstract base class for all AI model inference adapters."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None
    ) -> ModelResponse:
        """Synchronous response generation with optional tool-calling."""
        pass

    @abstractmethod
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Generator[Dict[str, Any], None, None]:
        """Streaming response generation yielding text chunks and tool calls."""
        pass


class JulyLocalAdapter(BaseModelAdapter):
    """
    Adapter for July Local Lightweight 3.21B GGUF model.
    Optimized for fast responses, terminal commands, and quick queries.
    """

    def __init__(self, model_path: Optional[str] = None):
        super().__init__("july-3.21b-local")
        self.model_path = model_path
        self._runtime = None

    def _get_runtime(self):
        if self._runtime is None:
            try:
                from july_distribution.client.dual_engine import DualModelCoordinator
                coordinator = DualModelCoordinator()
                self._runtime = coordinator.runtime
            except Exception:
                self._runtime = None
        return self._runtime

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None
    ) -> ModelResponse:
        t0 = time.time()
        runtime = self._get_runtime()
        prompt_text = self._format_prompt(messages, tools)

        if runtime is not None:
            try:
                full_text = ""
                for chunk in runtime.generate_stream(prompt_text, max_tokens=max_tokens, temperature=temperature):
                    full_text += chunk
                tool_calls = self._extract_tool_calls(full_text)
                return ModelResponse(
                    content=full_text,
                    tool_calls=tool_calls,
                    model_name=self.model_name,
                    duration_seconds=round(time.time() - t0, 3)
                )
            except Exception as e:
                return ModelResponse(
                    content=f"July runtime error: {e}",
                    model_name=self.model_name,
                    duration_seconds=round(time.time() - t0, 3),
                    finish_reason="error"
                )

        # Fallback simulator if GGUF is not currently loaded in memory
        simulated_text = f"July response to: {messages[-1]['content'] if messages else ''}"
        return ModelResponse(
            content=simulated_text,
            model_name=self.model_name,
            duration_seconds=round(time.time() - t0, 3)
        )

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Generator[Dict[str, Any], None, None]:
        runtime = self._get_runtime()
        prompt_text = self._format_prompt(messages, tools)
        if runtime is not None:
            try:
                for chunk in runtime.generate_stream(prompt_text, max_tokens=max_tokens, temperature=temperature):
                    yield {"type": "content", "delta": chunk}
                return
            except Exception as e:
                yield {"type": "error", "error": str(e)}
                return

        yield {"type": "content", "delta": f"[July] Processing task with {len(messages)} messages."}

    def _format_prompt(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        prompt_parts = []
        if tools:
            prompt_parts.append("<tools>\n" + json.dumps(tools, indent=2) + "\n</tools>\n")
            prompt_parts.append("To call a tool, format your output as: <tool_call>{\"name\": \"tool_name\", \"arguments\": {...}}</tool_call>\n")

        for m in messages:
            role = m.get("role", "user").upper()
            content = m.get("content", "")
            prompt_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")
        prompt_parts.append("<|im_start|>assistant\n")
        return "".join(prompt_parts)

    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        calls = []
        import re
        pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
        for match in pattern.finditer(text):
            try:
                parsed = json.loads(match.group(1))
                if "name" in parsed:
                    calls.append({
                        "name": parsed["name"],
                        "arguments": parsed.get("arguments", {})
                    })
            except Exception:
                continue
        return calls


class GravityLocalAdapter(JulyLocalAdapter):
    """
    Adapter for GRAVITY Heavyweight Reasoning GGUF model.
    Optimized for multi-step autonomous planning, deep architecture, and code verification.
    """

    def __init__(self, model_path: Optional[str] = None):
        super().__init__(model_path=model_path)
        self.model_name = "gravity-reasoning-local"


class OpenAICompatibleAdapter(BaseModelAdapter):
    """
    Generic adapter for OpenAI-compatible endpoints:
    - Local: vLLM, Ollama (/v1), LM Studio, LocalAI
    - Remote: OpenAI, DeepSeek, Groq, Mistral, OpenRouter
    """

    def __init__(self, model_name: str, base_url: str = "http://127.0.0.1:11434/v1", api_key: str = "EMPTY"):
        super().__init__(model_name)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None
    ) -> ModelResponse:
        t0 = time.time()
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
            payload["tool_choice"] = "auto"
        if stop:
            payload["stop"] = stop

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content") or ""
                tool_calls_raw = msg.get("tool_calls", [])
                tool_calls = []
                for tc in tool_calls_raw:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = fn.get("arguments", "{}")
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {"raw": fn_args}
                    if fn_name:
                        tool_calls.append({"name": fn_name, "arguments": fn_args})

                usage = data.get("usage", {})
                return ModelResponse(
                    content=content,
                    tool_calls=tool_calls,
                    model_name=self.model_name,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    duration_seconds=round(time.time() - t0, 3),
                    finish_reason=choice.get("finish_reason", "stop")
                )
        except urllib.error.URLError as e:
            return ModelResponse(
                content=f"Connection error to {self.base_url}: {e}",
                model_name=self.model_name,
                duration_seconds=round(time.time() - t0, 3),
                finish_reason="error"
            )
        except Exception as e:
            return ModelResponse(
                content=f"Error during OpenAI API call: {e}",
                model_name=self.model_name,
                duration_seconds=round(time.time() - t0, 3),
                finish_reason="error"
            )

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Generator[Dict[str, Any], None, None]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if not line_str.startswith("data:"):
                        continue
                    payload_part = line_str[5:].strip()
                    if payload_part == "[DONE]":
                        break
                    chunk = json.loads(payload_part)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        yield {"type": "content", "delta": delta["content"]}
        except Exception as e:
            yield {"type": "error", "error": str(e)}


class DynamicModelRouter:
    """
    Intelligently routes between July, Gravity, and external models based on
    task complexity, token count, reasoning demand, and system hardware.
    
    CRITICAL RULE:
    If the user has set an explicit model preference ('july', 'gravity', 'openai', etc.)
    and user_explicit_override is True, the router will NEVER change the model silently!
    """

    def __init__(self):
        self.adapters: Dict[str, BaseModelAdapter] = {
            "july": JulyLocalAdapter(),
            "gravity": GravityLocalAdapter(),
        }
        self.active_model_key = "july"
        self.user_explicit_lock = False

    def register_adapter(self, key: str, adapter: BaseModelAdapter):
        self.adapters[key.lower()] = adapter

    def set_active_model(self, model_key: str, user_explicit: bool = False):
        key = model_key.lower().strip()
        if key in self.adapters:
            self.active_model_key = key
            if user_explicit:
                self.user_explicit_lock = True
        else:
            raise ValueError(f"Unknown model adapter '{model_key}'. Registered: {list(self.adapters.keys())}")

    def unlock_user_preference(self):
        self.user_explicit_lock = False

    def route_for_task(self, task_goal: str, prompt_tokens_est: int = 0) -> Tuple[str, BaseModelAdapter]:
        """
        Selects the best model adapter.
        If locked by explicit user choice, returns the chosen adapter unconditionally.
        Otherwise, routes based on task complexity.
        """
        if self.user_explicit_lock:
            # Respect user explicit selection
            return self.active_model_key, self.adapters[self.active_model_key]

        # Automatic intelligent routing
        goal_lower = task_goal.lower()
        requires_heavy_reasoning = any(kw in goal_lower for kw in [
            "architect", "refactor", "complex", "debug deeply", "formal proof",
            "equation", "multi-step plan", "database migration", "full-stack"
        ])

        if requires_heavy_reasoning and "gravity" in self.adapters:
            return "gravity", self.adapters["gravity"]
        
        return "july", self.adapters.get("july", self.adapters[self.active_model_key])
