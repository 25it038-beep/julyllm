"""
HS AI SOLUTIONS — UNIVERSAL ECOSYSTEM CENTRAL SERVER
Module: hs_ecosystem.server.app
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

FastAPI & WebSocket application serving:
- Universal Model Management API (July LLM & Gravity LLM).
- Intelligent Model Router (AUTO Mode).
- Shared Agent Engine & Permission Gate.
- Universal Visual Response Engine.
- Local-first Persistent Conversation Management.
- Embedded Obsidian Black & Champagne Gold SPA Interface.
"""

from __future__ import annotations
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hs_ecosystem.core.hardware import UniversalHardwareEngine
from hs_ecosystem.core.model_manager import UniversalModelManager
from hs_ecosystem.core.dual_models import JulyModelCore, GravityModelCore
from hs_ecosystem.core.model_router import IntelligentModelRouter
from hs_ecosystem.agent.tool_router import SharedToolRouter
from hs_ecosystem.agent.agent_engine import SharedAgentEngine
from hs_ecosystem.agent.task_engine import AutonomousTaskEngine, TaskPersistenceStore
from hs_ecosystem.agent.tool_registry import ToolRegistry
from hs_ecosystem.agent.hierarchical_memory import HierarchicalMemorySystem
from hs_ecosystem.agent.skill_engine import SkillEngine
from hs_ecosystem.agent.scheduler import AutonomousScheduler
from july_distribution.client.sandbox import SandboxManager
from hs_ecosystem.visual.visual_studio import UniversalVisualEngine
from hs_ecosystem.storage.conversation_store import UniversalConversationStore
from july_distribution.server.r2_manager import CloudflareR2DistributionGateway
from july_distribution.server.main import CENTRAL_MODEL_REGISTRY

r2_gateway = CloudflareR2DistributionGateway()

app = FastAPI(
    title="HS AI Solutions — Universal AI Ecosystem",
    description="Unified cross-platform ecosystem for JULY LLM & GRAVITY LLM by Harshan Seliyan",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Subsystems
manager = UniversalModelManager()
july_core = JulyModelCore(manager)
gravity_core = GravityModelCore(manager)
router = IntelligentModelRouter(manager)
tool_router = SharedToolRouter(workspace_root=REPO_ROOT)
agent_engine = SharedAgentEngine(tool_router)
visual_engine = UniversalVisualEngine()
conv_store = UniversalConversationStore()

# Initialize Autonomous Agent Platform Subsystems
auto_tool_registry = ToolRegistry()
auto_task_store = TaskPersistenceStore()
auto_task_engine = AutonomousTaskEngine(store=auto_task_store, tool_executor=auto_tool_registry.execute)
auto_memory = HierarchicalMemorySystem()
auto_skills = SkillEngine()
auto_scheduler = AutonomousScheduler(executor_callback=lambda g: auto_task_engine.execute_plan(auto_task_engine.plan_task(g)))
auto_scheduler.start()


# --- Pydantic Request Models ---
class ChatRequest(BaseModel):
    message: str
    mode: str = "AUTO"  # "JULY", "GRAVITY", "AUTO"
    session_id: Optional[str] = None
    temperature: float = 0.6
    max_tokens: int = 1024


class ModelActionRequest(BaseModel):
    model_id: str
    force_cpu: bool = False
    context_length: Optional[int] = None


class ToolConfirmationRequest(BaseModel):
    token: str
    action: str  # "confirm" or "deny"


class VisualRenderRequest(BaseModel):
    visualization_type: str
    title: str
    explanation: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# --- REST Endpoints ---

@app.get("/api/system/status")
def get_system_status():
    """Returns overview of hardware, models, memory, and acceleration."""
    return manager.get_system_overview()


@app.get("/api/models")
def get_all_models_registry():
    """Returns centralized model registry mapping July and Gravity."""
    models_list = []
    for mid, meta in CENTRAL_MODEL_REGISTRY.items():
        r2_head = r2_gateway.verify_object_head(meta["object_key"])
        is_avail = r2_head.get("success", False)
        models_list.append({
            "id": meta["id"],
            "name": meta["name"],
            "family": meta["family"],
            "storage_provider": meta["storage_provider"],
            "bucket": meta["bucket"],
            "object_key": meta["object_key"],
            "status": "available" if is_avail else "unavailable",
            "size_bytes": r2_head.get("content_length", meta["size_bytes"]),
            "architecture": meta["architecture"],
            "base_model": meta["base_model"],
            "layers": meta["layers"],
            "context_length": meta["context_length"],
            "description": meta["description"]
        })
    return {
        "organization": "HS AI Solutions",
        "founder": "Harshan Seliyan",
        "models": models_list
    }


@app.get("/api/models/{model_id}")
def get_single_model_registry(model_id: str):
    """Returns verified metadata for an individual model (july or gravity)."""
    mid = model_id.lower().strip()
    if mid not in CENTRAL_MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry")
    meta = dict(CENTRAL_MODEL_REGISTRY[mid])
    r2_head = r2_gateway.verify_object_head(meta["object_key"])
    meta["status"] = "available" if r2_head.get("success") else "unavailable"
    if r2_head.get("success"):
        meta["size_bytes"] = r2_head["content_length"]
        meta["etag"] = r2_head.get("etag")
        meta["last_modified"] = r2_head.get("last_modified")
    return meta


@app.get("/api/models/{model_id}/status")
def get_model_status_live(model_id: str):
    """Performs live HeadObject verification on Cloudflare R2 for the exact model."""
    mid = model_id.lower().strip()
    if mid not in CENTRAL_MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    meta = CENTRAL_MODEL_REGISTRY[mid]
    r2_status = r2_gateway.verify_object_head(meta["object_key"])
    if not r2_status.get("success"):
        return JSONResponse(
            status_code=502,
            content={
                "model_id": mid,
                "model_name": meta["name"],
                "object_key": meta["object_key"],
                "bucket": r2_gateway.bucket_name,
                "status": "unavailable",
                "error": r2_status.get("error", "HeadObject verification failed")
            }
        )
    return {
        "model_id": mid,
        "model_name": meta["name"],
        "object_key": meta["object_key"],
        "bucket": r2_gateway.bucket_name,
        "status": "available",
        "content_length": r2_status["content_length"],
        "etag": r2_status["etag"],
        "last_modified": r2_status["last_modified"],
        "architecture": meta["architecture"],
        "context_length": meta["context_length"],
        "sha256": meta["sha256"],
        "storage_provider": "cloudflare_r2"
    }


@app.post("/api/models/{model_id}/download")
def download_model_signed_url(model_id: str):
    """Generates a short-lived presigned URL directly from private Cloudflare R2."""
    mid = model_id.lower().strip()
    if mid not in CENTRAL_MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    meta = CENTRAL_MODEL_REGISTRY[mid]
    r2_check = r2_gateway.verify_object_head(meta["object_key"])
    if not r2_check.get("success"):
        raise HTTPException(status_code=502, detail=f"R2 verification failure: {r2_check.get('error')}")
    url = r2_gateway.generate_short_lived_download_url(meta["object_key"], 900)
    return {
        "success": True,
        "model_id": mid,
        "model_name": meta["name"],
        "storage_provider": "cloudflare_r2",
        "bucket": r2_gateway.bucket_name,
        "object_key": meta["object_key"],
        "download_url": url,
        "expires_in_seconds": 900,
        "size_bytes": r2_check["content_length"],
        "etag": r2_check.get("etag", ""),
        "expected_sha256": meta["sha256"],
        "architecture": meta["architecture"],
        "chunk_size_bytes": 8 * 1024 * 1024
    }


@app.post("/api/model/load")
def load_model(req: ModelActionRequest):
    """Loads a specific model into memory."""
    success = manager.load_model(req.model_id, force_cpu=req.force_cpu, context_length=req.context_length)
    if not success:
        err = manager.states.get(req.model_id.lower(), {}).error_message or "Unknown failure"
        raise HTTPException(status_code=500, detail=f"Failed to load {req.model_id}: {err}")
    return {"status": "success", "loaded_model": req.model_id}


@app.post("/api/model/unload")
def unload_model(req: ModelActionRequest):
    """Unloads a specific model and reclaims memory."""
    manager.unload_model(req.model_id)
    return {"status": "success", "unloaded_model": req.model_id}


@app.post("/api/model/switch")
def switch_model(req: ModelActionRequest):
    """Switches active model."""
    success = manager.switch_model(req.model_id)
    return {"status": "success" if success else "failed", "active_model": manager.active_model_id}


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Executes single-turn inference with intelligent routing."""
    routing = router.route_prompt(req.message, requested_mode=req.mode)
    selected = routing.selected_model

    sid = req.session_id or f"session_{int(time.time())}"
    conv_store.log_message(sid, "user", req.message, selected)

    if selected == "gravity":
        verified = gravity_core.generate_verified(req.message)
    else:
        verified = july_core.generate_verified(req.message)

    resp_text = verified.verified_final_response
    conv_store.log_message(sid, "assistant", resp_text, selected)

    return {
        "model_used": selected.upper() + " LLM",
        "routing": routing.__dict__,
        "response": resp_text,
        "confidence": verified.confidence,
        "elapsed_seconds": verified.elapsed_seconds,
        "corrections_applied": verified.corrections_applied,
        "session_id": sid
    }


@app.post("/api/visual/render")
def render_visual(req: VisualRenderRequest):
    """Generates standalone interactive HTML visualization."""
    html = visual_engine.render_interactive_html(
        visualization_type=req.visualization_type,
        title=req.title,
        explanation=req.explanation or "",
        data=req.data
    )
    return HTMLResponse(content=html)


@app.get("/api/conversations")
def list_conversations(model: Optional[str] = Query(None)):
    """Lists conversation sessions with optional model filtering."""
    sessions = conv_store.list_sessions(model_filter=model)
    return {"sessions": [s.__dict__ for s in sessions]}


@app.get("/api/conversations/{session_id}")
def get_conversation_history(session_id: str):
    """Returns all messages in a session."""
    messages = conv_store.get_messages(session_id)
    return {"session_id": session_id, "messages": [m.__dict__ for m in messages]}


@app.post("/api/permission/authorize")
def authorize_tool(req: ToolConfirmationRequest):
    """Approves or denies a gated tool execution."""
    if req.action == "confirm":
        ok = tool_router.permission_mgr.confirm_token(req.token)
    else:
        ok = tool_router.permission_mgr.deny_token(req.token)
    return {"status": "success" if ok else "not_found", "token": req.token, "action": req.action}


# --- Autonomous Agent Platform Endpoints ---

class AgentRunRequest(BaseModel):
    goal: str
    model: str = "july"


@app.post("/api/agent/run")
def api_agent_run(req: AgentRunRequest):
    plan = auto_task_engine.plan_task(req.goal, model_id=req.model)
    executed = auto_task_engine.execute_plan(plan)
    return {
        "task_id": executed.task_id,
        "status": executed.status.value,
        "verification_passed": executed.verification_passed,
        "verification_notes": executed.verification_notes,
        "subtasks": [
            {
                "id": st.id,
                "name": st.name,
                "status": st.status.value,
                "output": st.output
            }
            for st in executed.subtasks
        ]
    }


@app.get("/api/agent/tasks")
def api_agent_tasks(limit: int = 20):
    return auto_task_store.list_tasks(limit=limit)


@app.get("/api/agent/memory")
def api_agent_memory(query: Optional[str] = None, layer: Optional[str] = None):
    if query:
        mems = auto_memory.search_fts(query, layer=layer)
    else:
        mems = auto_memory.list_memories(layer=layer)
    return [m.__dict__ for m in mems]


@app.get("/api/agent/skills")
def api_agent_skills():
    return auto_skills.list_skills()


@app.get("/api/agent/tools")
def api_agent_tools():
    return auto_tool_registry.get_schemas()


@app.get("/api/agent/scheduler")
def api_agent_scheduler():
    return auto_scheduler.list_jobs()


@app.get("/api/agent/sandbox/status")
def api_agent_sandbox_status():
    sbx = SandboxManager.get_instance()
    return sbx.get_status()


# --- Embedded Obsidian Black & Champagne Gold Web UI ---

@app.get("/", response_class=HTMLResponse)
def get_web_dashboard():
    web_file = REPO_ROOT / "hs_ecosystem" / "web" / "index.html"
    if web_file.exists():
        with open(web_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>HS AI Solutions Ecosystem</h1><p>Web dashboard building...</p>"
