"""
HS AI SOLUTIONS — MULTI-AGENT ORCHESTRATION SWARM
Module: hs_ecosystem.agent.multi_agent
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 7:
Specialized Agent Roles:
1. JULY MAIN (Coordinator)
2. RESEARCH AGENT
3. CODING AGENT
4. BROWSER AGENT
5. TESTING AGENT
6. SECURITY AGENT
7. FILE AGENT

Includes:
- Parallel execution via ThreadPool
- Independent agent contexts
- Shared blackboard / task artifacts store
- Inter-agent message bus
- Strict permission scoping per specialist agent
"""

from __future__ import annotations
import os
import sys
import time
import json
import uuid
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from .tool_registry import ToolRegistry
from .tools.base import PermissionTier
from july_distribution.client.sandbox import SandboxManager


@dataclass
class AgentMessage:
    id: str
    sender_role: str
    recipient_role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTaskAssignment:
    assignment_id: str
    agent_role: str
    task_goal: str
    input_data: Dict[str, Any]
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    output: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class BlackboardArtifactStore:
    """Thread-safe shared blackboard for exchanging task artifacts between agents."""

    def __init__(self):
        self._lock = threading.Lock()
        self._artifacts: Dict[str, Any] = {}

    def set_artifact(self, key: str, value: Any):
        with self._lock:
            self._artifacts[key] = value

    def get_artifact(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._artifacts.get(key)

    def list_artifacts(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._artifacts)


class SpecialistAgent:
    """Base class for specialized swarm agents with restricted permission scope."""

    def __init__(
        self,
        role: str,
        description: str,
        allowed_tools: List[str],
        max_permission_tier: PermissionTier,
        registry: ToolRegistry,
        blackboard: BlackboardArtifactStore
    ):
        self.role = role
        self.description = description
        self.allowed_tools = set(allowed_tools)
        self.max_permission_tier = max_permission_tier
        self.registry = registry
        self.blackboard = blackboard

    def execute_assignment(self, assignment: AgentTaskAssignment) -> Dict[str, Any]:
        assignment.status = "RUNNING"
        t0 = time.time()

        try:
            result = self._run_role_logic(assignment)
            assignment.status = "COMPLETED"
            assignment.output = result
            assignment.completed_at = time.time()
            return {"success": True, "role": self.role, "output": result, "duration": round(time.time() - t0, 3)}
        except Exception as e:
            assignment.status = "FAILED"
            assignment.error = str(e)
            assignment.completed_at = time.time()
            return {"success": False, "role": self.role, "error": str(e), "duration": round(time.time() - t0, 3)}

    def _run_role_logic(self, assignment: AgentTaskAssignment) -> Any:
        """Default tool dispatch with permission verification."""
        tool_name = assignment.input_data.get("tool_name")
        tool_args = assignment.input_data.get("tool_args", {})

        if tool_name:
            if tool_name not in self.allowed_tools:
                raise PermissionError(f"Agent '{self.role}' is not authorized to invoke tool '{tool_name}'.")

            tool_obj = self.registry.get_tool(tool_name)
            if not tool_obj:
                raise ValueError(f"Tool '{tool_name}' does not exist.")

            # Validate tier
            if tool_obj.permission_tier == PermissionTier.DESTRUCTIVE and self.max_permission_tier != PermissionTier.DESTRUCTIVE:
                raise PermissionError(f"Agent '{self.role}' cannot invoke DESTRUCTIVE tool '{tool_name}'.")

            res = tool_obj.execute(tool_args)
            return res.to_dict()

        return f"Completed {assignment.task_goal}"


class ResearchAgent(SpecialistAgent):
    def __init__(self, registry: ToolRegistry, blackboard: BlackboardArtifactStore):
        super().__init__(
            role="RESEARCH_AGENT",
            description="Searches web documentation, gathers citations and verifies facts.",
            allowed_tools=["web_search", "browser_navigate"],
            max_permission_tier=PermissionTier.SAFE,
            registry=registry,
            blackboard=blackboard
        )


class CodingAgent(SpecialistAgent):
    def __init__(self, registry: ToolRegistry, blackboard: BlackboardArtifactStore):
        super().__init__(
            role="CODING_AGENT",
            description="Application development, code generation, refactoring, and AST inspections.",
            allowed_tools=["file_read", "file_write", "file_patch", "file_search", "terminal_exec"],
            max_permission_tier=PermissionTier.PRIVILEGED,
            registry=registry,
            blackboard=blackboard
        )


class BrowserAgent(SpecialistAgent):
    def __init__(self, registry: ToolRegistry, blackboard: BlackboardArtifactStore):
        super().__init__(
            role="BROWSER_AGENT",
            description="Autonomous web interactions, form extraction, navigation, and DOM inspection.",
            allowed_tools=["browser_navigate"],
            max_permission_tier=PermissionTier.SAFE,
            registry=registry,
            blackboard=blackboard
        )


class TestingAgent(SpecialistAgent):
    def __init__(self, registry: ToolRegistry, blackboard: BlackboardArtifactStore):
        super().__init__(
            role="TESTING_AGENT",
            description="Automated unit and integration test runner, syntax verification, and assertion checks.",
            allowed_tools=["terminal_exec", "file_read"],
            max_permission_tier=PermissionTier.PRIVILEGED,
            registry=registry,
            blackboard=blackboard
        )


class SecurityAgent(SpecialistAgent):
    def __init__(self, registry: ToolRegistry, blackboard: BlackboardArtifactStore):
        super().__init__(
            role="SECURITY_AGENT",
            description="Windows Sandbox boundary audits, privilege escalation checks, and token validation.",
            allowed_tools=["file_read"],
            max_permission_tier=PermissionTier.SAFE,
            registry=registry,
            blackboard=blackboard
        )

    def audit_command_safety(self, command: str) -> Dict[str, Any]:
        from july_distribution.client.sandbox.validator import CommandSecurityValidator
        valid, reason = CommandSecurityValidator.validate(command)
        return {"safe": valid, "reason": reason}


class FileAgent(SpecialistAgent):
    def __init__(self, registry: ToolRegistry, blackboard: BlackboardArtifactStore):
        super().__init__(
            role="FILE_AGENT",
            description="Filesystem organization, search, atomic reads/writes, and artifact generation.",
            allowed_tools=["file_read", "file_write", "file_patch", "file_search"],
            max_permission_tier=PermissionTier.PRIVILEGED,
            registry=registry,
            blackboard=blackboard
        )


class JulyMainCoordinator:
    """
    Coordinator agent: Analyzes intent, decomposes the objective, delegates
    assignments in parallel or sequentially to specialist agents, and aggregates results.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()
        self.blackboard = BlackboardArtifactStore()
        self.specialists: Dict[str, SpecialistAgent] = {
            "RESEARCH": ResearchAgent(self.registry, self.blackboard),
            "CODING": CodingAgent(self.registry, self.blackboard),
            "BROWSER": BrowserAgent(self.registry, self.blackboard),
            "TESTING": TestingAgent(self.registry, self.blackboard),
            "SECURITY": SecurityAgent(self.registry, self.blackboard),
            "FILE": FileAgent(self.registry, self.blackboard)
        }
        self.message_history: List[AgentMessage] = []

    def dispatch_parallel(self, assignments: List[AgentTaskAssignment]) -> List[Dict[str, Any]]:
        """Executes multiple agent assignments concurrently in independent threads."""
        results = []
        with ThreadPoolExecutor(max_workers=min(4, len(assignments))) as executor:
            future_to_assign = {}
            for assign in assignments:
                specialist = self.specialists.get(assign.agent_role.upper())
                if specialist:
                    f = executor.submit(specialist.execute_assignment, assign)
                    future_to_assign[f] = assign
                else:
                    results.append({"success": False, "error": f"Specialist '{assign.agent_role}' not recognized."})

            for f in as_completed(future_to_assign):
                results.append(f.result())

        return results

    def post_message(self, sender: str, recipient: str, content: str) -> AgentMessage:
        msg = AgentMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            sender_role=sender,
            recipient_role=recipient,
            content=content
        )
        self.message_history.append(msg)
        return msg

    def list_swarm_status(self) -> Dict[str, Any]:
        return {
            "coordinator": "JULY_MAIN",
            "active_specialists": [
                {
                    "role": s.role,
                    "description": s.description,
                    "allowed_tools": list(s.allowed_tools),
                    "permission_tier": s.max_permission_tier.value
                }
                for s in self.specialists.values()
            ],
            "total_artifacts": len(self.blackboard.list_artifacts()),
            "message_count": len(self.message_history)
        }
