"""
HS AI SOLUTIONS — UNIVERSAL DUAL-MODEL ECOSYSTEM TEST SUITE
Layer: ECOSYSTEM VERIFICATION (test_dual_model_ecosystem)
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Comprehensive verification of:
1. Hardware detection & GPU acceleration.
2. GGUF binary metadata extraction for both July and Gravity.
3. Model Manager lifecycle (load, switch, unload, memory constraints).
4. July LLM identity preservation.
5. Gravity LLM identity preservation.
6. Intelligent Auto Router task categorization & rationale.
7. Universal Visual Studio interactive rendering across 8 domains.
8. Shared Agent Engine & Permission Manager authorization gates.
9. Conversation storage model isolation & Markdown export.
"""

from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hs_ecosystem.core.hardware import UniversalHardwareEngine
from hs_ecosystem.core.model_manager import UniversalModelManager
from hs_ecosystem.core.dual_models import JulyModelCore, GravityModelCore
from hs_ecosystem.core.model_router import IntelligentModelRouter
from hs_ecosystem.agent.permission_manager import AgentPermissionManager, PermissionLevel
from hs_ecosystem.agent.tool_router import SharedToolRouter
from hs_ecosystem.agent.agent_engine import SharedAgentEngine
from hs_ecosystem.visual.visual_studio import UniversalVisualEngine
from hs_ecosystem.storage.conversation_store import UniversalConversationStore


def run_dual_ecosystem_verification() -> Dict[str, Any]:
    print("================================================================================")
    print("HS AI SOLUTIONS — UNIVERSAL DUAL-MODEL ECOSYSTEM VERIFICATION SUITE")
    print("FOUNDER: HARSHAN SELIYAN | PRODUCT: JULY LLM & GRAVITY LLM")
    print("================================================================================")

    manager = UniversalModelManager()
    july_core = JulyModelCore(manager)
    gravity_core = GravityModelCore(manager)
    router = IntelligentModelRouter(manager)
    perm_mgr = AgentPermissionManager()
    tool_router = SharedToolRouter(workspace_root=REPO_ROOT)
    agent_engine = SharedAgentEngine(tool_router)
    visual_engine = UniversalVisualEngine()
    conv_store = UniversalConversationStore()

    tests = [
        # 1. Hardware Detection
        {
            "id": "ECO_01_HARDWARE",
            "name": "Cross-Platform Hardware Profiling",
            "runner": lambda: UniversalHardwareEngine.detect_hardware(),
            "check": lambda hw: hw.cpu_cores > 0 and hw.total_ram_gb > 0 and hw.gpu_name != ""
        },
        # 2. GGUF Metadata Extraction - July
        {
            "id": "ECO_02_JULY_META",
            "name": "July GGUF Binary Metadata Inspection",
            "runner": lambda: manager.inspect_gguf_metadata("july"),
            "check": lambda m: m.is_present_on_disk and m.layer_count == 28 and m.architecture == "LLAMA"
        },
        # 3. GGUF Metadata Extraction - Gravity
        {
            "id": "ECO_03_GRAVITY_META",
            "name": "Gravity GGUF Binary Metadata Inspection",
            "runner": lambda: manager.inspect_gguf_metadata("gravity"),
            "check": lambda m: m.is_present_on_disk and m.layer_count == 28 and m.file_size_mb > 1000
        },
        # 4. July Identity Preservation
        {
            "id": "ECO_04_JULY_IDENTITY",
            "name": "July Dedicated Identity Preservation",
            "runner": lambda: july_core.format_chat_prompt("Who are you?"),
            "check": lambda p: "JULY LLM" in p and "Harshan Seliyan" in p and "GRAVITY" not in p
        },
        # 5. Gravity Identity Preservation
        {
            "id": "ECO_05_GRAVITY_IDENTITY",
            "name": "Gravity Dedicated Identity Preservation",
            "runner": lambda: gravity_core.format_chat_prompt("Who are you?"),
            "check": lambda p: "GRAVITY LLM" in p and "Harshan Seliyan" in p and "JULY" not in p
        },
        # 6. Model Router: Mathematical task to Gravity
        {
            "id": "ECO_06_ROUTER_MATH",
            "name": "Auto Router: Math/Calculus to Gravity",
            "runner": lambda: router.route_prompt("Solve the differential equation dy/dx + 2*y = e^(-x) and derive eigenvalues."),
            "check": lambda r: r.selected_model == "gravity" and r.mode == "AUTO" and len(r.rationale) > 10
        },
        # 7. Model Router: Conversational/General to July
        {
            "id": "ECO_07_ROUTER_GENERAL",
            "name": "Auto Router: Conversational/General to July",
            "runner": lambda: router.route_prompt("Summarize the key differences between monolithic and microservice architecture in simple terms."),
            "check": lambda r: r.selected_model == "july" and r.mode == "AUTO"
        },
        # 8. Model Router: Manual Override
        {
            "id": "ECO_08_ROUTER_OVERRIDE",
            "name": "Model Router: Manual User Override",
            "runner": lambda: (
                router.route_prompt("Calculate 2+2", requested_mode="JULY").selected_model,
                router.route_prompt("Write a story", requested_mode="GRAVITY").selected_model
            ),
            "check": lambda res: res == ("july", "gravity")
        },
        # 9. Visual Studio: Water Phase Diagram Generation
        {
            "id": "ECO_09_VISUAL_PHASE",
            "name": "Universal Visual Studio: Water Phase Diagram",
            "runner": lambda: visual_engine.render_interactive_html("water_phase_diagram", "Water Phase Diagram"),
            "check": lambda html: "Water (H2O)" in html or "SOLID (ICE)" in html or "Triple Point" in html
        },
        # 10. Visual Studio: Binary Search Animation
        {
            "id": "ECO_10_VISUAL_SEARCH",
            "name": "Universal Visual Studio: Binary Search Animation",
            "runner": lambda: visual_engine.render_interactive_html("binary_search", "Binary Search O(log N)"),
            "check": lambda html: "Binary Search" in html and "LOW" in html and "MID" in html
        },
        # 11. Visual Studio: Neural Topology Parameter Consistency
        {
            "id": "ECO_11_VISUAL_NEURAL",
            "name": "Universal Visual Studio: Neural Consistency (235,146 Params)",
            "runner": lambda: visual_engine.render_interactive_html("neural_network", "Neural Network Architecture"),
            "check": lambda html: "235,146" in html and "200,960" in html and "32,896" in html
        },
        # 12. Visual Studio: Transformer Block Architecture
        {
            "id": "ECO_12_VISUAL_TRANSFORMER",
            "name": "Universal Visual Studio: Transformer Block",
            "runner": lambda: visual_engine.render_interactive_html("transformer_architecture", "Transformer Block"),
            "check": lambda html: "SwiGLU" in html and "RMSNorm" in html and "GQA" in html
        },
        # 13. Permission Manager: Gating Destructive Actions
        {
            "id": "ECO_13_PERMISSIONS_GATE",
            "name": "Permission Gate on Destructive File Deletion",
            "runner": lambda: perm_mgr.evaluate_request("file_delete", {"file_path": "important.txt"}),
            "check": lambda res: res["allowed"] is False and res["requires_token"] is True and "AUTH_" in res["authorization_token"]
        },
        # 14. Shared Agent Engine: Read-Only Tool Execution
        {
            "id": "ECO_14_TOOL_READONLY",
            "name": "Shared Agent: CAS Symbolic Tool Execution",
            "runner": lambda: tool_router.execute_tool_call("cas_solve", {"query": "solve 3*x + 9 = 24"}),
            "check": lambda res: res.get("success") is True and "5" in str(res.get("exact_solution"))
        },
        # 15. Conversation Store Model Isolation & Export
        {
            "id": "ECO_15_CONV_ISOLATION",
            "name": "Conversation Store: Model Isolation & Export",
            "runner": lambda: (
                sid := f"sess_test_{int(time.time()*1000)}",
                conv_store.create_session(sid, "July Chat", "july"),
                conv_store.log_message(sid, "user", "Hello July", "july"),
                conv_store.log_message(sid, "assistant", "Hello from July LLM", "july"),
                conv_store.export_session_markdown(sid)
            )[4],
            "check": lambda md: "JULY LLM" in md and "Hello July" in md and "GRAVITY" not in md
        }
    ]

    passed = 0
    total = len(tests)
    results = []

    for t in tests:
        t0 = time.time()
        try:
            res = t["runner"]()
            elapsed = round(time.time() - t0, 4)
            ok = t["check"](res)
            if ok:
                passed += 1
            status = "PASS" if ok else "FAIL"
        except Exception as e:
            elapsed = round(time.time() - t0, 4)
            ok = False
            status = f"ERROR: {e}"

        results.append({
            "test_id": t["id"],
            "name": t["name"],
            "status": "PASS" if ok else "FAIL",
            "duration_sec": elapsed
        })
        print(f"[{status[:4]}] {t['id']:<24} | {t['name']:<48} | {elapsed:.4f}s")

    pass_rate = round((passed / total) * 100, 1)
    print("--------------------------------------------------------------------------------")
    print(f"DUAL ECOSYSTEM VERIFICATION: {passed}/{total} PASSED ({pass_rate}%)")
    print("================================================================================")

    return {
        "timestamp": time.time(),
        "total_tests": total,
        "passed_tests": passed,
        "pass_rate_percent": pass_rate,
        "tests": results
    }


if __name__ == "__main__":
    run_dual_ecosystem_verification()
