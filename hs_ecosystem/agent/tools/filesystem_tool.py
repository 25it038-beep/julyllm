"""
HS AI SOLUTIONS — AUTONOMOUS FILESYSTEM & CODE EDITOR TOOLS
Module: hs_ecosystem.agent.tools.filesystem_tool
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM
"""

from __future__ import annotations
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from .base import BaseTool, ToolCategory, PermissionTier, ToolResult
from july_distribution.client.sandbox import SandboxManager, SecurityViolation


class FileReadTool(BaseTool):
    """Safely reads file contents within authorized sandbox boundaries."""

    def __init__(self, workspace_root: Optional[Path] = None):
        super().__init__(
            name="file_read",
            description="Reads the text content of a file within authorized workspace boundaries.",
            category=ToolCategory.FILESYSTEM,
            permission_tier=PermissionTier.SAFE
        )
        self.workspace_root = workspace_root or Path.cwd()

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative or absolute path to file."},
                "max_lines": {"type": "integer", "description": "Maximum number of lines to return (default 500)."}
            },
            "required": ["file_path"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        file_path = arguments.get("file_path", "")
        max_lines = int(arguments.get("max_lines", 500))

        try:
            sbx = SandboxManager.get_instance()
            target = sbx.fs.resolve_and_validate_path(Path(file_path), allow_write=False)
            if not target.exists() or not target.is_file():
                return ToolResult(success=False, output="", error=f"File not found: {file_path}", duration_seconds=round(time.time() - t0, 3))

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)

            return ToolResult(
                success=True,
                output=content,
                duration_seconds=round(time.time() - t0, 3),
                metadata={"file_path": str(target), "line_count": len(lines)}
            )
        except SecurityViolation as sv:
            return ToolResult(success=False, output="", error=f"SECURITY VIOLATION: {sv}", duration_seconds=round(time.time() - t0, 3))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), duration_seconds=round(time.time() - t0, 3))


class FileWriteTool(BaseTool):
    """Safely writes or overwrites file contents with path validation."""

    def __init__(self, workspace_root: Optional[Path] = None):
        super().__init__(
            name="file_write",
            description="Writes or overwrites a file within the workspace. Creates parent directories automatically.",
            category=ToolCategory.FILESYSTEM,
            permission_tier=PermissionTier.PRIVILEGED
        )
        self.workspace_root = workspace_root or Path.cwd()

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to file."},
                "content": {"type": "string", "description": "Full text content to write."}
            },
            "required": ["file_path", "content"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        file_path = arguments.get("file_path", "")
        content = arguments.get("content", "")

        try:
            sbx = SandboxManager.get_instance()
            target = sbx.fs.resolve_and_validate_path(Path(file_path), allow_write=True)
            target.parent.mkdir(parents=True, exist_ok=True)

            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content.encode('utf-8'))} bytes to {target.name}",
                duration_seconds=round(time.time() - t0, 3),
                metadata={"file_path": str(target), "bytes_written": len(content.encode("utf-8"))}
            )
        except SecurityViolation as sv:
            return ToolResult(success=False, output="", error=f"SECURITY VIOLATION: {sv}", duration_seconds=round(time.time() - t0, 3))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), duration_seconds=round(time.time() - t0, 3))


class FilePatchTool(BaseTool):
    """Atomically replaces exact text patterns inside a file."""

    def __init__(self):
        super().__init__(
            name="file_patch",
            description="Replaces target text block with replacement text block inside an existing file.",
            category=ToolCategory.FILESYSTEM,
            permission_tier=PermissionTier.PRIVILEGED
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to file."},
                "target": {"type": "string", "description": "Exact text block to replace."},
                "replacement": {"type": "string", "description": "New text block to insert."}
            },
            "required": ["file_path", "target", "replacement"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        file_path = arguments.get("file_path", "")
        target = arguments.get("target", "")
        replacement = arguments.get("replacement", "")

        try:
            sbx = SandboxManager.get_instance()
            path_obj = sbx.fs.resolve_and_validate_path(Path(file_path), allow_write=True)
            if not path_obj.exists():
                return ToolResult(success=False, output="", error=f"File not found: {file_path}", duration_seconds=round(time.time() - t0, 3))

            with open(path_obj, "r", encoding="utf-8") as f:
                original = f.read()

            if target not in original:
                return ToolResult(success=False, output="", error="Target text block not found in file.", duration_seconds=round(time.time() - t0, 3))

            patched = original.replace(target, replacement, 1)
            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(patched)

            return ToolResult(
                success=True,
                output=f"Successfully patched {path_obj.name}",
                duration_seconds=round(time.time() - t0, 3),
                metadata={"file_path": str(path_obj)}
            )
        except SecurityViolation as sv:
            return ToolResult(success=False, output="", error=f"SECURITY VIOLATION: {sv}", duration_seconds=round(time.time() - t0, 3))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), duration_seconds=round(time.time() - t0, 3))


class FileSearchTool(BaseTool):
    """Searches for files matching wildcard patterns or regex in contents."""

    def __init__(self, workspace_root: Optional[Path] = None):
        super().__init__(
            name="file_search",
            description="Searches directory for filenames matching pattern or content matching regex.",
            category=ToolCategory.FILESYSTEM,
            permission_tier=PermissionTier.SAFE
        )
        self.workspace_root = workspace_root or Path.cwd()

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Filename pattern (e.g. *.py, *config*).", "default": "*"},
                "content_query": {"type": "string", "description": "Optional text to search inside files."}
            }
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        pattern = arguments.get("pattern", "*")
        content_query = arguments.get("content_query")

        matches = []
        try:
            sbx = SandboxManager.get_instance()
            valid_root = sbx.fs.resolve_and_validate_path(self.workspace_root, allow_write=False)

            for p in valid_root.rglob(pattern):
                if p.is_file() and not any(part.startswith((".", "__")) for part in p.parts):
                    if content_query:
                        try:
                            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                                if content_query in f.read():
                                    matches.append(str(p.relative_to(valid_root)))
                        except Exception:
                            continue
                    else:
                        matches.append(str(p.relative_to(valid_root)))

                if len(matches) >= 50:
                    break

            return ToolResult(
                success=True,
                output=matches,
                duration_seconds=round(time.time() - t0, 3),
                metadata={"count": len(matches)}
            )
        except Exception as e:
            return ToolResult(success=False, output=[], error=str(e), duration_seconds=round(time.time() - t0, 3))
