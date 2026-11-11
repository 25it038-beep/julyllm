"""
HS AI SOLUTIONS — MODULAR TOOL INTERFACE & METADATA
Module: hs_ecosystem.agent.tools.base
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM
"""

from __future__ import annotations
import json
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


class ToolCategory(str, Enum):
    TERMINAL = "TERMINAL"
    FILESYSTEM = "FILESYSTEM"
    BROWSER = "BROWSER"
    COMPUTER_USE = "COMPUTER_USE"
    WEB = "WEB"
    MEDIA = "MEDIA"
    REASONING = "REASONING"


class PermissionTier(str, Enum):
    SAFE = "SAFE"
    PRIVILEGED = "PRIVILEGED"
    DESTRUCTIVE = "DESTRUCTIVE"


@dataclass
class ToolResult:
    success: bool
    output: Any
    error: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """Abstract base class for all autonomous agent tools."""

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        permission_tier: PermissionTier = PermissionTier.SAFE,
        timeout_seconds: float = 30.0
    ):
        self.name = name
        self.description = description
        self.category = category
        self.permission_tier = permission_tier
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for tool arguments."""
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Executes the tool with given arguments."""
        pass

    def to_schema(self) -> Dict[str, Any]:
        """Generates OpenAI / Hermes standard function definition."""
        return {
            "name": self.name,
            "description": f"[{self.category.value} | {self.permission_tier.value}] {self.description}",
            "parameters": self.get_parameters_schema()
        }
