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
from hs_ecosystem.visual.visual_studio import UniversalVisualEngine
from hs_ecosystem.storage.conversation_store import UniversalConversationStore

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


# --- Embedded Obsidian Black & Champagne Gold Web UI ---

@app.get("/", response_class=HTMLResponse)
def get_web_dashboard():
    web_file = REPO_ROOT / "hs_ecosystem" / "web" / "index.html"
    if web_file.exists():
        with open(web_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>HS AI Solutions Ecosystem</h1><p>Web dashboard building...</p>"
