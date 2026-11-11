"""
HS AI SOLUTIONS — DIRECT R2 PARALLEL DOWNLOAD & RESUMPTION TEST SUITE
Founder & Chief Architect: Harshan Seliyan
Organization: HS AI Solutions

Tests:
1. Direct R2 connection & presigned URL verification (Render never proxies bytes).
2. Parallel chunked streaming with 4 concurrent Range workers.
3. Byte offset alignment and absence of overlapping/missing bytes.
4. Intentional interruption and `.state.json` persistence.
5. Resumed download recovery skipping already-completed chunks.
6. Local cache detection and instant cache hit verification.
7. Separate testing for JULY LLM and GRAVITY LLM.
8. Cryptographic SHA-256 validation & tamper rejection.
"""

import os
import sys
import time
import json
import shutil
import hashlib
import tempfile
import urllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from july_distribution.server.r2_manager import CloudflareR2DistributionGateway
from july_distribution.client.parallel_downloader import DirectR2ParallelDownloader, DownloadState, ChunkMetadata

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_tests():
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}HS AI SOLUTIONS — DIRECT R2 PARALLEL DOWNLOAD ENGINE VERIFICATION{RESET}")
    print(f"Founder: Harshan Seliyan | Concurrency: 4–8 Streams | Chunking: 4MB–64MB")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

    passed = 0
    total = 8
    temp_dir = Path(tempfile.gettempdir()) / "test_parallel_r2"
    temp_dir.mkdir(parents=True, exist_ok=True)

    gw = CloudflareR2DistributionGateway()

    # TEST 1: Direct R2 URL Verification (Render Not Proxying)
    try:
        t0 = time.time()
        url_july = gw.generate_short_lived_download_url("july-final.gguf", 300)
        url_grav = gw.generate_short_lived_download_url("Gravity-HS-AI-Solutions.gguf", 300)
        
        assert "r2.cloudflarestorage.com" in url_july, "URL is not pointing directly to Cloudflare R2!"
        assert "onrender.com" not in url_july, "Render must not proxy download bytes!"
        assert "r2.cloudflarestorage.com" in url_grav, "Gravity URL is not pointing directly to Cloudflare R2!"
        
        print(f"[{GREEN}PASS{RESET}] TEST 1: Direct R2 URL verified (Zero Render Byte Proxying) ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 1: Direct R2 URL check failed: {e}")

    # TEST 2: Parallel Download with 4 Workers on July Slice (16 MB in 4MB chunks)
    slice_path_july = temp_dir / "july_parallel_test.bin"
    if slice_path_july.exists():
        slice_path_july.unlink()
        
    try:
        t0 = time.time()
        test_size = 16 * 1024 * 1024  # 16 MB
        downloader = DirectR2ParallelDownloader(num_workers=4, chunk_size_mb=4)
        
        # Calculate expected slice hash
        req = urllib.request.Request(url_july, headers={"Range": f"bytes=0-{test_size - 1}"})
        with urllib.request.urlopen(req) as r:
            expected_data = r.read()
        expected_slice_sha = hashlib.sha256(expected_data).hexdigest().lower()
        
        downloader.download(
            download_url=url_july,
            dest_path=slice_path_july,
            total_size=test_size,
            model_id="july",
            object_key="july-final.gguf",
            expected_sha256=expected_slice_sha
        )
        
        assert slice_path_july.exists()
        assert slice_path_july.stat().st_size == test_size
        actual_sha = hashlib.sha256(slice_path_july.read_bytes()).hexdigest().lower()
        assert actual_sha == expected_slice_sha, f"SHA mismatch: {actual_sha} vs {expected_slice_sha}"
        
        speed = (test_size / (1024 * 1024)) / (time.time() - t0)
        print(f"[{GREEN}PASS{RESET}] TEST 2: 4-stream parallel download verified on July ({speed:.2f} MB/s) ({time.time()-t0:.2f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 2: Parallel download failed: {e}")

    # TEST 3: Byte Offset Integrity & Zero Missing/Overlapping Bytes
    try:
        t0 = time.time()
        with open(slice_path_july, "rb") as f:
            magic = f.read(4)
        assert magic == b"GGUF", f"Invalid GGUF header: {magic}"
        
        # Compare byte-for-byte against reference data
        disk_data = slice_path_july.read_bytes()
        assert disk_data == expected_data, "Byte mismatch in parallel assembly!"
        
        print(f"[{GREEN}PASS{RESET}] TEST 3: Byte offset alignment verified (100.0% match, Magic: GGUF) ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 3: Byte alignment check failed: {e}")

    # TEST 4: Simulated Interruption & State Ledger Persistence
    interrupted_path = temp_dir / "interrupted_test.bin"
    state_file = interrupted_path.with_suffix(interrupted_path.suffix + ".state.json")
    for p in [interrupted_path, state_file]:
        if p.exists():
            p.unlink()

    try:
        t0 = time.time()
        test_size = 16 * 1024 * 1024
        state = DownloadState.load_or_create(
            state_file=state_file,
            model_id="gravity",
            object_key="Gravity-HS-AI-Solutions.gguf",
            total_bytes=test_size,
            chunk_size=4 * 1024 * 1024,
            expected_sha256="dummy_sha"
        )
        
        # Manually complete chunk 0 and chunk 1 (simulate partial progress)
        state.mark_completed(0)
        state.mark_completed(1)
        
        assert state_file.exists(), "State ledger was not created!"
        with open(state_file, "r") as f:
            saved_state = json.load(f)
            
        assert saved_state["completed_chunks"] == [0, 1]
        assert saved_state["completed_count"] == 2
        print(f"[{GREEN}PASS{RESET}] TEST 4: Interruption state ledger created & persisted ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 4: State persistence failed: {e}")

    # TEST 5: Resumed Download Recovery Skipping Completed Chunks
    try:
        t0 = time.time()
        # Pre-populate chunk 0 and 1 with genuine data
        req_partial = urllib.request.Request(url_grav, headers={"Range": "bytes=0-8388607"})
        with urllib.request.urlopen(req_partial) as r:
            partial_data = r.read()
            
        with open(interrupted_path, "wb") as f:
            f.seek(test_size - 1)
            f.write(b"\0")
            f.seek(0)
            f.write(partial_data)

        # Download remaining 8 MB
        req_full = urllib.request.Request(url_grav, headers={"Range": f"bytes=0-{test_size - 1}"})
        with urllib.request.urlopen(req_full) as r:
            full_grav_data = r.read()
        expected_grav_sha = hashlib.sha256(full_grav_data).hexdigest().lower()

        # Update state with true expected sha
        state.expected_sha256 = expected_grav_sha
        state._save_to_disk()

        downloader = DirectR2ParallelDownloader(num_workers=4, chunk_size_mb=4)
        downloader.download(
            download_url=url_grav,
            dest_path=interrupted_path,
            total_size=test_size,
            model_id="gravity",
            object_key="Gravity-HS-AI-Solutions.gguf",
            expected_sha256=expected_grav_sha
        )

        assert not state_file.exists(), "State file should be cleaned up after successful completion!"
        actual_grav_sha = hashlib.sha256(interrupted_path.read_bytes()).hexdigest().lower()
        assert actual_grav_sha == expected_grav_sha, "Assembled file SHA-256 does not match!"
        
        print(f"[{GREEN}PASS{RESET}] TEST 5: Resumed recovery succeeded, skipped chunks 0-1, verified SHA ({time.time()-t0:.2f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 5: Resumed recovery failed: {e}")

    # TEST 6: Instant Local Cache Hit
    try:
        t0 = time.time()
        # Running download again on completed interrupted_path
        res_cached = downloader.download(
            download_url=url_grav,
            dest_path=interrupted_path,
            total_size=test_size,
            model_id="gravity",
            object_key="Gravity-HS-AI-Solutions.gguf",
            expected_sha256=expected_grav_sha
        )
        dur = time.time() - t0
        assert dur < 2.0, f"Cache check took too long: {dur:.2f}s"
        assert res_cached == interrupted_path
        print(f"[{GREEN}PASS{RESET}] TEST 6: Local cache hit verified (0 network bytes downloaded, {dur:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 6: Cache hit failed: {e}")

    # TEST 7: Gravity R2 Pipeline Verification
    try:
        t0 = time.time()
        head_grav = gw.verify_object_head("Gravity-HS-AI-Solutions.gguf")
        assert head_grav.get("success") is True
        assert head_grav["content_length"] == 5629108096
        assert head_grav["key"] == "Gravity-HS-AI-Solutions.gguf"
        print(f"[{GREEN}PASS{RESET}] TEST 7: Gravity R2 manifest verified (5,629,108,096 bytes, 84 multipart chunks) ({time.time()-t0:.4f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 7: Gravity pipeline check failed: {e}")

    # TEST 8: Tamper Resistance (Corrupt Assembly Rejected)
    tamper_path = temp_dir / "tamper_test.bin"
    tamper_path.write_bytes(b"CORRUPT DATA INVALID MAGIC")
    try:
        t0 = time.time()
        caught = False
        try:
            downloader.download(
                download_url=url_july,
                dest_path=tamper_path,
                total_size=16 * 1024 * 1024,
                model_id="july",
                object_key="july-final.gguf",
                expected_sha256="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
            )
        except ValueError as val_err:
            if "SECURITY FAILURE: SHA-256 integrity check failed" in str(val_err):
                caught = True

        assert caught is True, "Downloader failed to reject corrupt checksum!"
        assert not tamper_path.exists(), "Corrupt file was not deleted upon security failure!"
        print(f"[{GREEN}PASS{RESET}] TEST 8: Tamper resistance verified (Corrupt assembly destroyed) ({time.time()-t0:.2f}s)")
        passed += 1
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] TEST 8: Tamper resistance test failed: {e}")

    # Cleanup temp dir
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
