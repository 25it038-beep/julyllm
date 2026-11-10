"""
HS AI SOLUTIONS — JULY CLOUDFLARE R2 CONNECTION & DIAGNOSTIC TEST
Product: JULY LLM | Family: HS AI FAMILY
Founder & Chief Architect: Harshan Seliyan
Script: scripts/test_r2_connection.py

Verifies:
1. Non-secret configuration loading.
2. Secure S3-compatible authentication with Cloudflare R2.
3. HeadObject verification on s3://july/july-final.gguf.
4. Exact byte length confirmation (2,019,377,888 bytes).
5. S3 Range request for GGUF magic bytes (bytes=0-1023).
6. Short-lived presigned URL generation.
7. Zero-credential HTTP Range verification.
"""

from __future__ import annotations
import sys
import time
import urllib.request
from pathlib import Path

# Setup path
ROOT = Path(__file__).resolve().parent.parent
HS_AI = ROOT / "HS-JULY-AI"
if str(HS_AI) not in sys.path:
    sys.path.insert(0, str(HS_AI))

from july_r2 import JulyR2Config, JulyR2AuthManager, ResumableR2Downloader

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def run_diagnostics():
    print("=" * 80)
    print("      JULY: CLOUDFLARE R2 INTEGRATION & CONNECTION DIAGNOSTIC")
    print("                         HS AI SOLUTIONS")
    print("                  Founder: Harshan Seliyan")
    print("=" * 80)

    cfg = JulyR2Config.load()
    print(f"\n[1. CONFIGURATION]")
    print(f"  Provider:       {cfg.provider}")
    print(f"  Endpoint URL:   {cfg.endpoint_url}")
    print(f"  Bucket:         {cfg.bucket_name}")
    print(f"  Object Key:     {cfg.object_key}")
    print(f"  Expected Size:  {cfg.expected_size_bytes:,} bytes (~{cfg.expected_size_bytes / (1024**3):.2f} GB)")
    print(f"  Expected Hash:  {cfg.expected_sha256}")
    print(f"  AWS Profile:    {cfg.aws_profile}")

    auth = JulyR2AuthManager(cfg)

    print(f"\n[2. HEADOBJECT REMOTE VERIFICATION]")
    t0 = time.time()
    head_res = auth.test_connection()
    t_head = time.time() - t0

    if not head_res.get("success"):
        print(f"  [!] FAILED: {head_res.get('error_message')}")
        sys.exit(1)

    print(f"  [+] HeadObject retrieved successfully in {t_head*1000:.1f}ms")
    print(f"  [+] Remote ContentLength: {head_res.get('content_length'):,} bytes")
    print(f"  [+] ETag:                 \"{head_res.get('etag')}\"")
    print(f"  [+] Last Modified:        {head_res.get('last_modified')}")
    print(f"  [+] Size Match:           {'VERIFIED' if head_res.get('matches_expected_size') else 'MISMATCH'}")

    assert head_res.get("matches_expected_size"), "Remote size does not match expected size!"

    print(f"\n[3. S3 RANGE REQUEST VERIFICATION]")
    client = auth.get_s3_client()
    t0 = time.time()
    range_resp = client.get_object(
        Bucket=cfg.bucket_name,
        Key=cfg.object_key,
        Range="bytes=0-1023"
    )
    data = range_resp["Body"].read()
    t_range = time.time() - t0

    print(f"  [+] S3 Range request (bytes=0-1023) received {len(data)} bytes in {t_range*1000:.1f}ms")
    print(f"  [+] HTTP Status:          {range_resp['ResponseMetadata']['HTTPStatusCode']}")
    print(f"  [+] ContentRange:         {range_resp.get('ContentRange')}")
    magic = data[:4]
    print(f"  [+] Header Magic Bytes:   {magic} ({'VALID GGUF' if magic == b'GGUF' else 'INVALID'})")
    assert magic == b"GGUF", f"Expected b'GGUF', got {magic}"

    print(f"\n[4. PRESIGNED DOWNLOAD URL GENERATION]")
    url = auth.generate_presigned_download_url(expires_in_seconds=900)
    print(f"  [+] Short-lived URL issued (expires in 900s):")
    print(f"      {url[:90]}...[truncated for security]")

    print(f"\n[5. ZERO-CREDENTIAL HTTP CLIENT RANGE RETRIEVAL]")
    t0 = time.time()
    req = urllib.request.Request(url, headers={"Range": "bytes=0-15"})
    with urllib.request.urlopen(req) as resp:
        http_data = resp.read()
        t_http = time.time() - t0
        print(f"  [+] HTTP Status Code:     {resp.status} (Partial Content)")
        print(f"  [+] Bytes Read:           {len(http_data)}")
        print(f"  [+] Header Magic:         {http_data[:4]}")
        print(f"  [+] Latency:              {t_http*1000:.1f}ms")
        assert http_data[:4] == b"GGUF"

    print("\n" + "=" * 80)
    print("  ALL CLOUDFLARE R2 CONNECTION & INTEGRITY TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_diagnostics()
