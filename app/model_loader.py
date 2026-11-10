"""
HS AI SOLUTIONS - JULY MODEL LOADER & HF SYNCHRONIZER
Atomic Hugging Face Hub Retrieval, Verification, & RAM Initialization
Founder: Harshan Seliyan
"""

import os
import sys
import time
import shutil
import hashlib
import threading
from typing import Optional, Dict, Any
from huggingface_hub import hf_hub_download

from app.config import settings
from app.gguf_inspector import inspect_gguf_file, GGUFInspectionError
from app.monitoring import metrics

# Lock ensuring single-threaded model load/reload
load_lock = threading.Lock()


class ModelLoadError(Exception):
    pass


class ModelManager:
    """
    Manages GGUF model lifecycle:
    1. Remote Hugging Face synchronization with atomic file replacement
    2. GGUF header validation and memory estimation
    3. Hardware headroom verification
    4. llama.cpp instantiation and thread safety
    """

    def __init__(self):
        self.llm = None
        self.is_loaded = False
        self.model_metadata: Dict[str, Any] = {}
        self.model_path = settings.MODEL_PATH
        self.is_mock = settings.MOCK_INFERENCE

    def verify_file_integrity(self, file_path: str) -> bool:
        """Verifies file existence, minimum size, and SHA256 if specified."""
        if not os.path.exists(file_path):
            return False

        size = os.path.getsize(file_path)
        # GGUF 3B models are typically > 1.2 GB
        if size < 50 * 1024 * 1024:  # Less than 50MB is definitely corrupt or incomplete
            print(f"[HS JULY LOADER] File {file_path} size ({size} bytes) is suspiciously small.")
            return False

        if settings.EXPECTED_SIZE and size != settings.EXPECTED_SIZE:
            print(f"[HS JULY LOADER] Size mismatch: expected {settings.EXPECTED_SIZE}, got {size}")
            return False

        if settings.EXPECTED_SHA256:
            print(f"[HS JULY LOADER] Calculating SHA-256 for {file_path}...")
            sha = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(16 * 1024 * 1024):
                    sha.update(chunk)
            computed = sha.hexdigest().lower()
            if computed != settings.EXPECTED_SHA256.lower():
                print(f"[HS JULY LOADER] Checksum mismatch: expected {settings.EXPECTED_SHA256}, got {computed}")
                return False

        return True

    def ensure_model_available(self) -> str:
        """
        Ensures model exists on persistent disk.
        If missing or corrupt, downloads atomically from Hugging Face Hub.
        """
        # If running in mock mode, bypass download
        if self.is_mock:
            print("[HS JULY LOADER] MOCK_INFERENCE enabled. Skipping remote download.")
            return "mock://Gravity_HS.gguf"

        # Check existing model on disk
        if self.verify_file_integrity(self.model_path):
            print(f"[HS JULY LOADER] Verified existing model at: {self.model_path}")
            return self.model_path

        # If model file is not at target path, check local fallback directory
        alt_paths = [
            os.path.join(os.getcwd(), "models", settings.MODEL_FILENAME),
            os.path.join(os.getcwd(), "models", "july-final.gguf"),
            r"E:\guff\Gravity_HS.gguf"
        ]
        for alt in alt_paths:
            if os.path.exists(alt) and self.verify_file_integrity(alt):
                print(f"[HS JULY LOADER] Found valid local model at: {alt}")
                self.model_path = alt
                return alt

        # Download from Hugging Face Hub
        target_dir = os.path.dirname(os.path.abspath(self.model_path))
        os.makedirs(target_dir, exist_ok=True)
        temp_path = self.model_path + ".tmp"

        print(f"[HS JULY LOADER] Initiating secure download from HF: {settings.MODEL_REPO} / {settings.MODEL_FILENAME}...")
        try:
            downloaded_cached = hf_hub_download(
                repo_id=settings.MODEL_REPO,
                filename=settings.MODEL_FILENAME,
                token=settings.HF_TOKEN,
                local_dir=target_dir,
                local_dir_use_symlinks=False,
                resume_download=True
            )
            # If hf_hub_download saved to a different name or path, rename atomically
            if downloaded_cached != self.model_path:
                shutil.move(downloaded_cached, self.model_path)

            if not self.verify_file_integrity(self.model_path):
                raise ModelLoadError("Downloaded model failed integrity verification.")

            print(f"[HS JULY LOADER] Model successfully stored and verified at {self.model_path}")
            return self.model_path

        except Exception as e:
            err_msg = (
                f"Failed to synchronize model from Hugging Face ({settings.MODEL_REPO}): {e}. "
                "Ensure MODEL_REPO, MODEL_FILENAME, and HF_TOKEN (for private repos) are properly configured."
            )
            print(f"[HS JULY LOADER] {err_msg}", file=sys.stderr)
            raise ModelLoadError(err_msg)

    def check_system_headroom(self, required_mb: float = 2200.0):
        """Checks available RAM before attempting model load."""
        mem = metrics.get_system_memory()
        avail = mem.get("available_mb", 0.0)
        total = mem.get("total_mb", 0.0)
        print(f"[HS JULY LOADER] Hardware Profile: Total RAM: {total} MB | Available RAM: {avail} MB | CPU Threads: {settings.N_THREADS}")

        if total > 0 and avail < 500.0:
            print(f"[HS JULY LOADER] WARNING: Critically low available RAM ({avail} MB). Model loading may cause OOM.")

    def load(self, force_cpu: bool = True):
        """Loads GGUF model into memory using llama.cpp with CPU optimization."""
        with load_lock:
            if self.is_loaded and self.llm is not None:
                return

            start_time = metrics.record_model_load_start()

            if self.is_mock:
                print("[HS JULY LOADER] Initializing in MOCK INFERENCE mode...")
                time.sleep(0.5)
                self.is_loaded = True
                self.model_metadata = {
                    "architecture": "llama",
                    "model_name": "JULY-3B-MOCK",
                    "quantization": "Q4_K_M (Simulated)",
                    "context_length": settings.N_CTX,
                    "parameter_label": "3B",
                    "is_mock": True
                }
                metrics.record_model_load_complete(start_time)
                print("[HS JULY LOADER] Mock Model ready for testing.")
                return

            # Ensure model path is ready and downloaded
            real_path = self.ensure_model_available()

            # Inspect GGUF binary metadata
            print(f"[HS JULY LOADER] Inspecting GGUF binary: {real_path}...")
            try:
                self.model_metadata = inspect_gguf_file(real_path)
                print(
                    f"[HS JULY LOADER] Architecture: {self.model_metadata.get('architecture')} | "
                    f"Quantization: {self.model_metadata.get('quantization')} | "
                    f"Params: {self.model_metadata.get('parameter_label')} | "
                    f"Native Context: {self.model_metadata.get('context_length')}"
                )
            except GGUFInspectionError as ge:
                raise ModelLoadError(f"GGUF Inspection failed: {ge}")

            # Verify system resources
            self.check_system_headroom()

            # Initialize llama.cpp
            try:
                import llama_cpp
            except ImportError:
                raise ModelLoadError("llama_cpp_python is not installed. Install requirements.txt first.")

            print(
                f"[HS JULY LOADER] Loading GGUF into llama.cpp (Threads={settings.N_THREADS}, "
                f"Context={settings.N_CTX}, Batch={settings.N_BATCH}, CPU-Only=True)..."
            )

            try:
                self.llm = llama_cpp.Llama(
                    model_path=real_path,
                    n_ctx=settings.N_CTX,
                    n_threads=settings.N_THREADS,
                    n_batch=settings.N_BATCH,
                    n_gpu_layers=0,  # Pure CPU execution on Render
                    verbose=False
                )
                self.is_loaded = True
                metrics.record_model_load_complete(start_time)
                print(f"[HS JULY LOADER] JULY LLM loaded successfully in {metrics.load_duration_seconds}s.")
            except Exception as e:
                self.is_loaded = False
                self.llm = None
                raise ModelLoadError(f"Failed to load GGUF weights into llama.cpp: {e}")

    def unload(self):
        """Releases GGUF model memory."""
        with load_lock:
            if self.llm is not None:
                del self.llm
                self.llm = None
            self.is_loaded = False
            import gc
            gc.collect()
            print("[HS JULY LOADER] Model unloaded. Memory reclaimed.")


model_manager = ModelManager()
