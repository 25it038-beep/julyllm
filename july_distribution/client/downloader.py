"""
HS AI SOLUTIONS â€” JULY CLIENT RESUMABLE RETRIEVAL
Layer: RETRIEVAL & INTEGRITY (july_distribution.client.downloader)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Performs authenticated model acquisition:
- Requests short-lived presigned URL from control server.
- Resumable chunked downloading directly from Cloudflare R2 via HTTP Range requests.
- SHA-256 cryptographic verification against server manifest.
"""

from __future__ import annotations
import os
import sys
import time
import hashlib
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from .config import ClientConfig
from .auth import ClientAuthManager


class ClientModelDownloader:
    """Manages secure presigned retrieval and verification."""

    def __init__(self, config: Optional[ClientConfig] = None, auth: Optional[ClientAuthManager] = None):
        self.config = config or ClientConfig.load()
        self.auth = auth or ClientAuthManager(self.config)

    def request_presigned_download(self) -> Dict[str, Any]:
        """Requests authorization and short-lived presigned URL from Central Server."""
        token = self.auth.get_token()
        if not token:
            raise PermissionError("Not authenticated. Please run 'july login' first.")

        session = self.auth.get_session() or {}
        device_id = session.get("device_id")
        if not device_id:
            from .hardware import get_device_identity
            device_id = get_device_identity()["device_id"]

        server_url = self.config.server_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Device-Id": device_id
        }

        req = urllib.request.Request(
            f"{server_url}/api/v1/model/request-download",
            headers=headers,
            data=b""
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_msg)
                raise PermissionError(err_json.get("detail", str(e)))
            except Exception:
                raise PermissionError(f"Download authorization rejected (HTTP {e.code}): {err_msg}")
        except Exception as e:
            raise ConnectionError(f"Failed to communicate with control server: {e}")

    @staticmethod
    def compute_sha256(file_path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    def download_to_ephemeral_storage(
        self,
        dest_path: Path,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> Path:
        """
        Retrieves the GGUF model into ephemeral RAM-backed storage with resumability.
        """
        # Step 1: Request presigned download authorization
        info = self.request_presigned_download()
        download_url = info["download_url"]
        expected_size = info["size_bytes"]
        expected_sha = info["expected_sha256"].lower()
        chunk_size = self.config.chunk_size_bytes

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        existing_bytes = dest_path.stat().st_size if dest_path.exists() else 0

        # Check existing byte length
        if existing_bytes == expected_size:
            print(f"[JULY CLIENT] Ephemeral file already complete ({existing_bytes:,} bytes). Verifying SHA-256...")
            actual_sha = self.compute_sha256(dest_path, chunk_size)
            if actual_sha == expected_sha:
                print(f"[JULY CLIENT] SHA-256 verified successfully: {actual_sha}")
                return dest_path
            else:
                dest_path.unlink()
                existing_bytes = 0
        elif existing_bytes > expected_size:
            dest_path.unlink()
            existing_bytes = 0

        headers = {}
        mode = "wb"
        if existing_bytes > 0:
            headers["Range"] = f"bytes={existing_bytes}-{expected_size - 1}"
            mode = "ab"
            print(f"[JULY CLIENT] Resuming download from offset: {existing_bytes:,} / {expected_size:,}")

        # Stream directly from Cloudflare R2
        start_time = time.time()
        bytes_received = existing_bytes
        req = urllib.request.Request(download_url, headers=headers)

        with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, mode) as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                bytes_received += len(chunk)
                elapsed = max(0.001, time.time() - start_time)
                speed_mb = (bytes_received - existing_bytes) / (1024 * 1024 * elapsed)
                if progress_callback:
                    progress_callback(bytes_received, expected_size, speed_mb)

        # Integrity Check
        print("\n[JULY CLIENT] Verifying SHA-256 cryptographic integrity...")
        actual_sha = self.compute_sha256(dest_path, chunk_size)
        if actual_sha != expected_sha:
            dest_path.unlink(missing_ok=True)
            raise ValueError(
                f"SECURITY FAILURE: SHA-256 integrity check failed!\n"
                f"Expected: {expected_sha}\n"
                f"Actual:   {actual_sha}\n"
                f"Corrupt temporary file destroyed."
            )

        print(f"[JULY CLIENT] Integrity verified: {actual_sha}")
        return dest_path

