"""
HS AI SOLUTIONS — HIGH-PERFORMANCE DIRECT R2 PARALLEL DOWNLOAD ENGINE
Layer: CLIENT RETRIEVAL ENGINE (july_distribution.client.parallel_downloader)
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM & GRAVITY LLM | Storage: Cloudflare R2 (Private Bucket 'july')

High-Performance Multi-Stream Engine:
1. Direct Cloudflare R2 streaming bypassing Render.
2. Concurrent HTTP Range workers (4 to 8 parallel streams).
3. Configurable 32 MB to 64 MB chunking with byte offset validation.
4. Thread-safe sparse file writing and byte synchronization.
5. Persistent JSON state ledger for instantaneous resume across restarts.
6. Auto-refresh of expired presigned URLs during long-running downloads.
7. Exponential backoff and per-chunk failure recovery.
8. Real-time sliding window telemetry: MB/s, chunks, active streams, ETA.
9. Cryptographic SHA-256 validation before registration.
"""

from __future__ import annotations
import os
import sys
import time
import math
import json
import shutil
import hashlib
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib3


class ChunkMetadata:
    def __init__(self, index: int, start_byte: int, end_byte: int):
        self.index = index
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.length = end_byte - start_byte + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "length": self.length
        }


class DownloadState:
    """Manages persistent ledger for chunk-level resumption."""

    def __init__(self, state_file: Path, model_id: str, object_key: str, total_bytes: int, chunk_size: int, expected_sha256: str):
        self.state_file = state_file
        self.model_id = model_id
        self.object_key = object_key
        self.total_bytes = total_bytes
        self.chunk_size = chunk_size
        self.expected_sha256 = expected_sha256.lower()
        self.completed_chunks: Set[int] = set()
        self.lock = threading.Lock()

    @classmethod
    def load_or_create(
        cls,
        state_file: Path,
        model_id: str,
        object_key: str,
        total_bytes: int,
        chunk_size: int,
        expected_sha256: str
    ) -> DownloadState:
        inst = cls(state_file, model_id, object_key, total_bytes, chunk_size, expected_sha256)
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if (
                    data.get("model_id") == model_id and
                    data.get("total_bytes") == total_bytes and
                    data.get("chunk_size") == chunk_size and
                    data.get("expected_sha256", "").lower() == expected_sha256.lower()
                ):
                    inst.completed_chunks = set(data.get("completed_chunks", []))
                else:
                    state_file.unlink(missing_ok=True)
            except Exception:
                state_file.unlink(missing_ok=True)
        return inst

    def mark_completed(self, chunk_index: int):
        with self.lock:
            self.completed_chunks.add(chunk_index)
            self._save_to_disk()

    def _save_to_disk(self):
        try:
            tmp_file = self.state_file.with_suffix(".tmp")
            payload = {
                "model_id": self.model_id,
                "object_key": self.object_key,
                "total_bytes": self.total_bytes,
                "chunk_size": self.chunk_size,
                "expected_sha256": self.expected_sha256,
                "completed_chunks": sorted(list(self.completed_chunks)),
                "completed_count": len(self.completed_chunks),
                "last_updated": time.time()
            }
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            tmp_file.replace(self.state_file)
        except Exception:
            pass

    def cleanup(self):
        with self.lock:
            self.state_file.unlink(missing_ok=True)


class DirectR2ParallelDownloader:
    """
    High-performance multi-stream downloader directly from Cloudflare R2.
    """

    def __init__(
        self,
        num_workers: int = 4,
        chunk_size_mb: int = 64,
        max_retries: int = 5,
        url_refresh_callback: Optional[Callable[[], str]] = None
    ):
        self.num_workers = max(1, min(8, num_workers))
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        self.max_retries = max_retries
        self.url_refresh_callback = url_refresh_callback
        
        self.cancel_requested = False
        self.retry_count = 0
        self.active_workers = 0
        self.bytes_transferred_this_session = 0
        
        self._url_lock = threading.Lock()
        self._file_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        
        # Sliding-window speed calculation
        self._speed_window: List[tuple[float, int]] = []
        
        # Connection pool with Keep-Alive
        self.http_pool = urllib3.PoolManager(
            maxsize=max(16, self.num_workers * 2),
            retries=urllib3.Retry(total=2, backoff_factor=0.5),
            timeout=urllib3.Timeout(connect=15.0, read=45.0)
        )

    def _record_bytes(self, count: int):
        now = time.time()
        with self._stats_lock:
            self.bytes_transferred_this_session += count
            self._speed_window.append((now, count))
            # Keep last 5 seconds in window
            cutoff = now - 5.0
            self._speed_window = [(t, b) for t, b in self._speed_window if t >= cutoff]

    def get_current_speed_mbps(self) -> float:
        now = time.time()
        with self._stats_lock:
            if not self._speed_window:
                return 0.0
            cutoff = now - 5.0
            valid = [(t, b) for t, b in self._speed_window if t >= cutoff]
            if not valid:
                return 0.0
            total_bytes = sum(b for _, b in valid)
            duration = max(0.2, now - valid[0][0])
            return (total_bytes / (1024 * 1024)) / duration

    def _preallocate_file(self, dest_path: Path, target_size: int):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if not dest_path.exists() or dest_path.stat().st_size != target_size:
            with open(dest_path, "wb") as f:
                if target_size > 0:
                    f.seek(target_size - 1)
                    f.write(b"\0")
                    f.flush()

    def _safe_write_chunk(self, dest_path: Path, offset: int, data: bytes):
        with self._file_lock:
            with open(dest_path, "r+b") as f:
                f.seek(offset)
                f.write(data)
                f.flush()

    def _download_single_chunk(
        self,
        chunk: ChunkMetadata,
        current_url: str,
        dest_path: Path,
        state: DownloadState
    ) -> bool:
        attempt = 0
        while attempt < self.max_retries and not self.cancel_requested:
            attempt += 1
            with self._stats_lock:
                self.active_workers += 1

            headers = {
                "Range": f"bytes={chunk.start_byte}-{chunk.end_byte}",
                "Connection": "keep-alive"
            }

            try:
                resp = self.http_pool.request(
                    "GET",
                    current_url,
                    headers=headers,
                    preload_content=False
                )

                # Validate HTTP 206 Partial Content
                if resp.status not in (206, 200):
                    resp.release_conn()
                    # Check for expiration (401 or 403)
                    if resp.status in (401, 403) and self.url_refresh_callback:
                        with self._url_lock:
                            current_url = self.url_refresh_callback()
                        continue
                    raise IOError(f"HTTP {resp.status} received for chunk {chunk.index}")

                # Stream and buffer chunk data
                buffer = bytearray()
                stream_chunk_size = 256 * 1024  # 256 KB read buffer

                for data_slice in resp.stream(stream_chunk_size):
                    if self.cancel_requested:
                        resp.release_conn()
                        return False
                    buffer.extend(data_slice)
                    self._record_bytes(len(data_slice))

                resp.release_conn()

                # Validate byte length
                if len(buffer) != chunk.length:
                    raise IOError(
                        f"Chunk {chunk.index} length mismatch: got {len(buffer)} bytes, expected {chunk.length}"
                    )

                # Safe offset write
                self._safe_write_chunk(dest_path, chunk.start_byte, buffer)
                state.mark_completed(chunk.index)
                return True

            except Exception as e:
                with self._stats_lock:
                    self.retry_count += 1
                backoff = min(16.0, (2.0 ** (attempt - 1)))
                time.sleep(backoff)
            finally:
                with self._stats_lock:
                    self.active_workers = max(0, self.active_workers - 1)

        return False

    @staticmethod
    def compute_sha256(file_path: Path, progress_callback: Optional[Callable[[float], None]] = None) -> str:
        """Computes SHA-256 hash with progress telemetry."""
        hasher = hashlib.sha256()
        total_size = file_path.stat().st_size
        bytes_read = 0
        chunk_size = 16 * 1024 * 1024  # 16 MB read chunks

        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
                bytes_read += len(chunk)
                if progress_callback and total_size > 0:
                    progress_callback((bytes_read / total_size) * 100)

        return hasher.hexdigest().lower()

    def download(
        self,
        download_url: str,
        dest_path: Path,
        total_size: int,
        model_id: str,
        object_key: str,
        expected_sha256: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Path:
        """
        Executes parallel multi-stream direct Cloudflare R2 download.
        """
        self.cancel_requested = False
        self.retry_count = 0
        self.bytes_transferred_this_session = 0
        start_time = time.time()

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        state_file = dest_path.with_suffix(dest_path.suffix + ".state.json")

        # 1. Local Cache Check
        if dest_path.exists() and dest_path.stat().st_size == total_size and not state_file.exists():
            print(f"[{model_id.upper()} CACHE] Complete checkpoint exists ({total_size:,} bytes). Verifying SHA-256...")
            actual_sha = self.compute_sha256(dest_path)
            if actual_sha == expected_sha256.lower():
                print(f"[{model_id.upper()} CACHE] SHA-256 verified from cache: {actual_sha}")
                return dest_path
            else:
                print(f"[{model_id.upper()} CACHE] Cache checksum mismatch. Initiating fresh parallel acquisition...")
                dest_path.unlink(missing_ok=True)

        # 2. Disk Space Pre-flight Check
        free_bytes = shutil.disk_usage(dest_path.parent).free
        existing_file_size = dest_path.stat().st_size if dest_path.exists() else 0
        needed_bytes = total_size - existing_file_size
        if free_bytes < needed_bytes + (100 * 1024 * 1024):
            raise IOError(
                f"Insufficient disk space. Needed: {needed_bytes / (1024**3):.2f} GB, "
                f"Available: {free_bytes / (1024**3):.2f} GB"
            )

        # 3. Partition into Chunks
        total_chunks = math.ceil(total_size / self.chunk_size_bytes)
        chunks: List[ChunkMetadata] = []
        for i in range(total_chunks):
            start = i * self.chunk_size_bytes
            end = min(total_size - 1, start + self.chunk_size_bytes - 1)
            chunks.append(ChunkMetadata(i, start, end))

        # 4. Initialize / Load State Ledger
        state = DownloadState.load_or_create(
            state_file=state_file,
            model_id=model_id,
            object_key=object_key,
            total_bytes=total_size,
            chunk_size=self.chunk_size_bytes,
            expected_sha256=expected_sha256
        )

        # Pre-allocate sparse target file
        self._preallocate_file(dest_path, total_size)

        # Filter pending chunks
        pending_chunks = [c for c in chunks if c.index not in state.completed_chunks]
        completed_initial = len(state.completed_chunks)

        if completed_initial > 0:
            bytes_already = sum(c.length for c in chunks if c.index in state.completed_chunks)
            print(f"[{model_id.upper()} RESUME] Resuming from saved state: {completed_initial}/{total_chunks} chunks ({bytes_already / (1024**3):.2f} GB already downloaded)")

        # 5. Background Telemetry Reporter
        stop_reporter = threading.Event()

        def telemetry_loop():
            while not stop_reporter.is_set():
                now = time.time()
                done_count = len(state.completed_chunks)
                done_bytes = sum(c.length for c in chunks if c.index in state.completed_chunks)
                pct = (done_bytes / max(1, total_size)) * 100
                speed = self.get_current_speed_mbps()
                rem_bytes = max(0, total_size - done_bytes)
                eta_s = (rem_bytes / (speed * 1024 * 1024)) if speed > 0 else 0.0

                stats = {
                    "model_id": model_id,
                    "completed_bytes": done_bytes,
                    "total_bytes": total_size,
                    "percent": pct,
                    "speed_mbps": speed,
                    "eta_seconds": eta_s,
                    "completed_chunks": done_count,
                    "total_chunks": total_chunks,
                    "active_workers": self.active_workers,
                    "retries": self.retry_count
                }

                if progress_callback:
                    try:
                        progress_callback(stats)
                    except Exception:
                        pass

                time.sleep(0.5)

        reporter_thread = threading.Thread(target=telemetry_loop, daemon=True)
        reporter_thread.start()

        # 6. Execute Parallel Pool
        current_url = download_url
        try:
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = {
                    executor.submit(
                        self._download_single_chunk,
                        chunk,
                        current_url,
                        dest_path,
                        state
                    ): chunk for chunk in pending_chunks
                }

                for fut in as_completed(futures):
                    if self.cancel_requested:
                        break
                    success = fut.result()
                    if not success:
                        chunk_failed = futures[fut]
                        raise IOError(f"Permanent download failure on chunk {chunk_failed.index}")

        finally:
            stop_reporter.set()
            reporter_thread.join(timeout=1.0)

        if self.cancel_requested:
            raise IOError("Download aborted by user request.")

        # 7. Verification Phase
        if len(state.completed_chunks) != total_chunks:
            raise IOError(f"Incomplete download: {len(state.completed_chunks)} of {total_chunks} chunks completed.")

        print(f"\n[{model_id.upper()} VERIFY] All {total_chunks} chunks assembled ({total_size:,} bytes). Validating SHA-256...")
        actual_sha = self.compute_sha256(
            dest_path,
            progress_callback=lambda p: sys.stdout.write(f"\r  Validating cryptographic integrity: [{p:5.1f}%] ")
        )
        sys.stdout.write("\n")

        if actual_sha != expected_sha256.lower():
            state.cleanup()
            dest_path.unlink(missing_ok=True)
            raise ValueError(
                f"SECURITY FAILURE: SHA-256 integrity check failed!\n"
                f"Expected: {expected_sha256}\n"
                f"Actual:   {actual_sha}\n"
                f"Corrupt assembly deleted."
            )

        # 8. Success: Clean up ledger
        state.cleanup()
        total_time = time.time() - start_time
        avg_speed = (total_size / (1024 * 1024)) / max(0.001, total_time)
        print(f"[{model_id.upper()} COMPLETE] SHA-256 verified: {actual_sha}")
        print(f"[{model_id.upper()} COMPLETE] Total time: {total_time:.1f}s | Average speed: {avg_speed:.2f} MB/s | Retries: {self.retry_count}")

        return dest_path
