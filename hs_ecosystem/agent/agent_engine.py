"""
HS AI SOLUTIONS — SHARED AUTONOMOUS AGENT ORCHESTRATOR
Module: hs_ecosystem.agent.agent_engine
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Permits both JULY LLM and GRAVITY LLM to operate as autonomous agents
using permission-controlled tool routing.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .tool_router import SharedToolRouter


@dataclass
class AgentStep:
    step_number: int
    thought: str
    action_tool: Optional[str]
    action_args: Dict[str, Any]
    observation: Optional[str]
    status: str  # "completed", "permission_pending", "failed"


@dataclass
class AgentExecutionResult:
    goal: str
    model_used: str
    steps: List[AgentStep]
    final_output: str
    total_duration_sec: float
    success: bool


class SharedAgentEngine:
    """
    Multi-step autonomous agent engine.
    Compatible with both July and Gravity models.
    """

    def __init__(self, tool_router: Optional[SharedToolRouter] = None):
        self.tool_router = tool_router or SharedToolRouter()

    def execute_plan(
        self,
        goal: str,
        model_id: str,
        steps_plan: List[Dict[str, Any]],
        auth_tokens: Optional[Dict[str, str]] = None
    ) -> AgentExecutionResult:
        t0 = time.time()
        executed_steps = []
        tokens = auth_tokens or {}

        for idx, s in enumerate(steps_plan, start=1):
            tool_name = s.get("tool")
            args = s.get("arguments", {})
            thought = s.get("thought", f"Step {idx}: Executing {tool_name}")

            token = tokens.get(tool_name) or args.get("token")
            res = self.tool_router.execute_tool_call(tool_name, args, auth_token=token)

            status = "completed" if res.get("success") else ("permission_pending" if res.get("error") == "PERMISSION_REQUIRED" else "failed")
            obs = json.dumps(res.get("details" if status == "permission_pending" else "content" or res), indent=2) if res else ""

            step_obj = AgentStep(
                step_number=idx,
                thought=thought,
                action_tool=tool_name,
                action_args=args,
                observation=obs[:500],
                status=status
            )
            executed_steps.append(step_obj)

            if status == "permission_pending":
                break

        elapsed = round(time.time() - t0, 3)
        all_passed = all(st.status == "completed" for st in executed_steps)

        return AgentExecutionResult(
            goal=goal,
            model_used=model_id,
            steps=executed_steps,
            final_output=f"Agent plan execution finished with {len(executed_steps)} step(s).",
            total_duration_sec=elapsed,
            success=all_passed
        )
