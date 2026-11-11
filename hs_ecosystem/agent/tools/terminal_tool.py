"""
HS AI SOLUTIONS — SANDBOXED TERMINAL & COMMAND TOOL
Module: hs_ecosystem.agent.tools.terminal_tool
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM
"""

from __future__ import annotations
import time
from typing import Dict, Any, Optional
from .base import BaseTool, ToolCategory, PermissionTier, ToolResult
from july_distribution.client.sandbox import SandboxManager, SecurityViolation


class SandboxedTerminalTool(BaseTool):
    """Executes shell commands strictly inside the Windows Sandbox Execution Engine."""

    def __init__(self):
        super().__init__(
            name="terminal_exec",
            description="Executes a PowerShell or CMD command safely inside the Windows Sandbox (Job Object + restricted token).",
            category=ToolCategory.TERMINAL,
            permission_tier=PermissionTier.PRIVILEGED,
            timeout_seconds=30.0
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute."
                },
                "timeout": {
                    "type": "number",
                    "description": "Execution timeout in seconds (default 30.0).",
                    "default": 30.0
                }
            },
            "required": ["command"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        command = arguments.get("command", "").strip()
        timeout = float(arguments.get("timeout", self.timeout_seconds))

        if not command:
            return ToolResult(
                success=False,
                output="",
                error="Empty command provided.",
                duration_seconds=round(time.time() - t0, 3)
            )

        try:
            sbx = SandboxManager.get_instance()
            res = sbx.execute(command, timeout=timeout)
            dur = round(time.time() - t0, 3)

            if res.security_blocked:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"SECURITY VIOLATION: {res.violation_reason}",
                    duration_seconds=dur,
                    metadata={"blocked": True, "reason": res.violation_reason}
                )

            success = (res.exit_code == 0)
            output = res.stdout if success or res.stdout else res.stderr
            return ToolResult(
                success=success,
                output=output,
                error=res.stderr if not success and not output else None,
                duration_seconds=dur,
                metadata={
                    "exit_code": res.exit_code,
                    "peak_memory_mb": res.peak_memory_mb,
                    "job_object_active": True
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Terminal execution error: {e}",
                duration_seconds=round(time.time() - t0, 3)
            )
