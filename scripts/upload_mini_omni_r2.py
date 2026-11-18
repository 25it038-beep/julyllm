"""
HS AI SOLUTIONS — UPLOAD MINI-OMNI TO CLOUDFLARE R2
Script: scripts/upload_mini_omni_r2.py
Founder & Chief Architect: Harshan Seliyan
Product: MINI-OMNI (Real-Time Conversational Voice Intelligence)
Bucket: july | Object Key: mini-omni-final.gguf
"""

import os
import sys
import time
from pathlib import Path
import boto3
from botocore.config import Config
from boto3.s3.transfer import TransferConfig

ENDPOINT_URL = "https://21e5f9f23e1d60cb56bf1200e89255f3.r2.cloudflarestorage.com"
BUCKET_NAME = "july"
OBJECT_KEY = "mini-omni-final.gguf"
LOCAL_FILE = Path("models/mini-omni/model.gguf")
EXPECTED_SIZE = 2019377888
EXPECTED_SHA = "f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4"


def main():
    print("=" * 75)
    print("      HS AI SOLUTIONS — CLOUDFLARE R2 STORAGE UPLOAD: MINI-OMNI")
    print("=" * 75)

    if not LOCAL_FILE.exists():
        print(f" [!] Error: Local model file not found: {LOCAL_FILE}")
        sys.exit(1)

    actual_size = LOCAL_FILE.stat().st_size
    print(f" Local Model File: {LOCAL_FILE.resolve()}")
    print(f" File Size       : {actual_size:,} bytes ({actual_size / (1024**3):.2f} GiB)")
    print(f" Target Bucket   : {BUCKET_NAME}")
    print(f" Target Key      : {OBJECT_KEY}")
    print(f" Endpoint        : {ENDPOINT_URL}")
    print("-" * 75)

    if actual_size != EXPECTED_SIZE:
        print(f" [!] Warning: File size {actual_size} differs from expected {EXPECTED_SIZE}")

    session = boto3.Session(profile_name="july-r2")
    cfg = Config(
        signature_version="s3v4",
        retries={"max_attempts": 10, "mode": "adaptive"},
        connect_timeout=60,
        read_timeout=300,
    )
    s3 = session.client("s3", endpoint_url=ENDPOINT_URL, config=cfg)

    # Transfer configuration optimized for resilient upload across variable broadband
    transfer_config = TransferConfig(
        multipart_threshold=16 * 1024 * 1024,   # 16 MB
        max_concurrency=4,                      # 4 concurrent parts to prevent bandwidth starvation
        multipart_chunksize=8 * 1024 * 1024,    # 8 MB chunks for fast per-part completion & timeout resilience
        use_threads=True,
    )

    t0 = time.time()
    last_print = t0
    uploaded_bytes = 0

    def progress_callback(bytes_amount):
        nonlocal uploaded_bytes, last_print
        uploaded_bytes += bytes_amount
        now = time.time()
        if now - last_print >= 2.0 or uploaded_bytes >= actual_size:
            elapsed = max(0.1, now - t0)
            speed_mb = (uploaded_bytes / (1024 * 1024)) / elapsed
            pct = (uploaded_bytes / actual_size) * 100
            remaining_bytes = max(0, actual_size - uploaded_bytes)
            eta_sec = int(remaining_bytes / (speed_mb * 1024 * 1024)) if speed_mb > 0 else 0
            eta_str = f"{eta_sec // 60:02d}m{eta_sec % 60:02d}s"
            up_mb = uploaded_bytes / (1024 * 1024)
            tot_mb = actual_size / (1024 * 1024)
            sys.stdout.write(
                f"\r [R2 UPLOAD] [{pct:5.1f}%] {up_mb:7.1f} / {tot_mb:7.1f} MB | "
                f"Speed: {speed_mb:5.2f} MB/s | ETA: {eta_str}   "
            )
            sys.stdout.flush()
            last_print = now

    max_retries = 3
    success = False
    for attempt in range(1, max_retries + 1):
        t0 = time.time()
        last_print = t0
        uploaded_bytes = 0
        print(f" [*] Upload attempt {attempt}/{max_retries}: Uploading {OBJECT_KEY} to Cloudflare R2 bucket '{BUCKET_NAME}'...")
        try:
            s3.upload_file(
                Filename=str(LOCAL_FILE),
                Bucket=BUCKET_NAME,
                Key=OBJECT_KEY,
                Config=transfer_config,
                Callback=progress_callback,
                ExtraArgs={
                    "ContentType": "application/octet-stream",
                    "Metadata": {
                        "model_id": "mini-omni",
                        "model_name": "MINI-OMNI",
                        "organization": "HS AI Solutions",
                        "founder": "Harshan Seliyan",
                        "sha256": EXPECTED_SHA,
                    },
                },
            )
            sys.stdout.write("\n")
            success = True
            break
        except Exception as e:
            sys.stdout.write("\n")
            print(f" [!] Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait_sec = 5 * attempt
                print(f" [*] Retrying in {wait_sec} seconds...")
                time.sleep(wait_sec)

    if not success:
        print(f" [!] Upload failed after {max_retries} attempts.")
        sys.exit(1)

    total_time = time.time() - t0
    avg_speed = (actual_size / (1024 * 1024)) / total_time
    print(f" [✓] UPLOAD COMPLETE in {total_time:.1f}s (Average Speed: {avg_speed:.2f} MB/s)")

    # Post-upload verification
    print("\n" + "=" * 75)
    print(" [VERIFICATION] Verifying uploaded object on Cloudflare R2...")
    try:
        head = s3.head_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
        remote_size = head.get("ContentLength", 0)
        etag = head.get("ETag", "")
        print(f" [✓] HeadObject Response   : OK")
        print(f" [✓] Remote Content-Length : {remote_size:,} bytes")
        print(f" [✓] Remote ETag           : {etag}")
        print(f" [✓] Metadata              : {head.get('Metadata', {})}")

        if remote_size == EXPECTED_SIZE:
            print(f" [✓] EXACT SIZE VERIFIED   : {remote_size:,} == {EXPECTED_SIZE:,} bytes")
        else:
            print(f" [!] SIZE MISMATCH         : Remote={remote_size}, Expected={EXPECTED_SIZE}")
            sys.exit(1)

        # Test presigned URL generation and range read
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": OBJECT_KEY},
            ExpiresIn=300,
        )
        print(f" [✓] Presigned Download URL generated successfully.")

        import urllib.request
        req = urllib.request.Request(presigned_url, headers={"Range": "bytes=0-15"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            magic = data[:4]
            print(f" [✓] Range Verification (bytes 0-15): Status {resp.status}, Magic: {magic}")
            if magic == b"GGUF":
                print(" [✓] GGUF Binary Magic Confirmed: b'GGUF'")
            else:
                print(f" [!] Unexpected magic header: {magic}")
                sys.exit(1)

    except Exception as e:
        print(f" [!] Verification error: {e}")
        sys.exit(1)

    print("=" * 75)
    print(" ALL R2 UPLOAD & VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
