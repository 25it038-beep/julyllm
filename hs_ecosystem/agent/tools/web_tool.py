"""
HS AI SOLUTIONS — AUTONOMOUS WEB SEARCH & RESEARCH TOOL
Module: hs_ecosystem.agent.tools.web_tool
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM
"""

from __future__ import annotations
import time
from typing import Dict, Any, Optional
from .base import BaseTool, ToolCategory, PermissionTier, ToolResult
from july_distribution.client.web_search import live_duckduckgo_search


class WebSearchResearchTool(BaseTool):
    """Executes live web searches and formats verified knowledge."""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Searches DuckDuckGo for live facts, documentation, packages and research data.",
            category=ToolCategory.WEB,
            permission_tier=PermissionTier.SAFE,
            timeout_seconds=20.0
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query terms."},
                "max_results": {"type": "integer", "description": "Number of results (1-10).", "default": 5}
            },
            "required": ["query"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        query = arguments.get("query", "").strip()
        max_results = int(arguments.get("max_results", 5))

        if not query:
            return ToolResult(success=False, output=[], error="Empty query provided.", duration_seconds=round(time.time() - t0, 3))

        try:
            results = live_duckduckgo_search(query, max_results=max_results)
            return ToolResult(
                success=True,
                output=results,
                duration_seconds=round(time.time() - t0, 3),
                metadata={"count": len(results), "query": query}
            )
        except Exception as e:
            return ToolResult(success=False, output=[], error=f"Search failed: {e}", duration_seconds=round(time.time() - t0, 3))
