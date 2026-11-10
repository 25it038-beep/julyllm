"""
HS AI SOLUTIONS - JULY CLOUD HEALTH PROBE
Container Readiness & Liveness Verification
Founder: Harshan Seliyan
"""

import os
import sys
import requests

def check_health(endpoint: str = "http://localhost:8000"):
    url = f"{endpoint.rstrip('/')}/health"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[HEALTH CHECK PASS] Status: {data.get('status')}, Model Loaded: {data.get('model_loaded')}")
            sys.exit(0)
        else:
            print(f"[HEALTH CHECK FAIL] Received HTTP {resp.status_code}: {resp.text}")
            sys.exit(1)
    except Exception as e:
        print(f"[HEALTH CHECK ERROR] Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.getenv("PORT_URL", "http://localhost:8000")
    check_health(target)
