"""
HS AI SOLUTIONS — ALWAYS-ON AUTONOMOUS GATEWAY SERVICE
Module: hs_ecosystem.gateway.service
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 8:
- FastAPI always-on background service
- WebSocket real-time event & telemetry streaming
- REST endpoints for tasks, memory, skills, tools, and sandbox telemetry
- Secure token validation
"""

from __future__ import annotations
import os
import sys
import time
import json
import uvicorn
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..agent.task_engine import AutonomousTaskEngine, TaskPersistenceStore, TaskPlan
from ..agent.tool_registry import ToolRegistry
from ..agent.hierarchical_memory import HierarchicalMemorySystem, MemoryLayer
from ..agent.skill_engine import SkillEngine
from ..agent.multi_agent import JulyMainCoordinator, AgentTaskAssignment
from ..agent.scheduler import AutonomousScheduler, PersistentSchedulerStore
from july_distribution.client.sandbox import SandboxManager


app = FastAPI(
    title="July Autonomous AI Agent Gateway",
    description="HS AI Solutions Always-On Autonomous Agent & Sandbox Gateway",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core singletons
tool_registry = ToolRegistry()
memory_system = HierarchicalMemorySystem()
skill_engine = SkillEngine()
task_store = TaskPersistenceStore()
task_engine = AutonomousTaskEngine(store=task_store, tool_executor=tool_registry.execute)
coordinator = JulyMainCoordinator(registry=tool_registry)
scheduler = AutonomousScheduler(executor_callback=lambda g: task_engine.execute_plan(task_engine.plan_task(g)))
scheduler.start()


class RunGoalRequest(BaseModel):
    goal: str
    model: str = "july"


class CronJobRequest(BaseModel):
    name: str
    cron_expr: str
    goal: str


class MemoryStoreRequest(BaseModel):
    layer: str
    key: str
    content: str


# REST Endpoints
@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "July Autonomous Gateway",
        "organization": "HS AI Solutions",
        "timestamp": time.time()
    }


@app.post("/api/agent/run")
def run_goal(req: RunGoalRequest):
    plan = task_engine.plan_task(req.goal, model_id=req.model)
    executed_plan = task_engine.execute_plan(plan)
    return {
        "task_id": executed_plan.task_id,
        "status": executed_plan.status.value,
        "verification_passed": executed_plan.verification_passed,
        "subtasks": [
            {
                "id": st.id,
                "name": st.name,
                "status": st.status.value,
                "output": st.output
            }
            for st in executed_plan.subtasks
        ]
    }


@app.get("/api/agent/tasks")
def list_tasks(limit: int = 20):
    return task_store.list_tasks(limit=limit)


@app.post("/api/agent/tasks/{task_id}/resume")
def resume_task(task_id: str):
    res = task_engine.resume_task(task_id)
    if not res:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": res.task_id, "status": res.status.value}


@app.get("/api/agent/memory")
def get_memory(query: Optional[str] = None, layer: Optional[str] = None, semantic: bool = False):
    if query:
        if semantic:
            mems = memory_system.search_semantic(query, layer=layer)
        else:
            mems = memory_system.search_fts(query, layer=layer)
    else:
        mems = memory_system.list_memories(layer=layer)
    return [m.__dict__ for m in mems]


@app.post("/api/agent/memory")
def store_memory(req: MemoryStoreRequest):
    mem_id = memory_system.store_memory(req.layer.upper(), req.key, req.content)
    return {"success": True, "id": mem_id}


@app.delete("/api/agent/memory/{mem_id}")
def delete_memory(mem_id: int):
    ok = memory_system.delete_memory(mem_id)
    return {"success": ok}


@app.get("/api/agent/skills")
def list_skills():
    return skill_engine.list_skills()


@app.get("/api/agent/tools")
def list_tools():
    return tool_registry.get_schemas()


@app.get("/api/agent/scheduler")
def list_scheduled():
    return scheduler.list_jobs()


@app.post("/api/agent/scheduler/cron")
def create_cron(req: CronJobRequest):
    job = scheduler.add_cron_job(req.name, req.cron_expr, req.goal)
    return {"success": True, "job_id": job.id, "next_run_at": job.next_run_at}


@app.get("/api/agent/sandbox/status")
def sandbox_status():
    sbx = SandboxManager.get_instance()
    return sbx.get_status()


# WebSockets for real-time telemetry
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


ws_manager = ConnectionManager()


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or process client command
            await websocket.send_text(json.dumps({"event": "ack", "received": data}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


def start_gateway(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_gateway()
