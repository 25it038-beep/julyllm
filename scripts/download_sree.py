"""
HS AI SOLUTIONS — MODEL ACQUISITION & INTEGRATION: SREE LLM
Script: scripts/download_sree.py
Downloads VibeThinker-3B:Q4_K_M GGUF from HuggingFace,
verifies its integrity, computes SHA-256, and stores in models/sree/model.gguf.
"""

import os
import sys
import time
import hashlib
import urllib.request
from pathlib import Path

MODEL_URL = "https://huggingface.co/mradermacher/VibeThinker-3B-GGUF/resolve/main/VibeThinker-3B.Q4_K_M.gguf"
TARGET_DIR = Path("models/sree")
TARGET_FILE = TARGET_DIR / "model.gguf"
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB chunks


def download_model():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = TARGET_DIR / "model.gguf.tmp"

    print("=" * 70)
    print("HS AI SOLUTIONS — ACQUIRING VIBETHINKER-3B:Q4_K_M -> SREE LLM")
    print(f"Source URL : {MODEL_URL}")
    print(f"Target Path: {TARGET_FILE.resolve()}")
    print("=" * 70)

    # Check if existing completed file exists
    if TARGET_FILE.exists() and TARGET_FILE.stat().st_size == 1929903232:
        print(f" [✓] Model already downloaded ({TARGET_FILE.stat().st_size} bytes). Computing SHA-256...")
        h = hashlib.sha256()
        with open(TARGET_FILE, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                h.update(chunk)
        sha = h.hexdigest()
        print(f" [✓] SHA-256: {sha}")
        return sha, TARGET_FILE.stat().st_size

    # Resume support or fresh download
    downloaded = 0
    headers = {"User-Agent": "HS-AI-Solutions/JulyLLM"}
    mode = "wb"

    if tmp_file.exists():
        downloaded = tmp_file.stat().st_size
        if downloaded > 0:
            headers["Range"] = f"bytes={downloaded}-"
            mode = "ab"
            print(f" [*] Resuming from byte {downloaded} ({downloaded / (1024*1024):.1f} MB)...")

    req = urllib.request.Request(MODEL_URL, headers=headers)
    t0 = time.time()
    last_log = t0

    h = hashlib.sha256()
    # If resuming, pre-hash existing
    if downloaded > 0:
        print(" [*] Pre-hashing resumed content...")
        with open(tmp_file, "rb") as fp:
            while chunk := fp.read(CHUNK_SIZE):
                h.update(chunk)

    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_file, mode) as fp:
        total_len = int(resp.headers.get("Content-Length", 0))
        if mode == "ab":
            total_size = downloaded + total_len
        else:
            total_size = total_len or 1929903232

        current_bytes = downloaded
        while True:
            chunk = resp.read(CHUNK_SIZE)
            if not chunk:
                break
            fp.write(chunk)
            h.update(chunk)
            current_bytes += len(chunk)

            now = time.time()
            if now - last_log >= 3.0 or current_bytes == total_size:
                elapsed = max(0.1, now - t0)
                speed_mb = (current_bytes - downloaded) / (1024 * 1024) / elapsed
                percent = (current_bytes / total_size) * 100 if total_size else 0
                print(f" [*] Progress: {current_bytes / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB ({percent:.1f}%) | Speed: {speed_mb:.2f} MB/s")
                last_log = now

    # Atomic move
    tmp_file.replace(TARGET_FILE)
    sha = h.hexdigest()
    final_size = TARGET_FILE.stat().st_size
    print("=" * 70)
    print(f" [✓] DOWNLOAD COMPLETE: {TARGET_FILE}")
    print(f" [✓] Size   : {final_size} bytes ({final_size / (1024*1024):.2f} MB)")
    print(f" [✓] SHA-256: {sha}")
    print("=" * 70)
    return sha, final_size


if __name__ == "__main__":
    download_model()
