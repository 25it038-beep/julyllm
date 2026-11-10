"""
HS AI SOLUTIONS - STANDALONE MODEL DOWNLOADER & VERIFIER
Atomic Synchronization from Hugging Face Hub
Founder: Harshan Seliyan
"""

import os
import sys
import shutil
import hashlib
from huggingface_hub import hf_hub_download

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.gguf_inspector import inspect_gguf_file


def calculate_sha256(file_path: str) -> str:
    print(f"[VERIFY] Computing SHA-256 checksum for {file_path}...")
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(16 * 1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest().lower()


def download_model(
    repo_id: str,
    filename: str,
    destination: str,
    token: str = None,
    expected_sha256: str = None,
    expected_size: int = None
) -> str:
    print("==================================================")
    print("    HS AI SOLUTIONS - JULY MODEL DOWNLOADER       ")
    print(f"    Repository:  {repo_id}")
    print(f"    File:        {filename}")
    print(f"    Destination: {destination}")
    print("==================================================")

    target_dir = os.path.dirname(os.path.abspath(destination))
    os.makedirs(target_dir, exist_ok=True)

    # Check if already present and valid
    if os.path.exists(destination):
        actual_size = os.path.getsize(destination)
        print(f"[CACHE] Found existing file at destination ({round(actual_size / 1e6, 2)} MB).")

        size_ok = True if not expected_size else (actual_size == expected_size)
        sha_ok = True
        if expected_sha256:
            sha_ok = (calculate_sha256(destination) == expected_sha256.lower())

        if size_ok and sha_ok and actual_size > 50 * 1024 * 1024:
            print("[CACHE] File matches integrity requirements. Skipping download.")
            return destination
        else:
            print("[CACHE] Existing file corrupted or incomplete. Proceeding with fresh download...")

    print(f"[DOWNLOAD] Downloading from Hugging Face Hub...")
    try:
        temp_cache = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            token=token,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            resume_download=True
        )

        # Atomic rename to target destination
        if temp_cache != destination:
            shutil.move(temp_cache, destination)

        print(f"[DOWNLOAD] File saved to {destination}")

        # Check integrity
        actual_size = os.path.getsize(destination)
        if expected_size and actual_size != expected_size:
            raise ValueError(f"Size verification failed: expected {expected_size}, got {actual_size}")

        if expected_sha256:
            checksum = calculate_sha256(destination)
            if checksum != expected_sha256.lower():
                raise ValueError(f"Checksum verification failed: expected {expected_sha256}, got {checksum}")

        # Inspect GGUF header
        print("[VERIFY] Validating GGUF header structure...")
        info = inspect_gguf_file(destination)
        print(f"[VERIFY] Verified {info.get('architecture')} model, Quantization: {info.get('quantization')}")
        print("[SUCCESS] Model is ready for inference deployment!")
        return destination

    except Exception as e:
        print(f"[ERROR] Model download/verification failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    repo = os.getenv("MODEL_REPO", settings.MODEL_REPO)
    filename = os.getenv("MODEL_FILENAME", settings.MODEL_FILENAME)
    dest = os.getenv("MODEL_PATH", settings.MODEL_PATH)
    token = os.getenv("HF_TOKEN", settings.HF_TOKEN)
    exp_sha = os.getenv("EXPECTED_SHA256", settings.EXPECTED_SHA256)
    exp_size = int(os.getenv("EXPECTED_SIZE", "0")) or settings.EXPECTED_SIZE

    download_model(
        repo_id=repo,
        filename=filename,
        destination=dest,
        token=token,
        expected_sha256=exp_sha,
        expected_size=exp_size
    )
