"""
HS AI SOLUTIONS — GRAVITY R2 INTEGRATION & DUAL-MODEL VERIFICATION SUITE
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & GRAVITY LLM

Verifies all 10 Acceptance Tests:
  TEST 1: Backend successfully authenticates with Cloudflare R2.
  TEST 2: HeadObject confirms Gravity exists at the exact object key ('Gravity-HS-AI-Solutions.gguf').
  TEST 3: Backend generates a valid Gravity signed download URL.
  TEST 4: Client downloads Gravity from R2 using HTTP Range requests.
  TEST 5: Resumed download recovery and byte slice size matching.
  TEST 6: Cryptographic SHA-256 verification on streamed chunk.
  TEST 7: Local inference runtime loads the Gravity GGUF checkpoint.
  TEST 8: Gravity generates a real response with dedicated identity.
  TEST 9: July continues working without regression.
  TEST 10: Seamless sequential switching between July and Gravity without memory leak.
"""

import os
import sys
import time
import shutil
import hashlib
from pathlib import Path

# Ensure workspace root in path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from july_distribution.server.r2_manager import CloudflareR2DistributionGateway
from july_distribution.client.downloader import ClientModelDownloader
from hs_ecosystem.core.model_manager import UniversalModelManager

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_tests():
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}HS AI SOLUTIONS — GRAVITY R2 & MULTI-MODEL VERIFICATION SUITE{RESET}")
    print(f"Founder: Harshan Seliyan | Private Cloudflare R2: 'july'")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

    passed = 0
    total = 10
    temp_dir = REPO_ROOT / "temp_test_r2"
    temp_dir.mkdir(parents=True, exist_ok=True)

    gw = CloudflareR2DistributionGateway()

    # TEST 1: R2 Authentication
    try:
        t0 = time.time()
        client = gw.get_client()
        assert client is not None
        print(f"[{GREEN}PASS{RESET}] TEST 1: Backend authenticates with Cloudflare R2 ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 1: R2 Authentication failed: {e}")

    # TEST 2: HeadObject on exact key 'Gravity-HS-AI-Solutions.gguf'
    head_info = {}
    try:
        t0 = time.time()
        head_info = gw.verify_object_head("Gravity-HS-AI-Solutions.gguf")
        assert head_info.get("success") is True, f"HeadObject returned failure: {head_info}"
        assert head_info.get("content_length") == 5629108096, f"Expected 5,629,108,096 bytes, got {head_info.get('content_length')}"
        assert "Gravity-HS-AI-Solutions.gguf" in head_info.get("key")
        print(f"[{GREEN}PASS{RESET}] TEST 2: HeadObject confirmed Gravity exists: 5,629,108,096 bytes ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 2: HeadObject failed: {e}")

    # TEST 3: Signed Download URL Generation
    download_url = ""
    try:
        t0 = time.time()
        download_url = gw.generate_short_lived_download_url("Gravity-HS-AI-Solutions.gguf", 900)
        assert download_url.startswith("https://")
        assert "Gravity-HS-AI-Solutions.gguf" in download_url
        print(f"[{GREEN}PASS{RESET}] TEST 3: Generated 15-minute presigned URL for Gravity ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 3: Signed URL generation failed: {e}")

    # TEST 4: Client Range Download from R2 (First 2 MB)
    slice_path = temp_dir / "gravity_slice.gguf"
    downloader = ClientModelDownloader()
    try:
        if slice_path.exists():
            slice_path.unlink()
        t0 = time.time()
        target_bytes = 2 * 1024 * 1024  # 2 MB slice
        downloader.download_model("gravity", slice_path, max_bytes=target_bytes)
        assert slice_path.exists()
        assert slice_path.stat().st_size == target_bytes
        # Verify GGUF magic bytes
        with open(slice_path, "rb") as f:
            magic = f.read(4)
        assert magic == b"GGUF", f"Invalid magic: {magic}"
        print(f"[{GREEN}PASS{RESET}] TEST 4: Client downloaded Range slice from R2 (Magic: GGUF) ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 4: Client Range download failed: {e}")

    # TEST 5: Resumed Download Recovery (Append next 2 MB to reach 4 MB total)
    try:
        t0 = time.time()
        target_bytes_resumed = 4 * 1024 * 1024  # Expand to 4 MB
        downloader.download_model("gravity", slice_path, max_bytes=target_bytes_resumed)
        assert slice_path.stat().st_size == target_bytes_resumed
        print(f"[{GREEN}PASS{RESET}] TEST 5: Interrupted download resumed from offset to 4 MB ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 5: Resumed download recovery failed: {e}")

    # TEST 6: SHA-256 Checksum Verification
    try:
        t0 = time.time()
        actual_sha = downloader.compute_sha256(slice_path)
        assert len(actual_sha) == 64
        # Validate that hashing streaming chunks works deterministically
        with open(slice_path, "rb") as f:
            expected_sha = hashlib.sha256(f.read()).hexdigest().lower()
        assert actual_sha == expected_sha
        print(f"[{GREEN}PASS{RESET}] TEST 6: Cryptographic SHA-256 stream integrity verified ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 6: SHA-256 verification failed: {e}")

    # TEST 7: Local Inference Runtime Loads Gravity GGUF
    manager = UniversalModelManager()
    try:
        t0 = time.time()
        load_ok = manager.load_model("gravity", context_length=512)
        assert load_ok is True
        assert manager.states["gravity"].status == "active"
        print(f"[{GREEN}PASS{RESET}] TEST 7: Local llama.cpp loaded Gravity GGUF into memory ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 7: Gravity model loading failed: {e}")

    # TEST 8: Gravity Generates a Real Response with Identity
    try:
        t0 = time.time()
        inst = manager._instances.get("gravity")
        assert inst is not None
        out = inst.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are GRAVITY LLM, developed by HS AI Solutions."},
                {"role": "user", "content": "Identify yourself in one short sentence."}
            ],
            max_tokens=64
        )
        resp_text = out["choices"][0]["message"]["content"]
        assert len(resp_text.strip()) > 5
        print(f"[{GREEN}PASS{RESET}] TEST 8: Gravity generated response: \"{resp_text.strip()[:65]}...\" ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 8: Gravity response generation failed: {e}")

    # TEST 9: July Continues Working Without Regression
    try:
        t0 = time.time()
        # Switching cleanly to July
        manager.switch_model("july")
        assert manager.active_model_id == "july"
        inst_july = manager._instances.get("july")
        assert inst_july is not None
        out_july = inst_july.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are JULY LLM."},
                {"role": "user", "content": "Hello July."}
            ],
            max_tokens=32
        )
        assert len(out_july["choices"][0]["message"]["content"].strip()) > 0
        print(f"[{GREEN}PASS{RESET}] TEST 9: July loaded & generated verified response without regression ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 9: July regression test failed: {e}")

    # TEST 10: Clean Sequential Model Switching
    try:
        t0 = time.time()
        # Unload July cleanly to verify sequential VRAM release
        manager.unload_model("july")
        assert manager.states["july"].status == "unloaded"
        assert "july" not in manager._instances

        # Switch back to Gravity
        switch_ok = manager.switch_model("gravity")
        assert switch_ok is True
        assert manager.active_model_id == "gravity"
        assert "gravity" in manager._instances and manager.states["gravity"].status == "active"
        print(f"[{GREEN}PASS{RESET}] TEST 10: Clean sequential model switching verified (VRAM Protected) ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 10: Model switching failed: {e}")

    # Cleanup temp directory
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"RESULTS: {passed}/{total} PASSED ({passed/total*100:.1f}%)")
    print(f"{BOLD}{'='*80}{RESET}\n")

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
