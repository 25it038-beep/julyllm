"""
HS AI SOLUTIONS â€” JULY CLIENT LOCAL INFERENCE RUNTIME
Layer: LOCAL INFERENCE (july_distribution.client.runtime)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Implements Requirement 4 & 6:
- 100% Genuine Local Inference on client hardware.
- CPU & NVIDIA CUDA auto-detection.
- Real-time token streaming.
- Safe model unloading and working-set memory reclamation.
"""

from __future__ import annotations
import gc
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, Generator

from .config import ClientConfig
from .hardware import detect_client_hardware
from .storage import ClientEphemeralStorage
from .customization import UserCustomizationManager
from .reasoning import JulyReasoningOrchestrator, OrchestratedReasoningResult
from .web_search import (
    should_trigger_web_search,
    extract_search_query,
    live_duckduckgo_search,
    format_search_context
)


class ClientInferenceRuntime:
    """Manages local llama.cpp execution on the client computer with external reasoning orchestration."""

    _instance: Optional[ClientInferenceRuntime] = None

    @classmethod
    def get_instance(cls, config: Optional[ClientConfig] = None) -> ClientInferenceRuntime:
        if cls._instance is None:
            cls._instance = cls(config=config)
        elif config is not None:
            cls._instance.config = config
        return cls._instance

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        storage: Optional[ClientEphemeralStorage] = None,
        customizer: Optional[UserCustomizationManager] = None
    ):
        self.config = config or ClientConfig.load()
        self.storage = storage or ClientEphemeralStorage()
        self.customizer = customizer or UserCustomizationManager(self.config)
        self.orchestrator = JulyReasoningOrchestrator()
        self.llm = None
        self.active_model_path: Optional[Path] = None
        self.current_model_id: str = getattr(self.config, "selected_model", "july").lower()
        if self.current_model_id == "auto":
            self.current_model_id = "july"
        self._is_loaded = False

    def switch_model(self, model_id: str, model_path: Optional[Path] = None):
        """Switches active model cleanly between july, gravity, and sree."""
        target = model_id.lower().strip()
        if target not in ("july", "gravity", "sree"):
            target = "july"

        if self._is_loaded and self.current_model_id == target and self.llm is not None:
            if model_path is None or self.active_model_path == model_path:
                return

        # Unload existing instance safely to prevent memory collision
        if self.llm is not None:
            try:
                if hasattr(self.llm, "close"):
                    self.llm.close()
            except Exception:
                pass
            del self.llm
            self.llm = None
            self._is_loaded = False
            gc.collect()
            if "torch" in sys.modules:
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
            self.storage.reclaim_os_memory()

        if model_path is None:
            from .storage import PermanentModelStorage
            perm = PermanentModelStorage()
            target_f = perm.get_model_file(target)
            if target_f.exists() and target_f.stat().st_size > 0:
                model_path = target_f
            else:
                from .cli import resolve_model_seed
                model_path = resolve_model_seed(target)

        if not model_path or not model_path.exists():
            raise FileNotFoundError(f"Model file for '{target}' not found: {model_path}")

        self.current_model_id = target
        self.load_model(model_path)

    def load_model(self, model_path: Path):
        """Loads model into active memory via llama.cpp with memory-aware dynamic layer budget."""
        if self._is_loaded and self.llm is not None:
            return

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            import llama_cpp
        except ImportError:
            raise ImportError("llama-cpp-python is required on client. Run: pip install llama-cpp-python")

        from .lifecycle import GGUFInspector, HardwareMemoryBudgeter
        try:
            meta = GGUFInspector.inspect(model_path)
            total_layers = meta.block_count
        except Exception:
            total_layers = 32

        mode = self.config.hardware_mode.lower()
        force_cpu = (mode == "cpu")

        budget = HardwareMemoryBudgeter.profile_and_budget(
            model_size_bytes=model_path.stat().st_size,
            total_layers=total_layers,
            target_context=getattr(self.config, "context_length", 4096) or 4096,
            force_cpu=force_cpu
        )

        n_gpu = budget["recommended_gpu_layers"]
        if n_gpu > 0:
            device_desc = f"CUDA GPU ({budget['gpu_name']}, {n_gpu}/{budget['total_layers']} layers offloaded, {budget['offload_strategy']})"
        else:
            device_desc = f"CPU Execution ({budget['recommended_threads']} threads, AVX2 RAM mode)"

        tag = getattr(self, "current_model_id", "july").upper()
        print(f"[{tag} RUNTIME] Initializing llama.cpp engine on: {device_desc}...")

        try:
            use_flash = bool(n_gpu > 0 and getattr(self.config, "flash_attention", True))
            self.llm = llama_cpp.Llama(
                model_path=str(model_path),
                n_ctx=4096,
                n_gpu_layers=n_gpu,
                n_threads=budget["recommended_threads"],
                n_batch=512,
                flash_attn=use_flash,
                logits_all=False,
                verbose=False
            )
            self._is_loaded = True
            self.active_model_path = model_path
            print(f"[{tag} RUNTIME] Model successfully initialized in active memory!")
        except Exception as e:
            if n_gpu > 0:
                print(f"[{tag} RUNTIME] GPU offload encountered issue ({e}). Falling back to pure CPU...")
                self.llm = llama_cpp.Llama(
                    model_path=str(model_path),
                    n_ctx=4096,
                    n_gpu_layers=0,
                    n_threads=budget["recommended_threads"],
                    n_batch=512,
                    logits_all=False,
                    verbose=False
                )
                self._is_loaded = True
                self.active_model_path = model_path
                print(f"[{tag} RUNTIME] Model loaded successfully on pure CPU fallback.")
            else:
                raise RuntimeError(f"Failed to load model: {e}")

    def generate_stream(
        self,
        prompt: str,
        session_id: str = "default",
        max_tokens: Optional[int] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Generator[str, None, None]:
        """Streams output tokens formatted with user customizations."""
        if not self._is_loaded or self.llm is None:
            raise RuntimeError("Model is not loaded. Please execute 'july load' first.")

        # Enforce authentication & rate limit protection
        try:
            from .clerk_auth import ClerkAuthManager
            from .rate_limiter import ClientRateLimiter, RateLimitExceededError
            clerk_mgr = ClerkAuthManager()
            if not clerk_mgr.is_authenticated():
                from .auth import ClientAuthManager
                if not ClientAuthManager().is_authenticated():
                    raise PermissionError("Authentication required to execute model inference. Please run 'july login'.")
            session = clerk_mgr.get_session() or {}
            tier = session.get("tier", "standard")
            ClientRateLimiter.get_instance().enforce_rate_limit(tier=tier, estimated_tokens=len(prompt.split()) * 2)
        except (PermissionError, RateLimitExceededError):
            raise
        except Exception as e:
            # Re-raise explicit permission or rate limit exceptions
            if "Authentication required" in str(e) or "Rate limit" in str(e):
                raise

        # In AUTO mode, dynamically evaluate and route task to July or Gravity
        routing_note = ""
        if getattr(self.config, "selected_model", "july").lower() == "auto":
            try:
                from hs_ecosystem.core.model_manager import UniversalModelManager
                from hs_ecosystem.core.model_router import IntelligentModelRouter
                dummy_mgr = UniversalModelManager()
                dummy_mgr.active_model_id = self.current_model_id
                router = IntelligentModelRouter(dummy_mgr)
                decision = router.route_prompt(prompt, requested_mode="AUTO")
                if decision.selected_model != self.current_model_id:
                    self.switch_model(decision.selected_model)
                routing_note = f"\n \033[93m⚡ [AUTO ROUTER]\033[0m Task routed to: \033[1m{decision.selected_model.upper()} LLM\033[0m ({decision.rationale})\n\n"
            except Exception:
                pass

        if routing_note:
            sys.stdout.write(routing_note)
            sys.stdout.flush()

        # Check for dynamic user name introduction (e.g. "My name is Priya", "Call me Rahul")
        try:
            from .context_provider import RuntimeContextProvider
            name_intro = re.search(r"(?i)\b(?:my name is|call me|myself|i am|i\'m)\s+([A-Z][a-zA-Z]+)\b", prompt)
            if name_intro:
                cand_name = name_intro.group(1).capitalize()
                common_non_names = {"sorry", "ready", "fine", "coding", "tired", "back", "done", "happy", "here", "just", "trying", "going", "asking", "wondering", "a", "an", "the", "working", "sree", "july", "gravity"}
                if cand_name.lower() not in common_non_names:
                    RuntimeContextProvider.set_user_override(name=cand_name)
        except Exception:
            pass

        history = self.customizer.get_session_history(session_id, limit=4)
        is_first_turn = (len(history) == 0)
        sys_prompt = self.customizer.get_effective_system_prompt(self.current_model_id, is_first_turn=is_first_turn)
        custom_kn = self.customizer.retrieve_custom_knowledge(prompt)

        # Autonomous Real-Time Web Search Grounding
        web_context = ""
        if getattr(self.config, "enable_web_search", True) and should_trigger_web_search(prompt, history=history):
            search_query = extract_search_query(prompt, history=history)
            try:
                sys.stdout.write(f"\n \033[93m🔍 [HS AI SEARCH]\033[0m Querying live web sources for: '\033[1m{search_query}\033[0m'...\n")
                sys.stdout.flush()
                results = live_duckduckgo_search(search_query)
                if results:
                    web_context = format_search_context(search_query, results)
                    sys.stdout.write(f" \033[92m[✓]\033[0m Grounded with {len(results)} live source snippets from web.\n\n")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f" \033[90m[*] Live web search returned 0 matches; relying on neural weights.\033[0m\n\n")
                    sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(f" \033[90m[*] Web search unavailable ({e}); relying on neural weights.\033[0m\n\n")
                sys.stdout.flush()

        # Adaptive Reasoning & Coding Speed Optimization (Requirement 3 & 4)
        from .adaptive_reasoning import AdaptiveReasoningEngine, ThinkingLevel
        user_think_override = getattr(self.config, "thinking_level", None) or os.getenv("JULY_THINKING_LEVEL")
        if user_think_override == "auto":
            user_think_override = None
        active_level, level_rationale = AdaptiveReasoningEngine.classify_task(prompt, user_override=user_think_override)
        steering = AdaptiveReasoningEngine.get_steering(
            self.current_model_id, active_level, level_rationale, is_first_turn=is_first_turn
        )

        # Reasoning Orchestration Invariants Pre-pass (Skip in INSTANT and CONVERSATIONAL modes)
        if active_level not in (ThinkingLevel.INSTANT, ThinkingLevel.CONVERSATIONAL):
            guidance = self.orchestrator.prepare_reasoning_guidance(prompt)
        else:
            guidance = None

        # Build chat format
        is_sree = "sree" in getattr(self, "current_model_id", "july").lower()
        if is_sree:
            # Sree uses ChatML format and native <think> tags for dense reasoning
            formatted = f"<|im_start|>system\n{sys_prompt}\n\n{steering.system_directive}"
            if custom_kn:
                formatted += f"\n\nReference Knowledge:\n{custom_kn}"
            if guidance:
                formatted += f"\n\n[HS AI COGNITIVE REASONING INVARIANTS]:\n{guidance}\nFollow these formal invariants strictly."
            if web_context:
                formatted += (
                    f"\n\n{web_context}\n\n"
                    f"[REAL-TIME WEB GROUNDING CONTEXT]:\n"
                    f"- The verified live facts above were retrieved from the real-time internet.\n"
                    f"- Use them to ground and inform your response accurately when answering questions about current events, people, prices, or live facts."
                )
            formatted += "<|im_end|>\n"

            for msg in history:
                m_role = msg.get("role", "user")
                m_content = msg.get("content", "").strip()
                # Clean thinking scratchpads from previous turns to prevent topic inertia
                if m_role == "assistant":
                    m_content = re.sub(r"(?s)<think>.*?</think>", "", m_content).strip()
                formatted += f"<|im_start|>{m_role}\n{m_content}<|im_end|>\n"

            formatted += f"<|im_start|>user\n{prompt}<|im_end|>\n"
            formatted += "<|im_start|>assistant\n"
            if steering.prefill_assistant:
                formatted += steering.prefill_assistant
            model_stops = ["<|im_end|>", "<|im_start|>", "<|endoftext|>"]
        else:
            formatted = f"<|start_header_id|>system<|end_header_id|>\n\n{sys_prompt}\n\n{steering.system_directive}"
            if custom_kn:
                formatted += f"\n\nReference Knowledge:\n{custom_kn}"
            if guidance:
                formatted += f"\n\n[HS AI REASONING ORCHESTRATOR INVARIANTS]:\n{guidance}\nFollow these formal invariants strictly."
            if web_context:
                formatted += (
                    f"\n\n{web_context}\n\n"
                    f"[REAL-TIME WEB GROUNDING CONTEXT]:\n"
                    f"- The verified live facts above were retrieved from the real-time internet.\n"
                    f"- Use them to ground and inform your response accurately when answering questions about current events, people, prices, or live facts."
                )
            formatted += "<|eot_id|>"

            for msg in history:
                m_role = msg.get("role", "user")
                m_content = msg.get("content", "").strip()
                if m_role == "assistant":
                    m_content = re.sub(r"(?s)<think>.*?</think>", "", m_content).strip()
                formatted += f"<|start_header_id|>{m_role}<|end_header_id|>\n\n{m_content}<|eot_id|>"

            formatted += f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|>"
            formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
            model_stops = ["<|eot_id|>", "<|end_of_text|>", "<|endoftext|>"]

        # Unlimited tokens: if requested_max <= 0 or None, llama.cpp generates until EOS
        requested_max = max_tokens if max_tokens is not None else self.config.max_tokens
        tokens_to_gen = None if (requested_max is None or requested_max <= 0) else requested_max

        eff_temp = steering.temperature if getattr(self.config, "adaptive_temperature", True) else self.config.temperature
        eff_top_p = steering.top_p if getattr(self.config, "adaptive_temperature", True) else self.config.top_p

        stream = self.llm(
            formatted,
            max_tokens=tokens_to_gen,
            temperature=eff_temp,
            top_p=eff_top_p,
            stop=model_stops,
            stream=True
        )

        full_response = []
        for chunk in stream:
            if cancel_event and cancel_event.is_set():
                break
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("text", "")
                if delta:
                    full_response.append(delta)
                    yield delta

        raw_text = "".join(full_response)

        # Post-stream verification & validation check (Skip in INSTANT and CONVERSATIONAL modes for zero-overhead speed)
        if active_level in (ThinkingLevel.INSTANT, ThinkingLevel.CONVERSATIONAL):
            logged_text = raw_text
        else:
            verified_res = self.orchestrator.validate_and_synthesize_response(prompt, raw_text)
            if verified_res.corrections_applied and verified_res.verified_final_response != raw_text:
                # Yield post-validation synthesis note
                yield f"\n\n\033[93m[HS AI REASONING VERIFIER: Applied {len(verified_res.corrections_applied)} verified formal corrections]:\033[0m\n{verified_res.verified_final_response}"
                logged_text = verified_res.verified_final_response
            else:
                logged_text = raw_text

        # Record to history with model attribution
        self.customizer.log_message(session_id, "user", prompt, model=self.current_model_id)
        self.customizer.log_message(session_id, "assistant", logged_text, model=self.current_model_id)

    def generate_verified(
        self,
        prompt: str,
        session_id: str = "default",
        max_tokens: Optional[int] = None
    ) -> OrchestratedReasoningResult:
        """
        Executes foundation model generation through the 9-stage Reasoning Orchestrator.
        Returns complete verified result with CAS, logic, code, and uncertainty artifacts.
        """
        t0 = time.time()
        tokens = list(self.generate_stream(prompt, session_id=session_id, max_tokens=max_tokens))
        elapsed = time.time() - t0
        raw_text = "".join(tokens)
        return self.orchestrator.validate_and_synthesize_response(prompt, raw_text, elapsed=elapsed)

    def unload(self, wipe_storage: bool = False):
        """Safe model unloading and memory reclamation without destroying permanent disk files."""
        if self.llm is not None:
            try:
                if hasattr(self.llm, "close"):
                    self.llm.close()
            except Exception:
                pass
            del self.llm
            self.llm = None

        self._is_loaded = False
        gc.collect()

        if "torch" in sys.modules:
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

        if wipe_storage and self.active_model_path:
            self.storage.wipe_and_unlink(self.active_model_path, allow_permanent_deletion=True)
            self.active_model_path = None
        elif self.active_model_path:
            self.storage.wipe_and_unlink(self.active_model_path, allow_permanent_deletion=False)

        self.storage.reclaim_os_memory()
        tag = getattr(self, "current_model_id", "july").upper()
        print(f"[{tag} RUNTIME] Model ({self.current_model_id}) safely unloaded from active RAM/VRAM.")

    def is_loaded(self) -> bool:
        return self._is_loaded

