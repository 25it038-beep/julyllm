"""
HS AI SOLUTIONS — MODEL INITIALIZATION & LIFECYCLE PIPELINE
Layer: CLIENT MODEL LIFECYCLE (july_distribution.client.lifecycle)
Founder & Chief Architect: Harshan Seliyan
Platform: JULY LLM & GRAVITY LLM

Guarantees strict 8-stage progression:
DOWNLOADING → VERIFYING → FINALIZING → INSPECTING → INITIALIZING → LOADING → WARMING UP → READY.

Features:
1. Explicit progress indicators for every single stage.
2. Cryptographic SHA-256 validation against trusted server-side checksum.
3. Fast-path local cache reuse (never redownload verified files).
4. Pure-Python GGUF v2/v3 header & tensor metadata inspection.
5. Hardware & memory-aware dynamic layer budget (16 GB RAM + 6 GB RTX 3050 VRAM).
6. Partial GPU offloading with 4096 conservative context window.
7. Validation test inference before declaring READY.
8. Comprehensive error interception with actionable diagnostic reporting.
"""

from __future__ import annotations
import os
import sys
import time
import math
import struct
import shutil
import hashlib
import ctypes
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Tuple

import psutil

from .config import ClientConfig
from .auth import ClientAuthManager
from .storage import ClientEphemeralStorage, FILE_ATTRIBUTE_TEMPORARY
from .downloader import ClientModelDownloader


class UI:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class GGUFMetadata:
    """Represents inspected metadata from a GGUF file header."""
    def __init__(
        self,
        version: int,
        tensor_count: int,
        kv_count: int,
        architecture: str,
        block_count: int,
        context_length: int,
        embedding_length: int,
        file_type: int
    ):
        self.version = version
        self.tensor_count = tensor_count
        self.kv_count = kv_count
        self.architecture = architecture
        self.block_count = block_count
        self.context_length = context_length
        self.embedding_length = embedding_length
        self.file_type = file_type


class GGUFInspector:
    """Pure-Python zero-dependency GGUF v2/v3 binary header reader."""

    @staticmethod
    def inspect(file_path: Path) -> GGUFMetadata:
        if not file_path.exists():
            raise FileNotFoundError(f"GGUF file does not exist: {file_path}")

        file_size = file_path.stat().st_size
        if file_size < 24:
            raise ValueError(f"File too small to be valid GGUF: {file_size} bytes")

        with open(file_path, "rb") as f:
            magic = f.read(4)
            if magic != b"GGUF":
                raise ValueError(f"Invalid GGUF magic header: {magic!r} (expected b'GGUF')")

            version = struct.unpack("<I", f.read(4))[0]
            if version not in (2, 3):
                raise ValueError(f"Unsupported GGUF version: {version} (supported: 2, 3)")

            if version == 3:
                tensor_count, kv_count = struct.unpack("<QQ", f.read(16))
            else:
                tensor_count, kv_count = struct.unpack("<QI", f.read(12))

            def _read_str() -> str:
                str_len = struct.unpack("<Q", f.read(8))[0]
                if str_len > 1000000:
                    raise ValueError(f"GGUF string length corrupt: {str_len}")
                return f.read(str_len).decode("utf-8", errors="replace")

            def _parse_val(vt: int) -> Any:
                if vt == 0: return struct.unpack("<B", f.read(1))[0]
                if vt == 1: return struct.unpack("<b", f.read(1))[0]
                if vt == 2: return struct.unpack("<H", f.read(2))[0]
                if vt == 3: return struct.unpack("<h", f.read(2))[0]
                if vt == 4: return struct.unpack("<I", f.read(4))[0]
                if vt == 5: return struct.unpack("<i", f.read(4))[0]
                if vt == 6: return struct.unpack("<f", f.read(4))[0]
                if vt == 7: return bool(struct.unpack("<?", f.read(1))[0])
                if vt == 8: return _read_str()
                if vt == 9:
                    sub_type, count = struct.unpack("<IQ", f.read(12))
                    return [_parse_val(sub_type) for _ in range(count)]
                if vt == 10: return struct.unpack("<Q", f.read(8))[0]
                if vt == 11: return struct.unpack("<q", f.read(8))[0]
                if vt == 12: return struct.unpack("<d", f.read(8))[0]
                return None

            meta: Dict[str, Any] = {}
            for _ in range(min(kv_count, 128)):
                k = _read_str()
                vt = struct.unpack("<I", f.read(4))[0]
                val = _parse_val(vt)
                meta[k] = val

            arch = str(meta.get("general.architecture", "llama"))
            block_count = int(meta.get(f"{arch}.block_count", meta.get("llama.block_count", 32)))
            ctx_len = int(meta.get(f"{arch}.context_length", meta.get("llama.context_length", 4096)))
            emb_len = int(meta.get(f"{arch}.embedding_length", meta.get("llama.embedding_length", 4096)))
            file_type = int(meta.get("general.file_type", 1))

            return GGUFMetadata(
                version=version,
                tensor_count=tensor_count,
                kv_count=kv_count,
                architecture=arch,
                block_count=block_count,
                context_length=ctx_len,
                embedding_length=emb_len,
                file_type=file_type
            )


class HardwareMemoryBudgeter:
    """Profiles system RAM and NVIDIA GPU VRAM to calculate memory-aware layer offloading."""

    @staticmethod
    def profile_and_budget(
        model_size_bytes: int,
        total_layers: int,
        target_context: int = 4096,
        force_cpu: bool = False
    ) -> Dict[str, Any]:
        # 1. System RAM
        vm = psutil.virtual_memory()
        ram_total_gb = round(vm.total / (1024**3), 2)
        ram_free_gb = round(vm.available / (1024**3), 2)

        # 2. NVIDIA GPU VRAM Telemetry
        gpu_available = False
        gpu_name = "CPU Only"
        vram_total_mb = 0.0
        vram_free_mb = 0.0

        if not force_cpu:
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_available = True
                    gpu_name = torch.cuda.get_device_name(0)
                    free_b, total_b = torch.cuda.mem_get_info(0)
                    vram_total_mb = round(total_b / (1024 * 1024), 2)
                    vram_free_mb = round(free_b / (1024 * 1024), 2)
            except Exception:
                pass

        cpu_threads = os.cpu_count() or 4
        recommended_threads = max(1, min(cpu_threads, 6))

        # 3. Dynamic Memory-Aware GPU Layer Allocation (Partial Offload)
        model_mb = model_size_bytes / (1024 * 1024)
        layer_count = max(1, total_layers)
        mb_per_layer = model_mb / layer_count

        recommended_gpu_layers = 0
        offload_strategy = "CPU"

        if gpu_available and vram_free_mb >= 2000:
            # Conservative VRAM Reserve: 1200 MB for KV Cache (4096 ctx) + Windows DWM headroom
            vram_reserve_mb = 1200.0
            usable_vram_mb = max(0.0, vram_free_mb - vram_reserve_mb)
            
            # Calculate max safe layers within usable VRAM
            calculated_layers = int(usable_vram_mb // mb_per_layer)
            recommended_gpu_layers = max(0, min(total_layers, calculated_layers))

            if recommended_gpu_layers >= total_layers:
                offload_strategy = "FULL_GPU"
            elif recommended_gpu_layers > 0:
                offload_strategy = "PARTIAL_GPU"
            else:
                offload_strategy = "CPU_FALLBACK"

        return {
            "ram_total_gb": ram_total_gb,
            "ram_free_gb": ram_free_gb,
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "vram_total_mb": vram_total_mb,
            "vram_free_mb": vram_free_mb,
            "total_layers": total_layers,
            "recommended_gpu_layers": recommended_gpu_layers,
            "recommended_threads": recommended_threads,
            "target_context": target_context,
            "offload_strategy": offload_strategy,
            "mb_per_layer": round(mb_per_layer, 2)
        }


class ModelLifecyclePipeline:
    """
    Executes the 8-stage model initialization pipeline:
    DOWNLOADING → VERIFYING → FINALIZING → INSPECTING → INITIALIZING → LOADING → WARMING UP → READY.
    """

    def __init__(self, config: Optional[ClientConfig] = None, auth: Optional[ClientAuthManager] = None):
        self.config = config or ClientConfig.load()
        self.auth = auth or ClientAuthManager()
        self.storage = ClientEphemeralStorage()

    @staticmethod
    def _print_stage(stage_num: int, stage_name: str, status_text: str, color: str = UI.CYAN):
        prefix = f" [{stage_num}/8] {stage_name.ljust(12)}"
        print(f" {color}{UI.BOLD}{prefix}{UI.RESET} {status_text}")

    def execute_pipeline(
        self,
        model_id: str = "gravity",
        dest_path: Optional[Path] = None,
        force_cpu: bool = False
    ) -> Tuple[Any, GGUFMetadata, Dict[str, Any]]:
        """
        Executes the entire verified lifecycle pipeline from storage to active inference.
        Returns: (initialized_llama_llm, gguf_metadata, budget_dict)
        """
        mid = model_id.lower().strip()
        model_title = "GRAVITY LLM" if mid == "gravity" else "JULY LLM"

        print(f"\n{UI.BOLD}{UI.CYAN}{'═'*78}{UI.RESET}")
        print(f" {UI.BOLD}HS AI SOLUTIONS — AUTONOMOUS MODEL LIFECYCLE PIPELINE{UI.RESET}")
        print(f" Target Model : {UI.BOLD}{UI.YELLOW}{model_title}{UI.RESET} (ID: {mid})")
        print(f" Progression  : DOWNLOADING → VERIFYING → FINALIZING → INSPECTING →")
        print(f"                INITIALIZING → LOADING → WARMING UP → READY")
        print(f"{UI.BOLD}{UI.CYAN}{'═'*78}{UI.RESET}\n")

        # -------------------------------------------------------------------------
        # Pre-flight: Request remote manifest from Cloudflare R2
        # -------------------------------------------------------------------------
        downloader = ClientModelDownloader(self.config, self.auth)
        manifest = downloader.request_presigned_download(mid)
        remote_size = manifest["size_bytes"]
        expected_sha = manifest.get("expected_sha256", "").lower().strip()
        download_url = manifest["download_url"]

        if not expected_sha:
            raise ValueError(f"Backend failed to return expected_sha256 for model {mid}")

        if dest_path is None:
            dest_path = self.storage.allocate_path(prefix=f"{mid}_ram_model")

        state_file = dest_path.with_suffix(dest_path.suffix + ".state.json")

        from .state_manager import DualModelStateManager, ModelStatus
        state_mgr = DualModelStateManager()

        # -------------------------------------------------------------------------
        # STAGE 1: DOWNLOADING (or Local Cache Reuse)
        # -------------------------------------------------------------------------
        can_skip_download = False
        if dest_path.exists() and dest_path.stat().st_size == remote_size and not state_file.exists():
            can_skip_download = True

        if can_skip_download:
            state_mgr.set_model_state(mid, ModelStatus.DOWNLOADED.value)
            self._print_stage(
                1, "DOWNLOADING",
                f"{UI.GREEN}✓ Reusing existing complete checkpoint ({remote_size:,} bytes). Skipping network transfer.{UI.RESET}",
                UI.GREEN
            )
        else:
            state_mgr.set_model_state(mid, ModelStatus.DOWNLOADING.value)
            self._print_stage(
                1, "DOWNLOADING",
                f"Connecting directly to Cloudflare R2 ({remote_size / (1024**3):.2f} GiB)...",
                UI.CYAN
            )

            def dl_progress(stats: Dict[str, Any]):
                pct = stats["percent"]
                done_mb = stats["completed_bytes"] / (1024 * 1024)
                tot_mb = stats["total_bytes"] / (1024 * 1024)
                speed = stats["speed_mbps"]
                eta_s = int(stats["eta_seconds"])
                eta_m = eta_s // 60
                eta_rem = eta_s % 60
                streams = stats.get("active_workers", 4)
                sys.stdout.write(
                    f"\r  [DOWNLOADING]  Retrieving Cloudflare R2: [{pct:5.1f}%] {done_mb:7.1f} / {tot_mb:7.1f} MB "
                    f"({speed:4.1f} MB/s | {streams} streams | ETA: {eta_m:02d}m{eta_rem:02d}s)   "
                )
                sys.stdout.flush()

            try:
                from .parallel_downloader import DirectR2ParallelDownloader
                workers = int(os.getenv("R2_DOWNLOAD_WORKERS", "6"))
                chunk_mb = 16

                p_dl = DirectR2ParallelDownloader(
                    num_workers=workers,
                    chunk_size_mb=chunk_mb,
                    url_refresh_callback=lambda: downloader.request_presigned_download(mid)["download_url"]
                )

                p_dl.download(
                    download_url=download_url,
                    dest_path=dest_path,
                    total_size=remote_size,
                    model_id=mid,
                    object_key=manifest.get("object_key", ""),
                    expected_sha256=expected_sha,
                    progress_callback=dl_progress
                )
                sys.stdout.write("\n")
                self._print_stage(
                    1, "DOWNLOADING",
                    f"{UI.GREEN}✓ Download complete: {remote_size:,} bytes assembled without error.{UI.RESET}",
                    UI.GREEN
                )
            except Exception as e:
                sys.stdout.write("\n")
                self._print_stage(1, "DOWNLOADING", f"{UI.RED}✗ Download failure: {e}{UI.RESET}", UI.RED)
                raise RuntimeError(f"[STAGE 1: DOWNLOADING] Failed to retrieve model from R2: {e}")

        # -------------------------------------------------------------------------
        # STAGE 2: VERIFYING (Full Cryptographic SHA-256 Validation)
        # -------------------------------------------------------------------------
        state_mgr.set_model_state(mid, ModelStatus.VERIFYING.value)
        self._print_stage(2, "VERIFYING", f"Computing SHA-256 checksum over {dest_path.stat().st_size:,} bytes...", UI.CYAN)
        t_sha_start = time.time()

        sha256 = hashlib.sha256()
        total_bytes = dest_path.stat().st_size
        bytes_hashed = 0

        with open(dest_path, "rb") as f:
            while True:
                buf = f.read(8 * 1024 * 1024)  # 8 MB streaming read
                if not buf:
                    break
                sha256.update(buf)
                bytes_hashed += len(buf)
                pct = (bytes_hashed / total_bytes) * 100
                elapsed = max(0.001, time.time() - t_sha_start)
                rate_gb = (bytes_hashed / (1024**3)) / elapsed
                sys.stdout.write(f"\r  [VERIFYING]    Validating cryptographic integrity: [{pct:5.1f}%] ({rate_gb:.2f} GB/s)   ")
                sys.stdout.flush()

        sys.stdout.write("\n")
        actual_sha = sha256.hexdigest().lower()

        if actual_sha != expected_sha:
            self._print_stage(2, "VERIFYING", f"{UI.RED}✗ SECURITY FAILURE: Checksum mismatch!{UI.RESET}", UI.RED)
            print(f" {UI.RED}  [!] Expected : {expected_sha}{UI.RESET}")
            print(f" {UI.RED}  [!] Actual   : {actual_sha}{UI.RESET}")
            dest_path.unlink(missing_ok=True)
            if state_file.exists():
                state_file.unlink(missing_ok=True)
            raise ValueError(
                f"[STAGE 2: VERIFYING] SECURITY INTEGRITY COMPROMISED!\n"
                f"Expected: {expected_sha}\nActual:   {actual_sha}\nCorrupt model weights destroyed."
            )

        sha_duration = time.time() - t_sha_start
        self._print_stage(
            2, "VERIFYING",
            f"{UI.GREEN}✓ Cryptographic SHA-256 verified in {sha_duration:.2f}s: {actual_sha}{UI.RESET}",
            UI.GREEN
        )

        # -------------------------------------------------------------------------
        # STAGE 3: FINALIZING (Zero-Persistence RAM Caching & Buffer Sync)
        # -------------------------------------------------------------------------
        self._print_stage(3, "FINALIZING", "Syncing OS disk buffers and activating RAM caching...", UI.CYAN)
        try:
            if state_file.exists():
                state_file.unlink(missing_ok=True)

            # Enable Windows FILE_ATTRIBUTE_TEMPORARY (Ram caching without disk thrashing)
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.SetFileAttributesW(str(dest_path), FILE_ATTRIBUTE_TEMPORARY)
                except Exception:
                    pass

            # Flush file system buffers
            with open(dest_path, "r+b") as f:
                f.flush()
                if hasattr(os, "fsync"):
                    os.fsync(f.fileno())

            self._print_stage(
                3, "FINALIZING",
                f"{UI.GREEN}✓ Storage finalized: {dest_path.stat().st_size:,} bytes primed for ephemeral execution.{UI.RESET}",
                UI.GREEN
            )
        except Exception as e:
            self._print_stage(3, "FINALIZING", f"{UI.YELLOW}! Finalization warning: {e}{UI.RESET}", UI.YELLOW)

        # -------------------------------------------------------------------------
        # STAGE 4: INSPECTING (GGUF Binary Header & Metadata Parsing)
        # -------------------------------------------------------------------------
        self._print_stage(4, "INSPECTING", "Parsing GGUF container headers and tensor layout...", UI.CYAN)
        try:
            gguf_meta = GGUFInspector.inspect(dest_path)
            self._print_stage(
                4, "INSPECTING",
                f"{UI.GREEN}✓ GGUF v{gguf_meta.version} valid | Architecture: {gguf_meta.architecture} | "
                f"Layers: {gguf_meta.block_count} | Tensors: {gguf_meta.tensor_count} | Native Ctx: {gguf_meta.context_length}{UI.RESET}",
                UI.GREEN
            )
        except Exception as e:
            self._print_stage(4, "INSPECTING", f"{UI.RED}✗ GGUF header inspection error: {e}{UI.RESET}", UI.RED)
            raise RuntimeError(f"[STAGE 4: INSPECTING] Model file is corrupt or invalid GGUF format: {e}")

        # -------------------------------------------------------------------------
        # STAGE 5: INITIALIZING (Memory Budgeting: 16 GB RAM + 6 GB RTX 3050 VRAM)
        # -------------------------------------------------------------------------
        self._print_stage(5, "INITIALIZING", "Profiling available host RAM and NVIDIA GPU VRAM...", UI.CYAN)
        try:
            budget = HardwareMemoryBudgeter.profile_and_budget(
                model_size_bytes=dest_path.stat().st_size,
                total_layers=gguf_meta.block_count,
                target_context=4096,  # Requirement 10: Conservative 4096 tokens
                force_cpu=force_cpu
            )

            ram_info = f"RAM: {budget['ram_total_gb']} GB total ({budget['ram_free_gb']} GB available)"
            gpu_info = (
                f"{budget['gpu_name']} ({budget['vram_free_mb']:.0f}/{budget['vram_total_mb']:.0f} MB free VRAM)"
                if budget["gpu_available"] else "CPU Only"
            )

            offload_info = (
                f"Offloading {budget['recommended_gpu_layers']}/{budget['total_layers']} layers to CUDA "
                f"({budget['offload_strategy']}) | n_ctx=4096 | {budget['recommended_threads']} CPU threads"
            )

            self._print_stage(
                5, "INITIALIZING",
                f"{UI.GREEN}✓ Hardware Profile: {ram_info} | {gpu_info}\n"
                f"                   {UI.CYAN}✓ Configuration   : {offload_info}{UI.RESET}",
                UI.GREEN
            )
        except Exception as e:
            self._print_stage(5, "INITIALIZING", f"{UI.RED}✗ Memory profiling error: {e}{UI.RESET}", UI.RED)
            raise RuntimeError(f"[STAGE 5: INITIALIZING] Memory allocation budgeting failed: {e}")

        # -------------------------------------------------------------------------
        # STAGE 6: LOADING (llama.cpp Neural Engine Instantiation)
        # -------------------------------------------------------------------------
        self._print_stage(6, "LOADING", "Mounting model weights into llama.cpp neural runtime...", UI.CYAN)
        t_load_start = time.time()

        try:
            import llama_cpp
        except ImportError:
            self._print_stage(6, "LOADING", f"{UI.RED}✗ llama-cpp-python is missing.{UI.RESET}", UI.RED)
            raise ImportError("[STAGE 6: LOADING] Please install llama-cpp-python: pip install llama-cpp-python")

        llm = None
        n_gpu = budget["recommended_gpu_layers"]

        try:
            llm = llama_cpp.Llama(
                model_path=str(dest_path),
                n_ctx=4096,
                n_gpu_layers=n_gpu,
                n_threads=budget["recommended_threads"],
                n_batch=512,
                logits_all=False,
                verbose=False
            )
        except Exception as cuda_err:
            if n_gpu > 0:
                print(f" {UI.YELLOW} [!] CUDA allocation encountered issue ({cuda_err}). Retrying pure CPU memory-safe fallback...{UI.RESET}")
                try:
                    llm = llama_cpp.Llama(
                        model_path=str(dest_path),
                        n_ctx=4096,
                        n_gpu_layers=0,
                        n_threads=budget["recommended_threads"],
                        n_batch=512,
                        logits_all=False,
                        verbose=False
                    )
                except Exception as cpu_err:
                    self._print_stage(6, "LOADING", f"{UI.RED}✗ CPU Fallback also failed: {cpu_err}{UI.RESET}", UI.RED)
                    raise RuntimeError(f"[STAGE 6: LOADING] Pure CPU fallback failed: {cpu_err}")
            else:
                self._print_stage(6, "LOADING", f"{UI.RED}✗ Inference engine loading failed: {cuda_err}{UI.RESET}", UI.RED)
                raise RuntimeError(f"[STAGE 6: LOADING] Failed to instantiate llama.cpp: {cuda_err}")

        load_duration = time.time() - t_load_start
        self._print_stage(
            6, "LOADING",
            f"{UI.GREEN}✓ Neural weights successfully mounted in {load_duration:.2f}s!{UI.RESET}",
            UI.GREEN
        )

        # -------------------------------------------------------------------------
        # STAGE 7: WARMING UP (Validation Test Inference)
        # -------------------------------------------------------------------------
        self._print_stage(7, "WARMING UP", "Executing short test inference to prime compute graph...", UI.CYAN)
        t_warm_start = time.time()

        try:
            test_prompt = "Hello"
            test_res = llm(test_prompt, max_tokens=3, stop=["\n"])
            warm_duration_ms = (time.time() - t_warm_start) * 1000.0
            generated_token = test_res["choices"][0]["text"].strip()
            self._print_stage(
                7, "WARMING UP",
                f"{UI.GREEN}✓ Warm-up inference verified ({warm_duration_ms:.1f}ms latency | Output: '{generated_token}'){UI.RESET}",
                UI.GREEN
            )
        except Exception as warm_err:
            self._print_stage(7, "WARMING UP", f"{UI.RED}✗ Test inference failed: {warm_err}{UI.RESET}", UI.RED)
            raise RuntimeError(f"[STAGE 7: WARMING UP] Compute graph test failed: {warm_err}")

        # -------------------------------------------------------------------------
        # STAGE 8: READY (Model Available for Interaction)
        # -------------------------------------------------------------------------
        state_mgr.set_model_state(mid, ModelStatus.READY.value)
        state_mgr.activeModel = mid
        self._print_stage(
            8, "READY",
            f"{UI.BOLD}{UI.GREEN}🚀 {model_title} is verified, loaded in RAM, and ready for genuine local inference!{UI.RESET}",
            UI.GREEN
        )
        print(f"\n{UI.BOLD}{UI.CYAN}{'═'*78}{UI.RESET}\n")

        return llm, gguf_meta, budget
