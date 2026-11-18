"""
HS AI SOLUTIONS — SREE LLM CODING SPEED & REASONING BENCHMARK SUITE
Layer: BENCHMARK HARNESS (benchmarks/benchmark_sree.py)
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: SREE LLM & JULY AI CODING AGENT | Family: HS AI Family

Compares Baseline (Unoptimized) vs Optimized (Adaptive Code-First) across 6 real-world coding benchmarks:
1. Simple Python Function (Memoized Fibonacci / Math)
2. Complete React Component (TypeScript UserProfileCard with state and styling)
3. Multi-File Application (Backend Models + API Client)
4. Complex Debugging (Asyncio race condition & memory leak fix)
5. API Integration (GitHub REST Client with exponential backoff & rate limit handling)
6. Algorithm Implementation (LRU Cache with O(1) get and put)

Measures:
- Time to First Token (TTFT)
- Time to First Code Token (TTFC)
- Total Completion Time
- Reasoning / Thinking Tokens Count
- Total Generated Tokens
- LLM Calls Count
- Tool Calls Count
- Code Correctness / Syntax Validity
"""

from __future__ import annotations
import os
import sys
import time
import json
import ast
from pathlib import Path
from typing import Dict, Any, List

# Add workspace to path
workspace_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_dir))

import llama_cpp
from july_distribution.client.adaptive_reasoning import AdaptiveReasoningEngine, ThinkingLevel
from july_distribution.client.reasoning.code_verifier import ProgrammingIntelligenceEngine

BENCHMARK_SUITE = [
    {
        "id": "1_simple_python_function",
        "name": "1. Simple Python Function",
        "prompt": "Write a python function to compute fibonacci numbers with memoization and type annotations.",
        "expected_lang": "python",
        "validation_func": lambda code: "def " in code and ("memo" in code or "lru_cache" in code)
    },
    {
        "id": "2_react_component",
        "name": "2. Complete React Component",
        "prompt": "Create a complete React TypeScript component for a UserProfileCard with avatar, name, bio, active status badge, and an edit profile button.",
        "expected_lang": "typescript",
        "validation_func": lambda code: ("interface " in code or "type " in code) and ("UserProfileCard" in code or "React.FC" in code or "export " in code)
    },
    {
        "id": "3_multi_file_app",
        "name": "3. Multi-File Application",
        "prompt": "Create a minimal multi-file architecture with: 1) models.py for SQLite user storage, 2) client.py for fetching users with error handling.",
        "expected_lang": "python",
        "validation_func": lambda code: "sqlite" in code.lower() or "class User" in code or "def fetch_users" in code
    },
    {
        "id": "4_complex_debugging",
        "name": "4. Complex Debugging",
        "prompt": "Fix the race condition and infinite memory accumulation in this Python worker:\n```python\nimport asyncio\nqueue = []\nasync def worker():\n    while True:\n        if len(queue) > 0:\n            item = queue.pop(0)\n            await process(item)\n```",
        "expected_lang": "python",
        "validation_func": lambda code: "asyncio.Queue" in code or "collections.deque" in code or "Lock" in code
    },
    {
        "id": "5_api_integration",
        "name": "5. API Integration",
        "prompt": "Implement a robust GitHub API client in Python that fetches repository releases with exponential backoff retry and rate limit handling.",
        "expected_lang": "python",
        "validation_func": lambda code: "urllib" in code or "requests" in code or "aiohttp" in code and "retry" in code.lower()
    },
    {
        "id": "6_algorithm_implementation",
        "name": "6. Algorithm Implementation",
        "prompt": "Implement an LRU Cache in Python using a doubly linked list and hash map with O(1) get and put operations.",
        "expected_lang": "python",
        "validation_func": lambda code: "class LRUCache" in code and ("def get" in code or "def put" in code)
    }
]


def run_single_inference(
    llm: llama_cpp.Llama,
    system_prompt: str,
    user_prompt: str,
    prefill_assistant: str = "",
    temperature: float = 0.2,
    top_p: float = 0.95,
    max_tokens: int = 400
) -> Dict[str, Any]:
    """Runs a single streaming inference and records timing and token telemetry."""
    formatted = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n{prefill_assistant}"
    )

    t0 = time.time()
    ttft = None
    ttfc = None
    accumulated_text = prefill_assistant
    generated_text = ""
    thinking_tokens = 0
    code_tokens = 0
    total_tokens = 0
    in_thinking = bool(prefill_assistant and not ("</think>" in prefill_assistant))

    stream = llm(
        formatted,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        stop=["<|im_end|>", "<|im_start|>", "<|endoftext|>"],
        stream=True
    )

    for chunk in stream:
        delta = chunk["choices"][0].get("text", "")
        if not delta:
            continue
        total_tokens += 1
        accumulated_text += delta
        generated_text += delta
        now = time.time()

        if ttft is None:
            ttft = now - t0

        if "<think>" in delta or "<think>" in accumulated_text:
            if "</think>" not in accumulated_text:
                in_thinking = True

        if "</think>" in delta or "</think>" in accumulated_text:
            in_thinking = False

        if in_thinking:
            thinking_tokens += 1
        else:
            code_tokens += 1
            if ttfc is None and any(marker in accumulated_text for marker in ["def ", "class ", "```", "import ", "interface ", "function "]):
                ttfc = now - t0

    total_time = time.time() - t0
    if ttfc is None and not in_thinking:
        ttfc = total_time

    return {
        "ttft_s": ttft or 0.0,
        "ttfc_s": ttfc or total_time,
        "total_time_s": total_time,
        "thinking_tokens": thinking_tokens,
        "code_tokens": code_tokens,
        "total_tokens": total_tokens,
        "output_text": accumulated_text,
        "generated_text": generated_text
    }


def execute_benchmark_suite() -> Dict[str, Any]:
    """Executes all 6 benchmarks comparing unoptimized baseline vs optimized adaptive code-first."""
    print("=" * 80)
    print("HS AI SOLUTIONS — SREE LLM CODING SPEED & ACCELERATION BENCHMARK")
    print("=" * 80)

    model_candidates = [
        workspace_dir / "models" / "sree" / "model.gguf",
        Path.home() / "OneDrive" / "Desktop" / "collab-editor" / "models" / "sree" / "model.gguf",
    ]
    model_path = next((p for p in model_candidates if p.exists()), None)
    if not model_path:
        raise FileNotFoundError("SREE model weights not found at models/sree/model.gguf")

    print(f"Loading SREE model from: {model_path}")
    print("Initializing llama.cpp with Flash Attention enabled...")
    llm = llama_cpp.Llama(
        model_path=str(model_path),
        n_ctx=4096,
        n_gpu_layers=36,
        n_batch=512,
        flash_attn=True,
        verbose=False
    )
    print("Model loaded successfully on CUDA GPU.\n")

    code_engine = ProgrammingIntelligenceEngine()
    results = []

    for task in BENCHMARK_SUITE:
        print(f"\n[{task['name']}]")
        print(f"Prompt: {task['prompt'][:75]}...")

        # 1. Baseline Run (Unoptimized: default unconstrained <think> mode, temp 0.7)
        sys_unopt = "You are SREE LLM, developed by HS AI Solutions."
        base_res = run_single_inference(
            llm=llm,
            system_prompt=sys_unopt,
            user_prompt=task["prompt"],
            prefill_assistant="",
            temperature=0.7,
            top_p=0.9,
            max_tokens=300
        )

        base_is_correct = task["validation_func"](base_res["output_text"])
        print(f"  BASELINE  : TTFT={base_res['ttft_s']:.3f}s | TTFC={base_res['ttfc_s']:.3f}s | Total={base_res['total_time_s']:.2f}s | ThinkTok={base_res['thinking_tokens']} | Correct={base_is_correct}")

        # 2. Optimized Run (Adaptive Code-First: task classified, prefill applied, temp 0.15-0.25)
        level, rationale = AdaptiveReasoningEngine.classify_task(task["prompt"])
        steering = AdaptiveReasoningEngine.get_steering("sree", level, rationale)

        opt_res = run_single_inference(
            llm=llm,
            system_prompt=f"You are SREE LLM, developed by HS AI Solutions.\n{steering.system_directive}",
            user_prompt=task["prompt"],
            prefill_assistant=steering.prefill_assistant or "",
            temperature=steering.temperature,
            top_p=steering.top_p,
            max_tokens=300
        )

        # Code verification check
        detected = code_engine.detect_code_block(opt_res["output_text"])
        opt_is_correct = task["validation_func"](opt_res["output_text"])
        if detected and detected[0] == "python":
            py_ver = code_engine.verify_code(detected[1], "python")
            if not py_ver.is_valid_syntax:
                opt_is_correct = False

        speedup = (base_res["ttfc_s"] / max(0.001, opt_res["ttfc_s"])) if opt_res["ttfc_s"] > 0 else 1.0
        print(f"  OPTIMIZED : TTFT={opt_res['ttft_s']:.3f}s | TTFC={opt_res['ttfc_s']:.3f}s | Total={opt_res['total_time_s']:.2f}s | ThinkTok={opt_res['thinking_tokens']} | Level={level.value.upper()} | Speedup={speedup:.1f}x | Correct={opt_is_correct}")

        results.append({
            "task_id": task["id"],
            "task_name": task["name"],
            "level": level.value,
            "baseline": {
                "ttft_s": round(base_res["ttft_s"], 3),
                "ttfc_s": round(base_res["ttfc_s"], 3),
                "total_time_s": round(base_res["total_time_s"], 3),
                "thinking_tokens": base_res["thinking_tokens"],
                "total_tokens": base_res["total_tokens"],
                "llm_calls": 1,
                "tool_calls": 0,
                "is_correct": base_is_correct
            },
            "optimized": {
                "ttft_s": round(opt_res["ttft_s"], 3),
                "ttfc_s": round(opt_res["ttfc_s"], 3),
                "total_time_s": round(opt_res["total_time_s"], 3),
                "thinking_tokens": opt_res["thinking_tokens"],
                "total_tokens": opt_res["total_tokens"],
                "llm_calls": 1,
                "tool_calls": 1 if detected else 0,
                "is_correct": opt_is_correct,
                "speedup_ratio": round(speedup, 2)
            }
        })

    out_file = workspace_dir / "benchmarks" / "benchmark_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"BENCHMARK COMPLETED: Results successfully saved to {out_file}")
    print("=" * 80)
    return {"results": results}


if __name__ == "__main__":
    execute_benchmark_suite()
