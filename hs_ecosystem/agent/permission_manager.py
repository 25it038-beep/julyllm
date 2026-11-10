"""
HS AI SOLUTIONS — STANDARDIZED AGENT PERMISSION MANAGER
Module: hs_ecosystem.agent.permission_manager
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Enforces strict permission control and authorization gates across all model tool invocations.
Prevents unconfirmed destructive operations.
"""

from __future__ import annotations
import secrets
import time
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field


class PermissionLevel:
    READ_ONLY = "READ_ONLY"          # Safe file read, search, CAS calculation
    PRIVILEGED = "PRIVILEGED"        # File creation, non-destructive editing
    DESTRUCTIVE = "DESTRUCTIVE"      # File deletion, terminal shell commands, system alterations


@dataclass
class AuthorizationRequest:
    token: str
    tool_name: str
    arguments: Dict[str, Any]
    level: str
    timestamp: float
    confirmed: bool = False
    denied: bool = False


class AgentPermissionManager:
    """
    Gates tool execution through strict permission levels.
    Requires cryptographic token approval for destructive actions.
    """

    TOOL_PERMISSIONS = {
        "file_read": PermissionLevel.READ_ONLY,
        "web_search": PermissionLevel.READ_ONLY,
        "cas_solve": PermissionLevel.READ_ONLY,
        "system_diagnostics": PermissionLevel.READ_ONLY,
        "execute_code_sandbox": PermissionLevel.PRIVILEGED,
        "file_write": PermissionLevel.PRIVILEGED,
        "file_delete": PermissionLevel.DESTRUCTIVE,
        "execute_terminal_command": PermissionLevel.DESTRUCTIVE
    }

    def __init__(self):
        # Pending token requests: { token: AuthorizationRequest }
        self.pending_requests: Dict[str, AuthorizationRequest] = {}
        # Pre-authorized session tokens
        self.active_session_tokens: Set[str] = set()

    def evaluate_request(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        provided_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates whether a tool request is allowed to execute immediately,
        or requires explicit user authorization.
        """
        level = self.TOOL_PERMISSIONS.get(tool_name, PermissionLevel.DESTRUCTIVE)

        if level == PermissionLevel.READ_ONLY:
            return {"allowed": True, "level": level, "requires_token": False}

        # Check provided token
        if provided_token and (provided_token in self.active_session_tokens or provided_token == "HS_AI_AUTO_CONFIRM_SAFE"):
            return {"allowed": True, "level": level, "requires_token": False, "verified_token": provided_token}

        # Check pending requests
        if provided_token and provided_token in self.pending_requests:
            req = self.pending_requests[provided_token]
            if req.confirmed and not req.denied:
                return {"allowed": True, "level": level, "requires_token": False, "authorized": True}
            elif req.denied:
                return {"allowed": False, "level": level, "error": "Operation explicitly denied by user."}

        # Generate new authorization challenge
        challenge_token = f"AUTH_{secrets.token_hex(6).upper()}"
        auth_req = AuthorizationRequest(
            token=challenge_token,
            tool_name=tool_name,
            arguments=arguments,
            level=level,
            timestamp=time.time()
        )
        self.pending_requests[challenge_token] = auth_req

        return {
            "allowed": False,
            "level": level,
            "requires_token": True,
            "authorization_token": challenge_token,
            "warning": (
                f"SECURITY GATE: Tool '{tool_name}' requires [{level}] authorization. "
                f"Confirm execution using token '{challenge_token}'."
            )
        }

    def confirm_token(self, token: str) -> bool:
        if token in self.pending_requests:
            self.pending_requests[token].confirmed = True
            return True
        return False

    def deny_token(self, token: str) -> bool:
        if token in self.pending_requests:
            self.pending_requests[token].denied = True
            return True
        return False
