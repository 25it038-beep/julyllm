"""
HS AI SOLUTIONS — JULY CLIENT LOCAL INFERENCE RUNTIME
Layer: LOCAL INFERENCE (july_distribution.client.runtime)
Founder & Chief Architect: Harshan Seliyan
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


class ClientInferenceRuntime:
    """Manages local llama.cpp execution on the client computer."""

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        storage: Optional[ClientEphemeralStorage] = None,
        customizer: Optional[UserCustomizationManager] = None
    ):
        self.config = config or ClientConfig.load()
        self.storage = storage or ClientEphemeralStorage()
        self.customizer = customizer or UserCustomizationManager(self.config)
        self.llm = None
        self.active_model_path: Optional[Path] = None
        self._is_loaded = False

    def load_model(self, model_path: Path):
        """Loads model into active memory via llama.cpp."""
        if self._is_loaded and self.llm is not None:
            return

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            import llama_cpp
        except ImportError:
            raise ImportError("llama-cpp-python is required on client. Run: pip install llama-cpp-python")

        hw = detect_client_hardware()
        mode = self.config.hardware_mode.lower()

        if mode == "cuda" or (mode == "auto" and hw["gpu_available"]):
            n_gpu = hw["recommended_gpu_layers"]
            device_desc = f"CUDA GPU ({hw['gpu_name']}, {n_gpu} layers offloaded)"
        else:
            n_gpu = 0
            device_desc = f"CPU Execution ({hw['recommended_threads']} threads)"

        print(f"[JULY RUNTIME] Initializing llama.cpp engine on: {device_desc}...")

        try:
            self.llm = llama_cpp.Llama(
                model_path=str(model_path),
                n_ctx=self.config.context_length,
                n_gpu_layers=n_gpu,
                n_threads=hw["recommended_threads"],
                n_batch=self.config.n_batch,
                logits_all=False,
                verbose=False
            )
            self._is_loaded = True
            self.active_model_path = model_path
            print(f"[JULY RUNTIME] Model successfully initialized in RAM!")
        except Exception as e:
            if n_gpu > 0:
                print(f"[JULY RUNTIME] GPU load encountered ({e}). Falling back to pure CPU...")
                self.llm = llama_cpp.Llama(
                    model_path=str(model_path),
                    n_ctx=self.config.context_length,
                    n_gpu_layers=0,
                    n_threads=hw["recommended_threads"],
                    n_batch=self.config.n_batch,
                    logits_all=False,
                    verbose=False
                )
                self._is_loaded = True
                self.active_model_path = model_path
                print(f"[JULY RUNTIME] Model loaded successfully on CPU fallback.")
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

        sys_prompt = self.customizer.get_effective_system_prompt()
        history = self.customizer.get_session_history(session_id, limit=4)
        custom_kn = self.customizer.retrieve_custom_knowledge(prompt)

        # Build chat format
        formatted = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{sys_prompt}"
        if custom_kn:
            formatted += f"\n\nReference Knowledge:\n{custom_kn}"
        formatted += "<|eot_id|>"

        for msg in history:
            formatted += f"<|start_header_id|>{msg['role']}<|end_header_id|>\n\n{msg['content']}<|eot_id|>"

        formatted += f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|>"
        formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"

        tokens_to_gen = max_tokens or self.config.max_tokens

        stream = self.llm(
            formatted,
            max_tokens=tokens_to_gen,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
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

        # Record to history
        self.customizer.log_message(session_id, "user", prompt)
        self.customizer.log_message(session_id, "assistant", "".join(full_response))

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
