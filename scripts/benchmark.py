"""
HS AI SOLUTIONS - JULY CLOUD AI BENCHMARKING SUITE
Empirical Latency, Tokens Per Second, & Hardware Profiler
Founder: Harshan Seliyan
"""

import os
import sys
import time
import json
import requests
from typing import List, Dict, Any

BENCHMARK_PROMPTS = [
    "Write a short 3-sentence summary of cloud computing.",
    "Explain the difference between a process and a thread in operating systems.",
    "Write a Python function to compute the Fibonacci sequence using memoization.",
    "What are the key architectural advantages of Rotary Position Embeddings (RoPE) in LLMs?"
]


def run_benchmark(endpoint: str, api_key: str, max_tokens: int = 128, iterations: int = 3):
    print("==================================================")
    print("       JULY CLOUD INFERENCE BENCHMARK             ")
    print(f"       Endpoint: {endpoint}")
    print(f"       Max Tokens: {max_tokens} | Iterations: {iterations}")
    print("==================================================")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-API-Key": api_key
    }

    # 1. Health check & status
    try:
        health_resp = requests.get(f"{endpoint}/health", headers=headers, timeout=10)
        health = health_resp.json()
        print(f"[STATUS] Server Status: {health.get('status')} | Mock Mode: {health.get('is_mock')}")
    except Exception as e:
        print(f"[ERROR] Could not connect to {endpoint}/health: {e}")
        return

    results: List[Dict[str, Any]] = []

    print("\n--- Starting Benchmark Iterations ---")
    for idx, prompt in enumerate(BENCHMARK_PROMPTS[:iterations], 1):
        print(f"\n[Test {idx}/{iterations}] Prompt: \"{prompt[:45]}...\"")
        payload = {
            "message": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": False
        }

        start_time = time.time()
        try:
            resp = requests.post(f"{endpoint}/v1/chat", headers=headers, json=payload, timeout=60)
            elapsed = time.time() - start_time

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("response", "")
                tokens = data.get("completion_tokens", len(content.split()))
                tps = round(tokens / elapsed, 2) if elapsed > 0 else 0.0

                print(f" -> Output Length: {len(content)} chars (~{tokens} tokens)")
                print(f" -> Total Latency: {round(elapsed, 2)}s")
                print(f" -> Measured Throughput: {tps} tokens/sec")

                results.append({
                    "prompt": prompt,
                    "tokens": tokens,
                    "latency_sec": round(elapsed, 3),
                    "tokens_per_sec": tps,
                    "is_mock": data.get("is_mock", False)
                })
            else:
                print(f" -> Failed: HTTP {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f" -> Request Exception: {e}")

    if not results:
        print("[ERROR] No benchmark runs completed successfully.")
        return

    # Summary
    avg_latency = round(sum(r["latency_sec"] for r in results) / len(results), 3)
    avg_tps = round(sum(r["tokens_per_sec"] for r in results) / len(results), 2)
    total_tokens = sum(r["tokens"] for r in results)

    print("\n==================================================")
    print("             BENCHMARK SUMMARY                    ")
    print("==================================================")
    print(f"Total Successful Queries:  {len(results)}")
    print(f"Total Tokens Evaluated:    {total_tokens}")
    print(f"Average Request Latency:   {avg_latency} seconds")
    print(f"Average Generation Speed:  {avg_tps} tokens/second")
    print(f"Mode Tested:               {'MOCK SIMULATION' if results[0]['is_mock'] else 'REAL GGUF CPU INFERENCE'}")
    print("==================================================")


if __name__ == "__main__":
    ep = os.getenv("JULY_ENDPOINT", "http://localhost:8000")
    key = os.getenv("JULY_API_KEY", "july-hs-secret-key-2026")
    run_benchmark(endpoint=ep, api_key=key, max_tokens=64, iterations=2)
