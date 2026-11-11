"""
HS AI SOLUTIONS — DUAL MODEL ORCHESTRATION ENGINE
Layer: DUAL-MODEL COORDINATOR (july_distribution.client.dual_engine)
Organization: HS AI Solutions | Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM & GRAVITY LLM

Implements Requirements 1, 3, 4, 6, 7 & 8:
- Independent model selection for July and Gravity.
- Non-blocking background downloader when a model is not downloaded.
- Fallback routing to currently operational model during background acquisition.
- Automatic activation of target model once verified & initialized.
- Memory-aware execution (single active model in RAM/CUDA to prevent exhaustion).
- Never deletes or overwrites files.
- Thread-safe coordination and state persistence.
"""

from __future__ import annotations
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from .config import ClientConfig
from .auth import ClientAuthManager
from .storage import PermanentModelStorage
from .state_manager import DualModelStateManager, ModelStatus
from .downloader import ClientModelDownloader
from .parallel_downloader import DirectR2ParallelDownloader
from .runtime import ClientInferenceRuntime
from .lifecycle import ModelLifecyclePipeline, HardwareMemoryBudgeter, GGUFInspector


class DualModelCoordinator:
    """
    Coordinates July and Gravity as two independent, permanently available models.
    """

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        auth: Optional[ClientAuthManager] = None,
        runtime: Optional[ClientInferenceRuntime] = None,
        storage: Optional[PermanentModelStorage] = None,
        state_mgr: Optional[DualModelStateManager] = None
    ):
        self.config = config or ClientConfig.load()
        self.auth = auth or ClientAuthManager()
        self.storage = storage or PermanentModelStorage()
        self.state_mgr = state_mgr or DualModelStateManager()
        self.runtime = runtime or ClientInferenceRuntime(config=self.config)

        self._inference_lock = threading.Lock()
        self._bg_threads: Dict[str, threading.Thread] = {}
        self._bg_cancel_flags: Dict[str, threading.Event] = {}

        # Sync disk presence on startup
        self.sync_disk_state()

    def sync_disk_state(self):
        """Scans permanent storage and synchronizes states without redownloading."""
        for mid in ("july", "gravity"):
            is_present = self.storage.is_model_present(mid)
            current_state = self.state_mgr.get_model_state(mid)

            if is_present:
                if current_state in (ModelStatus.NOT_DOWNLOADED.value, ModelStatus.ERROR.value, ModelStatus.DOWNLOADING.value):
                    self.state_mgr.set_model_state(mid, ModelStatus.DOWNLOADED.value)
            else:
                if current_state not in (ModelStatus.DOWNLOADING.value,):
                    self.state_mgr.set_model_state(mid, ModelStatus.NOT_DOWNLOADED.value)

        # Restore persistent selection
        saved_sel = getattr(self.config, "selected_model", "july").lower()
        if saved_sel in ("july", "gravity"):
            self.state_mgr.selectedModel = saved_sel

    def select_model(self, model_id: str, on_activated_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        User selects a model (Requirement 1):
        - Set selectedModel to target.
        - If target is downloaded and initialized, activate immediately.
        - If downloaded but not initialized, initialize and activate.
        - If not downloaded, keep current operational model answering prompts while target downloads in background.
        """
        target = model_id.lower().strip()
        if target not in ("july", "gravity"):
            raise ValueError(f"Unknown model: {model_id}. Must be 'july' or 'gravity'.")

        self.state_mgr.selectedModel = target
        self.config.selected_model = target
        self.config.save()

        # Check disk availability
        target_file = self.storage.get_model_file(target)
        target_present = target_file.exists() and target_file.stat().st_size == self.storage.EXPECTED_SIZES.get(target)

        if target_present:
            # Already on disk! Mount and activate
            self._activate_local_model(target)
            if on_activated_callback:
                on_activated_callback(target)
            return target
        else:
            # Not downloaded: keep currently operational fallback model
            operational_model = self._ensure_operational_fallback(exclude_model=target)

            # Start non-blocking background acquisition for target
            self._launch_background_download(target, auto_activate=True, callback=on_activated_callback)

            return operational_model

    def _activate_local_model(self, model_id: str):
        """Safely loads model into memory with single-model RAM protection (Requirement 4)."""
        with self._inference_lock:
            if self.runtime.is_loaded() and self.runtime.current_model_id == model_id:
                self.state_mgr.set_model_state(model_id, ModelStatus.READY.value)
                self.state_mgr.activeModel = model_id
                return

            # Safely unload existing model from memory (NEVER deleting disk file)
            if self.runtime.is_loaded():
                curr_mid = self.runtime.current_model_id
                self.runtime.unload(wipe_storage=False)
                self.state_mgr.set_model_state(curr_mid, ModelStatus.UNLOADED.value)

            model_file = self.storage.get_model_file(model_id)
            if not model_file.exists():
                raise FileNotFoundError(f"Model file missing: {model_file}")

            self.state_mgr.set_model_state(model_id, ModelStatus.INITIALIZING.value)
            self.runtime.switch_model(model_id, model_path=model_file)
            self.state_mgr.set_model_state(model_id, ModelStatus.READY.value)
            self.state_mgr.activeModel = model_id

    def _ensure_operational_fallback(self, exclude_model: str) -> str:
        """Finds and ensures an operational fallback model is running so user isn't blocked."""
        fallback = "july" if exclude_model == "gravity" else "gravity"
        fallback_file = self.storage.get_model_file(fallback)

        if fallback_file.exists() and fallback_file.stat().st_size == self.storage.EXPECTED_SIZES.get(fallback):
            if not self.runtime.is_loaded() or self.runtime.current_model_id != fallback:
                self._activate_local_model(fallback)
            return fallback
        return "none"

    def _launch_background_download(
        self,
        model_id: str,
        auto_activate: bool = True,
        callback: Optional[Callable[[str], None]] = None
    ):
        """Spawns background worker to download, verify, and auto-activate target model."""
        if model_id in self._bg_threads and self._bg_threads[model_id].is_alive():
            return

        stop_evt = threading.Event()
        self._bg_cancel_flags[model_id] = stop_evt

        def worker():
            try:
                self.state_mgr.set_model_state(model_id, ModelStatus.DOWNLOADING.value)
                downloader = ClientModelDownloader(self.config, self.auth)
                manifest = downloader.request_presigned_download(model_id)
                download_url = manifest["download_url"]
                remote_size = manifest["size_bytes"]
                expected_sha = manifest.get("expected_sha256", "").lower().strip()
                dest_path = self.storage.get_model_file(model_id)

                def bg_progress(stats: Dict[str, Any]):
                    if stop_evt.is_set():
                        raise InterruptedError("Download canceled by user.")
                    self.state_mgr.update_progress(
                        model_id=model_id,
                        stage="DOWNLOADING",
                        percent=stats.get("percent", 0.0),
                        speed_mb=stats.get("speed_mbps", 0.0),
                        eta_seconds=stats.get("eta_seconds", 0.0)
                    )

                p_dl = DirectR2ParallelDownloader(
                    num_workers=int(os.getenv("R2_DOWNLOAD_WORKERS", "6")),
                    chunk_size_mb=16,
                    url_refresh_callback=lambda: downloader.request_presigned_download(model_id)["download_url"]
                )

                p_dl.download(
                    download_url=download_url,
                    dest_path=dest_path,
                    total_size=remote_size,
                    model_id=model_id,
                    object_key=manifest.get("object_key", ""),
                    expected_sha256=expected_sha,
                    progress_callback=bg_progress
                )

                # Verification
                self.state_mgr.set_model_state(model_id, ModelStatus.VERIFYING.value)
                is_valid, actual_sha, _ = self.storage.verify_model_checksum(model_id)
                if not is_valid:
                    self.state_mgr.set_model_state(
                        model_id,
                        ModelStatus.ERROR.value,
                        {"error": f"SHA-256 mismatch: expected {expected_sha}, got {actual_sha}"}
                    )
                    return

                # Record manifest
                self.storage.save_manifest(model_id, {
                    "model_id": model_id,
                    "sha256": actual_sha,
                    "size_bytes": remote_size,
                    "verified": True,
                    "completed_at": time.time()
                })

                self.state_mgr.set_model_state(model_id, ModelStatus.DOWNLOADED.value)

                # Automatic activation if user still wants this model
                if auto_activate and self.state_mgr.selectedModel == model_id:
                    self._activate_local_model(model_id)
                    if callback:
                        callback(model_id)

            except Exception as e:
                self.state_mgr.set_model_state(
                    model_id,
                    ModelStatus.ERROR.value,
                    {"error": str(e), "stage": "BACKGROUND_ACQUISITION"}
                )

        t = threading.Thread(target=worker, name=f"bg-dl-{model_id}", daemon=True)
        self._bg_threads[model_id] = t
        t.start()

    def get_status_summary(self) -> Dict[str, Any]:
        """Provides full telemetry across both models for UI rendering."""
        return {
            "selectedModel": self.state_mgr.selectedModel,
            "activeModel": self.state_mgr.activeModel,
            "downloadingModels": self.state_mgr.downloadingModels,
            "availableModels": self.state_mgr.availableModels,
            "loadedModels": self.state_mgr.loadedModels,
            "modelStates": self.state_mgr.modelInitializationStatus
        }

    def generate_response(self, prompt: str, session_id: str = "default"):
        """Routes prompt to the active model runtime with thread safety."""
        with self._inference_lock:
            return self.runtime.generate_stream(prompt, session_id=session_id)
