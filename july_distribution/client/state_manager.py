"""
HS AI SOLUTIONS — DUAL MODEL STATE MANAGER
Layer: STATE MANAGEMENT (july_distribution.client.state_manager)
Organization: HS AI Solutions | Founder & Chief Architect: Harshan Seliyan
Product: JULY & GRAVITY DUAL-MODEL ARCHITECTURE

Tracks model states independently:
- NOT_DOWNLOADED
- DOWNLOADING
- DOWNLOAD_PAUSED
- VERIFYING
- DOWNLOADED
- INITIALIZING
- READY
- UNLOADED
- ERROR

Maintains separate properties:
- selectedModel
- activeModel
- downloadingModels
- availableModels
- loadedModels
- modelInitializationStatus
"""

from __future__ import annotations
import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from enum import Enum


class ModelStatus(str, Enum):
    NOT_DOWNLOADED = "NOT_DOWNLOADED"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOAD_PAUSED = "DOWNLOAD_PAUSED"
    VERIFYING = "VERIFYING"
    DOWNLOADED = "DOWNLOADED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    UNLOADED = "UNLOADED"
    ERROR = "ERROR"


class DualModelStateManager:
    """
    Thread-safe State Manager for July & Gravity Dual-Model Architecture.
    Never confuses selectedModel (user preference) with activeModel (currently operational).
    """

    SUPPORTED_MODELS = ("july", "gravity")

    def __init__(self, state_file: Optional[Path] = None):
        self._lock = threading.RLock()
        self._state_file = state_file or self._default_state_file()
        
        # Core architectural properties
        self._selected_model: str = "july"
        self._active_model: str = "none"
        self._model_states: Dict[str, str] = {
            "july": ModelStatus.NOT_DOWNLOADED.value,
            "gravity": ModelStatus.NOT_DOWNLOADED.value
        }
        self._initialization_status: Dict[str, Dict[str, Any]] = {
            "july": {"stage": "IDLE", "percent": 0.0, "error": None, "timestamp": time.time()},
            "gravity": {"stage": "IDLE", "percent": 0.0, "error": None, "timestamp": time.time()}
        }
        self._listeners: List[Callable[[str, str, Dict[str, Any]], None]] = []

        self.load()

    @staticmethod
    def _default_state_file() -> Path:
        custom_dir = os.getenv("JULY_CLIENT_HOME")
        if custom_dir:
            p = Path(custom_dir)
        else:
            p = Path.home() / ".july"
        p.mkdir(parents=True, exist_ok=True)
        return p / "dual_model_state.json"

    # --- Property Accessors (as per Requirement 3) ---

    @property
    def selectedModel(self) -> str:
        """The user's persistent model choice."""
        with self._lock:
            return self._selected_model

    @selectedModel.setter
    def selectedModel(self, model_id: str):
        mid = model_id.lower().strip()
        if mid not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_id}. Must be one of {self.SUPPORTED_MODELS}")
        with self._lock:
            self._selected_model = mid
            self.save()

    @property
    def activeModel(self) -> str:
        """The model currently executing inference / answering prompts."""
        with self._lock:
            return self._active_model

    @activeModel.setter
    def activeModel(self, model_id: str):
        mid = model_id.lower().strip()
        if mid != "none" and mid not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported active model: {model_id}")
        with self._lock:
            self._active_model = mid
            self.save()

    @property
    def downloadingModels(self) -> List[str]:
        """Models currently in DOWNLOADING state."""
        with self._lock:
            return [m for m, s in self._model_states.items() if s == ModelStatus.DOWNLOADING.value]

    @property
    def availableModels(self) -> List[str]:
        """Models downloaded and verified on disk (DOWNLOADED, UNLOADED, or READY)."""
        with self._lock:
            available_statuses = {
                ModelStatus.DOWNLOADED.value,
                ModelStatus.INITIALIZING.value,
                ModelStatus.READY.value,
                ModelStatus.UNLOADED.value
            }
            return [m for m, s in self._model_states.items() if s in available_statuses]

    @property
    def loadedModels(self) -> List[str]:
        """Models currently residing in active system RAM / VRAM."""
        with self._lock:
            return [m for m, s in self._model_states.items() if s == ModelStatus.READY.value]

    @property
    def modelInitializationStatus(self) -> Dict[str, Dict[str, Any]]:
        """Detailed status and telemetry for each model."""
        with self._lock:
            return {
                m: {
                    "state": self._model_states.get(m, ModelStatus.NOT_DOWNLOADED.value),
                    **self._initialization_status.get(m, {})
                }
                for m in self.SUPPORTED_MODELS
            }

    # --- State Transitions ---

    def get_model_state(self, model_id: str) -> str:
        with self._lock:
            return self._model_states.get(model_id.lower().strip(), ModelStatus.NOT_DOWNLOADED.value)

    def set_model_state(self, model_id: str, status: ModelStatus | str, details: Optional[Dict[str, Any]] = None):
        mid = model_id.lower().strip()
        if mid not in self.SUPPORTED_MODELS:
            return

        stat_val = status.value if isinstance(status, ModelStatus) else str(status)

        with self._lock:
            old_state = self._model_states.get(mid)
            self._model_states[mid] = stat_val

            info = self._initialization_status.setdefault(mid, {})
            info["timestamp"] = time.time()
            if details:
                info.update(details)

            # Update activeModel if model transitioned to READY or UNLOADED
            if stat_val == ModelStatus.READY.value:
                # In resource-limited systems, making this ready means active
                self._active_model = mid
            elif stat_val in (ModelStatus.UNLOADED.value, ModelStatus.ERROR.value) and self._active_model == mid:
                self._active_model = "none"

            self.save()

            # Trigger listeners
            listeners = list(self._listeners)

        for callback in listeners:
            try:
                callback(mid, stat_val, details or {})
            except Exception:
                pass

    def update_progress(self, model_id: str, stage: str, percent: float, speed_mb: float = 0.0, eta_seconds: float = 0.0):
        with self._lock:
            mid = model_id.lower().strip()
            if mid in self._initialization_status:
                self._initialization_status[mid].update({
                    "stage": stage,
                    "percent": percent,
                    "speed_mb": speed_mb,
                    "eta_seconds": eta_seconds,
                    "timestamp": time.time()
                })

    def register_listener(self, callback: Callable[[str, str, Dict[str, Any]], None]):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[str, str, Dict[str, Any]], None]):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    # --- Persistence ---

    def save(self):
        with self._lock:
            try:
                data = {
                    "selectedModel": self._selected_model,
                    "activeModel": self._active_model,
                    "modelStates": self._model_states,
                    "initializationStatus": self._initialization_status,
                    "updated_at": time.time()
                }
                self._state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self._state_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

    def load(self):
        with self._lock:
            if not self._state_file.exists():
                return
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                sel = data.get("selectedModel", "july").lower()
                if sel in self.SUPPORTED_MODELS:
                    self._selected_model = sel
                
                act = data.get("activeModel", "none").lower()
                if act in self.SUPPORTED_MODELS or act == "none":
                    self._active_model = act

                states = data.get("modelStates", {})
                for m in self.SUPPORTED_MODELS:
                    if m in states:
                        self._model_states[m] = states[m]

                init_stat = data.get("initializationStatus", {})
                for m in self.SUPPORTED_MODELS:
                    if m in init_stat:
                        self._initialization_status[m] = init_stat[m]
            except Exception:
                pass
