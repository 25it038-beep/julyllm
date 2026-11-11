"""
HS AI SOLUTIONS — AUTONOMOUS BROWSER AUTOMATION TOOL
Module: hs_ecosystem.agent.tools.browser_tool
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM
"""

from __future__ import annotations
import re
import time
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
from .base import BaseTool, ToolCategory, PermissionTier, ToolResult


class BrowserAutomationTool(BaseTool):
    """Navigates web pages, extracts DOM elements, forms, and renders clean markdown."""

    def __init__(self):
        super().__init__(
            name="browser_navigate",
            description="Navigates to a URL, parses web content, extracts DOM text, links, headings and forms.",
            category=ToolCategory.BROWSER,
            permission_tier=PermissionTier.SAFE,
            timeout_seconds=20.0
        )
        self.last_url: Optional[str] = None
        self.last_dom: Optional[BeautifulSoup] = None

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "extract_text", "extract_links", "extract_forms"],
                    "description": "Action to perform on browser."
                },
                "url": {
                    "type": "string",
                    "description": "Target HTTP/HTTPS or file URL."
                }
            },
            "required": ["action"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        action = arguments.get("action", "navigate")
        url = arguments.get("url", self.last_url)

        if not url:
            return ToolResult(success=False, output="", error="No URL provided.", duration_seconds=round(time.time() - t0, 3))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JulyAI/2.0 (HS AI Solutions)"
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw_html = resp.read().decode("utf-8", errors="replace")

            soup = BeautifulSoup(raw_html, "html.parser")
            self.last_url = url
            self.last_dom = soup

            # Strip script and style elements
            for s in soup(["script", "style", "noscript", "svg"]):
                s.decompose()

            if action in ("navigate", "extract_text"):
                title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
                text_content = "\n".join([line.strip() for line in soup.get_text().splitlines() if line.strip()])
                preview = text_content[:4000]

                return ToolResult(
                    success=True,
                    output={
                        "title": title,
                        "url": url,
                        "content_preview": preview,
                        "char_count": len(text_content)
                    },
                    duration_seconds=round(time.time() - t0, 3),
                    metadata={"url": url, "title": title}
                )

            elif action == "extract_links":
                links = []
                for a in soup.find_all("a", href=True):
                    href = urllib.parse.urljoin(url, a["href"])
                    text = a.get_text().strip() or href
                    if href.startswith(("http://", "https://")):
                        links.append({"text": text, "url": href})
                    if len(links) >= 50:
                        break
                return ToolResult(
                    success=True,
                    output=links,
                    duration_seconds=round(time.time() - t0, 3),
                    metadata={"count": len(links)}
                )

            elif action == "extract_forms":
                forms_data = []
                for idx, f in enumerate(soup.find_all("form"), start=1):
                    inputs = []
                    for inp in f.find_all(["input", "button", "textarea", "select"]):
                        inputs.append({
                            "tag": inp.name,
                            "type": inp.get("type", "text"),
                            "name": inp.get("name"),
                            "value": inp.get("value")
                        })
                    forms_data.append({
                        "form_index": idx,
                        "action": f.get("action"),
                        "method": f.get("method", "get").upper(),
                        "inputs": inputs
                    })
                return ToolResult(
                    success=True,
                    output=forms_data,
                    duration_seconds=round(time.time() - t0, 3),
                    metadata={"form_count": len(forms_data)}
                )

            return ToolResult(success=False, output="", error=f"Unknown browser action: {action}", duration_seconds=round(time.time() - t0, 3))

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Browser navigation error: {e}", duration_seconds=round(time.time() - t0, 3))
