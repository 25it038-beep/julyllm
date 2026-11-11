"""
HS AI SOLUTIONS — MODULAR TOOL REGISTRY & DISPATCHER
Module: hs_ecosystem.agent.tool_registry
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM
"""

from __future__ import annotations
import json
import time
from typing import Dict, Any, List, Optional
from .tools.base import BaseTool, ToolCategory, PermissionTier, ToolResult
from .tools.terminal_tool import SandboxedTerminalTool
from .tools.filesystem_tool import FileReadTool, FileWriteTool, FilePatchTool, FileSearchTool
from .tools.browser_tool import BrowserAutomationTool
from .tools.computer_use_tool import ComputerUseTool
from .tools.media_tool import MediaVoiceTool
from .tools.web_tool import WebSearchResearchTool
from .permission_manager import AgentPermissionManager


class ToolRegistry:
    """Central registry for all tools in the July Autonomous Agent Platform."""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.permission_mgr = AgentPermissionManager()
        self._register_default_tools()

    def _register_default_tools(self):
        default_tools = [
            SandboxedTerminalTool(),
            FileReadTool(),
            FileWriteTool(),
            FilePatchTool(),
            FileSearchTool(),
            BrowserAutomationTool(),
            ComputerUseTool(),
            MediaVoiceTool(),
            WebSearchResearchTool()
        ]
        for t in default_tools:
            self.register(t)

    def register(self, tool: BaseTool):
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions for all registered tools."""
        return [tool.to_schema() for tool in self.tools.values()]

    def execute(self, tool_name: str, arguments: Dict[str, Any], auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Dispatches tool execution with strict permission evaluation."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found."}

        # Permission evaluation
        eval_res = self.permission_mgr.evaluate_request(
            tool_name,
            arguments,
            provided_token=auth_token or arguments.get("token")
        )
        if not eval_res["allowed"]:
            return {
                "success": False,
                "error": "PERMISSION_REQUIRED",
                "details": eval_res
            }

        # Execution
        result: ToolResult = tool.execute(arguments)
        return result.to_dict()
