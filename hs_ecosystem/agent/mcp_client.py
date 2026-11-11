"""
HS AI SOLUTIONS — MODEL CONTEXT PROTOCOL (MCP) CLIENT
Module: hs_ecosystem.agent.mcp_client
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 13:
- JSON-RPC stdio client connecting to MCP servers
- Dynamic tool discovery (`tools/list`)
- Execution routing (`tools/call`)
- Dynamic registration into ToolRegistry
"""

from __future__ import annotations
import os
import sys
import json
import time
import subprocess
from typing import Dict, Any, List, Optional
from .tools.base import BaseTool, ToolCategory, PermissionTier, ToolResult
from .tool_registry import ToolRegistry


class MCPRemoteTool(BaseTool):
    """Wraps an MCP server tool into July ToolRegistry."""

    def __init__(self, mcp_client: MCPClient, name: str, description: str, schema: Dict[str, Any]):
        super().__init__(
            name=name,
            description=f"[MCP] {description}",
            category=ToolCategory.REASONING,
            permission_tier=PermissionTier.PRIVILEGED
        )
        self.mcp_client = mcp_client
        self.schema = schema

    def get_parameters_schema(self) -> Dict[str, Any]:
        return self.schema

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        res = self.mcp_client.call_tool(self.name, arguments)
        return ToolResult(
            success=not bool(res.get("isError")),
            output=res.get("content", ""),
            error=res.get("error"),
            duration_seconds=round(time.time() - t0, 3)
        )


class MCPClient:
    """Connects to external MCP servers via stdio and queries tools."""

    def __init__(self, command: str, args: List[str]):
        self.command = command
        self.args = args
        self.process: Optional[subprocess.Popen] = None
        self._req_id = 0

    def start(self):
        full_cmd = [self.command] + self.args
        self.process = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def send_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.process or self.process.poll() is not None:
            return {"error": "MCP server process is not running."}

        self._req_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": method,
            "params": params or {}
        }
        line = json.dumps(req) + "\n"
        self.process.stdin.write(line)
        self.process.stdin.flush()

        resp_line = self.process.stdout.readline()
        if not resp_line:
            return {"error": "Empty response from MCP server."}
        try:
            return json.loads(resp_line)
        except Exception as e:
            return {"error": f"Invalid JSON response: {e}"}

    def list_tools(self) -> List[Dict[str, Any]]:
        resp = self.send_rpc("tools/list")
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.send_rpc("tools/call", {"name": name, "arguments": arguments})
        if "error" in resp:
            return {"isError": True, "error": resp["error"]}
        return resp.get("result", {})

    def register_into_registry(self, registry: ToolRegistry):
        tools = self.list_tools()
        for t in tools:
            remote_tool = MCPRemoteTool(
                mcp_client=self,
                name=t.get("name", "unnamed_mcp_tool"),
                description=t.get("description", ""),
                schema=t.get("inputSchema", {})
            )
            registry.register(remote_tool)

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process = None
