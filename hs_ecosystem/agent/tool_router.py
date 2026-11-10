"""
HS AI SOLUTIONS — STANDARDIZED SHARED TOOL ROUTER
Module: hs_ecosystem.agent.tool_router
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Standardized interface:
Model -> Tool Router -> Permission Manager -> Tool -> Result -> Model.
"""

from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from .permission_manager import AgentPermissionManager
from july_distribution.client.reasoning.math_verifier import MathematicalIntelligenceEngine
from july_distribution.client.reasoning.code_verifier import ProgrammingIntelligenceEngine
from july_distribution.client.web_search import live_duckduckgo_search


class SharedToolRouter:
    """Dispatches tool calls from July or Gravity through PermissionManager."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.permission_mgr = AgentPermissionManager()
        self.math_engine = MathematicalIntelligenceEngine()
        self.code_engine = ProgrammingIntelligenceEngine()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """JSON schema tool definitions for model function calling."""
        return [
            {
                "name": "file_read",
                "description": "Reads text content of a file within the workspace safely.",
                "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}
            },
            {
                "name": "file_write",
                "description": "Writes or overwrites a file. Requires PRIVILEGED authorization token.",
                "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}, "token": {"type": "string"}}, "required": ["file_path", "content"]}
            },
            {
                "name": "file_delete",
                "description": "Deletes a file from workspace. Requires DESTRUCTIVE authorization token.",
                "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}, "token": {"type": "string"}}, "required": ["file_path"]}
            },
            {
                "name": "execute_code_sandbox",
                "description": "Executes Python or PowerShell code inside a sandboxed isolated process.",
                "parameters": {"type": "object", "properties": {"language": {"type": "string"}, "code": {"type": "string"}}, "required": ["language", "code"]}
            },
            {
                "name": "cas_solve",
                "description": "Performs formal Computer Algebra System symbolic equation solving and calculus via SymPy.",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            },
            {
                "name": "web_search",
                "description": "Searches the live web for verified facts using DuckDuckGo.",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            },
            {
                "name": "system_diagnostics",
                "description": "Inspects host CPU, RAM, GPU VRAM, and platform hardware telemetry.",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

    def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes: Model -> Tool Router -> Permission Manager -> Tool -> Result -> Model.
        """
        # Step 1: Permission evaluation
        perm = self.permission_mgr.evaluate_request(tool_name, arguments, provided_token=auth_token or arguments.get("token"))
        if not perm["allowed"]:
            return {
                "success": False,
                "error": "PERMISSION_REQUIRED",
                "details": perm
            }

        # Step 2: Tool execution
        try:
            if tool_name == "file_read":
                rel_path = arguments.get("file_path", "")
                target = (self.workspace_root / rel_path).resolve()
                if not target.exists() or not target.is_file():
                    return {"success": False, "error": f"File not found: {rel_path}"}
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return {"success": True, "file_path": str(target), "content": content[:10000]}

            elif tool_name == "file_write":
                rel_path = arguments.get("file_path", "")
                content = arguments.get("content", "")
                target = (self.workspace_root / rel_path).resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"success": True, "file_path": str(target), "bytes_written": len(content.encode("utf-8"))}

            elif tool_name == "file_delete":
                rel_path = arguments.get("file_path", "")
                target = (self.workspace_root / rel_path).resolve()
                if target.exists() and target.is_file():
                    target.unlink()
                    return {"success": True, "file_path": str(target), "action": "deleted"}
                return {"success": False, "error": "File does not exist."}

            elif tool_name == "execute_code_sandbox":
                lang = arguments.get("language", "python")
                code = arguments.get("code", "")
                res = self.code_engine.verify_code(code, lang)
                return {
                    "success": res.is_valid_syntax,
                    "language": res.language,
                    "sandbox_executed": res.sandbox_executed,
                    "sandbox_passed": res.sandbox_passed,
                    "sandbox_output": res.sandbox_output,
                    "syntax_warnings": res.static_warnings,
                    "complexity": res.time_complexity
                }

            elif tool_name == "cas_solve":
                query = arguments.get("query", "")
                res = self.math_engine.analyze_mathematical_query(query)
                return {
                    "success": res.is_valid,
                    "type": res.problem_type,
                    "exact_solution": res.exact_solution,
                    "uniquely_determined": res.uniquely_determined_vars,
                    "underdetermined": res.underdetermined_vars,
                    "unconstrained": res.unconstrained_vars,
                    "notes": res.verification_notes
                }

            elif tool_name == "web_search":
                q = arguments.get("query", "")
                results = live_duckduckgo_search(q, max_results=3)
                return {"success": True, "query": q, "results": results}

            elif tool_name == "system_diagnostics":
                from ..core.hardware import UniversalHardwareEngine
                hw = UniversalHardwareEngine.detect_hardware()
                return {"success": True, "hardware": hw.__dict__}

            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
