"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.network
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Enforces Windows Sandbox Network Security:
- Policies: OFFLINE (default), ALLOWLIST, ONLINE
- Pre-execution network command detection and blocking
- Windows Advanced Firewall rules (JulySandbox-Block-Outbound)
- Connection and network event logging
- Block all inbound connections to sandbox processes
"""

from __future__ import annotations
import os
import re
import sys
import time
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class NetworkPolicyType:
    OFFLINE = "OFFLINE"
    ALLOWLIST = "ALLOWLIST"
    ONLINE = "ONLINE"


class SandboxNetworkPolicy:
    """
    Controls network connectivity for sandbox processes.
    Enforces OFFLINE by default.
    """

    FIREWALL_RULE_OUTBOUND = "JulySandbox-Block-Outbound"
    FIREWALL_RULE_INBOUND = "JulySandbox-Block-Inbound"

    # Known network tools & patterns in commands
    NETWORK_PATTERNS = [
        r"\bcurl\b", r"\bwget\b", r"\binvoke-webrequest\b", r"\biwr\b",
        r"\binvoke-restmethod\b", r"\birm\b", r"\bstart-bitstransfer\b",
        r"\bnetsh\b", r"\bping\b", r"\btracert\b", r"\bftp\b", r"\btelnet\b",
        r"\bssh\b", r"\bscp\b", r"\bsftp\b", r"\bnc\b", r"\bncat\b",
        r"\btest-netconnection\b", r"\btnc\b",
        r"\burllib\b", r"\brequests\b", r"\bhttpx\b", r"\baiohttp\b",
        r"\bsocket\b", r"\bhttp\.client\b"
    ]

    def __init__(self, logs_dir: Optional[Path] = None, default_policy: str = NetworkPolicyType.OFFLINE):
        self.policy = default_policy.upper()
        self.logs_dir = logs_dir
        self.allowlist_domains: List[str] = ["localhost", "127.0.0.1", "pypi.org", "files.pythonhosted.org"]
        self.network_log_file = (logs_dir / "network.log") if logs_dir else None

    def set_policy(self, policy: str):
        p_norm = policy.upper().strip()
        if p_norm not in (NetworkPolicyType.OFFLINE, NetworkPolicyType.ALLOWLIST, NetworkPolicyType.ONLINE):
            raise ValueError(f"Unknown network policy: {policy}. Must be OFFLINE, ALLOWLIST, or ONLINE.")
        self.policy = p_norm
        self.log_event("POLICY_CHANGE", f"Network policy updated to: {self.policy}")

    def add_allowed_domain(self, domain: str):
        d = domain.lower().strip()
        if d and d not in self.allowlist_domains:
            self.allowlist_domains.append(d)
            self.log_event("ALLOWLIST_ADD", f"Added domain: {d}")

    def log_event(self, event_type: str, details: str, destination: Optional[str] = None):
        """Records network events and connection attempts in audit log."""
        if not self.network_log_file:
            return

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "policy": self.policy,
            "destination": destination or "none",
            "details": details
        }
        try:
            with open(self.network_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{self.policy}] [{event_type}] {details} (dest: {destination or 'N/A'})\n")
        except Exception:
            pass

    def inspect_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Evaluates command string to verify if it complies with the current network policy.
        Returns (is_allowed, reason_if_blocked).
        """
        cmd_lower = command.lower()

        # Check if command appears to initiate network traffic
        has_network_token = False
        matched_token = ""
        for pat in self.NETWORK_PATTERNS:
            m = re.search(pat, cmd_lower)
            if m:
                has_network_token = True
                matched_token = m.group(0)
                break

        if not has_network_token:
            return True, None

        # Network token was detected
        if self.policy == NetworkPolicyType.OFFLINE:
            reason = f"Network access is blocked by policy (OFFLINE). Command references network utility '{matched_token}'."
            self.log_event("BLOCKED_OFFLINE", reason, destination=matched_token)
            return False, reason

        if self.policy == NetworkPolicyType.ALLOWLIST:
            # Check if command refers to an unauthorized domain/URL
            urls = re.findall(r"https?://([a-zA-Z0-9\.\-]+)", cmd_lower)
            for u in urls:
                if not any(u == d or u.endswith("." + d) for d in self.allowlist_domains):
                    reason = f"Destination domain '{u}' is not in sandbox allowlist ({', '.join(self.allowlist_domains)})."
                    self.log_event("BLOCKED_ALLOWLIST", reason, destination=u)
                    return False, reason
            self.log_event("ALLOWED_ALLOWLIST", f"Command passed allowlist filter: {command[:100]}")
            return True, None

        # ONLINE
        self.log_event("ALLOWED_ONLINE", f"Command executed under ONLINE policy: {command[:100]}")
        return True, None

    def get_firewall_status(self) -> Dict[str, Any]:
        """Checks whether Windows Advanced Firewall rules exist for JulySandbox."""
        ps_check = (
            "$rOut = Get-NetFirewallRule -Name 'JulySandbox-Block-Outbound' -ErrorAction SilentlyContinue; "
            "$rIn = Get-NetFirewallRule -Name 'JulySandbox-Block-Inbound' -ErrorAction SilentlyContinue; "
            "$res = [PSCustomObject]@{"
            "  OutboundBlockExists = ($null -ne $rOut);"
            "  OutboundEnabled = if ($rOut) { $rOut.Enabled } else { $false };"
            "  InboundBlockExists = ($null -ne $rIn);"
            "  InboundEnabled = if ($rIn) { $rIn.Enabled } else { $false };"
            "}; "
            "$res | ConvertTo-Json -Compress"
        )
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_check],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0 and proc.stdout.strip():
                import json
                data = json.loads(proc.stdout.strip())
                return {
                    "outbound_rule_active": bool(data.get("OutboundBlockExists") and data.get("OutboundEnabled")),
                    "inbound_rule_active": bool(data.get("InboundBlockExists") and data.get("InboundEnabled")),
                    "policy": self.policy,
                    "allowlist_count": len(self.allowlist_domains)
                }
        except Exception:
            pass

        return {
            "outbound_rule_active": False,
            "inbound_rule_active": False,
            "policy": self.policy,
            "allowlist_count": len(self.allowlist_domains)
        }

    def generate_firewall_powershell(self) -> str:
        """Generates script to register strict Windows Firewall rules for the sandbox."""
        return f"""# HS AI Solutions - July Sandbox Firewall Rules
$ErrorActionPreference = 'SilentlyContinue'

Write-Host '[*] Configuring July Sandbox Windows Advanced Firewall Rules...' -ForegroundColor Cyan

# Block all inbound to JulySandbox
if (-not (Get-NetFirewallRule -Name '{self.FIREWALL_RULE_INBOUND}')) {{
    New-NetFirewallRule -Name '{self.FIREWALL_RULE_INBOUND}' `
        -DisplayName 'July Sandbox - Block All Inbound' `
        -Description 'Blocks unsolicited inbound connections to July Sandbox processes.' `
        -Direction Inbound -Action Block -Enabled True -Profile Any | Out-Null
    Write-Host '[✓] Inbound Block rule active.' -ForegroundColor Green
}}

# Block outbound if OFFLINE policy requested
if (-not (Get-NetFirewallRule -Name '{self.FIREWALL_RULE_OUTBOUND}')) {{
    New-NetFirewallRule -Name '{self.FIREWALL_RULE_OUTBOUND}' `
        -DisplayName 'July Sandbox - Block All Outbound' `
        -Description 'Blocks outbound traffic from July Sandbox processes.' `
        -Direction Outbound -Action Block -Enabled True -Profile Any | Out-Null
    Write-Host '[✓] Outbound Block rule active.' -ForegroundColor Green
}}
"""
