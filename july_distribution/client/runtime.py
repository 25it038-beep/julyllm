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
        """Switches active model cleanly between july and gravity."""
        target = model_id.lower().strip()
        if target not in ("july", "gravity"):
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

        if model_path is None:
            from .cli import resolve_model_seed
            model_path = resolve_model_seed(target)

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

        print(f"[JULY RUNTIME] Initializing llama.cpp engine on: {device_desc}...")

        try:
            self.llm = llama_cpp.Llama(
                model_path=str(model_path),
                n_ctx=4096,
                n_gpu_layers=n_gpu,
                n_threads=budget["recommended_threads"],
                n_batch=512,
                logits_all=False,
                verbose=False
            )
            self._is_loaded = True
            self.active_model_path = model_path
            print(f"[JULY RUNTIME] Model successfully initialized in active memory!")
        except Exception as e:
            if n_gpu > 0:
                print(f"[JULY RUNTIME] GPU offload encountered issue ({e}). Falling back to pure CPU...")
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
                print(f"[JULY RUNTIME] Model loaded successfully on pure CPU fallback.")
            else:
                raise RuntimeError(f"Failed to load model: {e}")

    def generate_stream(
        self,
        prompt: str,
        session_id: str = "default",
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:
        """Streams output tokens formatted with user customizations."""
        if not self._is_loaded or self.llm is None:
            raise RuntimeError("Model is not loaded. Please execute 'july load' first.")

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

        if self.current_model_id == "gravity":
            sys_prompt = (
                "You are GRAVITY LLM, an advanced mathematical and reasoning neural model created by Harshan Seliyan "
                "and developed by HS AI Solutions. Deliver rigorous, exact, and mathematically verified answers."
            )
        else:
            sys_prompt = self.customizer.get_effective_system_prompt()
        history = self.customizer.get_session_history(session_id, limit=4)
        custom_kn = self.customizer.retrieve_custom_knowledge(prompt)

        # Autonomous Real-Time Web Search Grounding
        web_context = ""
        if getattr(self.config, "enable_web_search", True) and should_trigger_web_search(prompt):
            search_query = extract_search_query(prompt)
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

        # Reasoning Orchestration Invariants Pre-pass
        guidance = self.orchestrator.prepare_reasoning_guidance(prompt)

        # Build chat format
        formatted = f"<|start_header_id|>system<|end_header_id|>\n\n{sys_prompt}"
        if custom_kn:
            formatted += f"\n\nReference Knowledge:\n{custom_kn}"
        if guidance:
            formatted += f"\n\n[HS AI REASONING ORCHESTRATOR INVARIANTS]:\n{guidance}\nFollow these formal invariants strictly."
        if web_context:
            formatted += (
                f"\n\n{web_context}\n\n"
                f"CRITICAL REAL-TIME GROUNDING DIRECTIVE:\n"
                f"- You have access to verified real-time live internet facts above.\n"
                f"- You MUST prioritize and base your response on these real-time search facts to provide accurate, up-to-date answers.\n"
                f"- Override any older pretraining memory with the provided live web search data."
            )
        formatted += "<|eot_id|>"

        for msg in history:
            formatted += f"<|start_header_id|>{msg['role']}<|end_header_id|>\n\n{msg['content']}<|eot_id|>"

        formatted += "<|start_header_id|>user<|end_header_id|>\n\n"
        if web_context:
            formatted += f"[Real-Time Live Web Search Information:\n{web_context}]\n\nQuestion: {prompt}<|eot_id|>"
        else:
            formatted += f"{prompt}<|eot_id|>"
        formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"

        # Unlimited tokens: if requested_max <= 0 or None, llama.cpp generates until EOS (<|eot_id|>)
        requested_max = max_tokens if max_tokens is not None else self.config.max_tokens
        tokens_to_gen = None if (requested_max is None or requested_max <= 0) else requested_max

        stream = self.llm(
            formatted,
            max_tokens=tokens_to_gen,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            stop=["<|eot_id|>", "<|end_of_text|>", "<|endoftext|>"],
            stream=True
        )

        full_response = []
        for chunk in stream:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("text", "")
                if delta:
                    full_response.append(delta)
                    yield delta

        raw_text = "".join(full_response)

        # Post-stream verification & validation check
        verified_res = self.orchestrator.validate_and_synthesize_response(prompt, raw_text)
        if verified_res.corrections_applied and verified_res.verified_final_response != raw_text:
            # Yield post-validation synthesis note
            yield f"\n\n\033[93m[HS AI REASONING VERIFIER: Applied {len(verified_res.corrections_applied)} verified formal corrections]:\033[0m\n{verified_res.verified_final_response}"
            logged_text = verified_res.verified_final_response
        else:
            logged_text = raw_text

        # Record to history
        self.customizer.log_message(session_id, "user", prompt)
        self.customizer.log_message(session_id, "assistant", logged_text)

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

    def unload(self, wipe_storage: bool = True):
        """Safe model unloading and memory reclamation."""
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

        if wipe_storage and self.active_model_path:
            self.storage.wipe_and_unlink(self.active_model_path)
            self.active_model_path = None

        self.storage.reclaim_os_memory()
        print("[JULY RUNTIME] Model safely unloaded. Ephemeral memory reclaimed.")

    def is_loaded(self) -> bool:
        return self._is_loaded

