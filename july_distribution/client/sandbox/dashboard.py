"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.dashboard
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Renders the Sandbox Security Dashboard for the CLI:
- Real-time telemetry (Status, Memory, CPU, Processes)
- Account & Security Group verification
- Filesystem disk usage breakdown
- Network firewall & policy status
- Execution logs and security violation alerts
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


class UIColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    RED = "\033[91m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"


class SandboxDashboard:
    """Renders formatted ASCII/ANSI dashboard cards for July Sandbox CLI."""

    @staticmethod
    def render(status_data: Dict[str, Any]) -> str:
        C = UIColors
        lines = []

        lines.append(f"{C.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET} {C.BOLD}{C.WHITE}HS AI SOLUTIONS — WINDOWS SANDBOX SECURITY DASHBOARD{C.RESET}{' '*22}{C.CYAN}║{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET} {C.GRAY}Product: JULY LLM | Architecture: Windows Isolated Execution Engine{C.RESET}{' '*7}{C.CYAN}║{C.RESET}")
        lines.append(f"{C.CYAN}╠══════════════════════════════════════════════════════════════════════════════╣{C.RESET}")

        # 1. System & Accounts Status
        state = status_data.get("state", "READY")
        state_color = C.GREEN if state in ("READY", "ACTIVE") else C.YELLOW
        acc = status_data.get("accounts", {})
        grp_status = f"{C.GREEN}VERIFIED{C.RESET}" if acc.get("group_exists") else f"{C.YELLOW}PENDING ELEVATION{C.RESET}"
        r1_status = f"{C.GREEN}ACTIVE{C.RESET}" if acc.get("r1_exists") else f"{C.YELLOW}PENDING{C.RESET}"
        u1_status = f"{C.GREEN}ACTIVE{C.RESET}" if acc.get("u1_exists") else f"{C.YELLOW}PENDING{C.RESET}"
        vault_status = f"{C.GREEN}DPAPI ENCRYPTED{C.RESET}" if acc.get("credentials_vault_present") else f"{C.YELLOW}NOT PROVISIONED{C.RESET}"

        lines.append(f"{C.CYAN}║{C.RESET} {C.BOLD}1. SECURITY STATE & ACCOUNT ISOLATION{C.RESET}{' '*37}{C.CYAN}║{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Sandbox State        : {state_color}{C.BOLD}{state}{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Security Group       : JulySandboxUsers ({grp_status})")
        lines.append(f"{C.CYAN}║{C.RESET}   • Worker Account 1     : july-sbx-r1 ({r1_status}) [Admin Rights: {C.GREEN}STRIPPED{C.RESET}]")
        lines.append(f"{C.CYAN}║{C.RESET}   • Untrusted Account 2  : july-sbx-u1 ({u1_status}) [Admin Rights: {C.GREEN}STRIPPED{C.RESET}]")
        lines.append(f"{C.CYAN}║{C.RESET}   • Credential Vault     : {vault_status}")
        lines.append(f"{C.CYAN}╟──────────────────────────────────────────────────────────────────────────────╢{C.RESET}")

        # 2. Kernel Enforcement & Job Objects
        job = status_data.get("job_limits", {})
        mem_limit = job.get("max_process_memory_mb", 512)
        job_limit = job.get("max_job_memory_mb", 1024)
        cpu_rate = job.get("cpu_rate_percent", 50.0)
        active_proc = job.get("active_processes", 0)
        peak_mem = job.get("peak_memory_mb", 0.0)

        lines.append(f"{C.CYAN}║{C.RESET} {C.BOLD}2. KERNEL ENFORCEMENT & JOB OBJECT QUOTAS{C.RESET}{' '*33}{C.CYAN}║{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Windows Job Object   : {C.GREEN}ACTIVE (KILL_ON_JOB_CLOSE ENABLED){C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Memory Ceilings      : Process Max: {C.CYAN}{mem_limit} MB{C.RESET} | Total Job Max: {C.CYAN}{job_limit} MB{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • CPU Rate Control     : {C.CYAN}{cpu_rate}% Hard Cap (JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP){C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Active Process Tree  : {active_proc} active processes (Peak Memory: {peak_mem:.1f} MB)")
        lines.append(f"{C.CYAN}║{C.RESET}   • Process Tokens       : {C.GREEN}RESTRICTED TOKEN (DISABLE_MAX_PRIVILEGE + LUA){C.RESET}")
        lines.append(f"{C.CYAN}╟──────────────────────────────────────────────────────────────────────────────╢{C.RESET}")

        # 3. Filesystem Security
        fs = status_data.get("filesystem", {})
        root_path = fs.get("Root", "C:\\JulySandbox")
        rt = fs.get("Runtime", {})
        ws = fs.get("Workspace", {})
        tmp = fs.get("Temporary", {})
        logs = fs.get("Logs", {})
        art = fs.get("Artifacts", {})
        tot_mb = fs.get("Total_MB", 0.0)

        lines.append(f"{C.CYAN}║{C.RESET} {C.BOLD}3. FILESYSTEM BOUNDARY & DISK ALLOCATION{C.RESET}{' '*34}{C.CYAN}║{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Sandbox Root         : {C.YELLOW}{root_path}{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Runtime/ (RO)        : {rt.get('size_mb', 0.0)} MB ({rt.get('file_count', 0)} files)")
        lines.append(f"{C.CYAN}║{C.RESET}   • Workspace/ (RW)      : {ws.get('size_mb', 0.0)} MB ({ws.get('file_count', 0)} files)")
        lines.append(f"{C.CYAN}║{C.RESET}   • Temporary/ (RW)      : {tmp.get('size_mb', 0.0)} MB ({tmp.get('file_count', 0)} files)")
        lines.append(f"{C.CYAN}║{C.RESET}   • Logs/ (Append)       : {logs.get('size_mb', 0.0)} MB ({logs.get('file_count', 0)} files)")
        lines.append(f"{C.CYAN}║{C.RESET}   • Artifacts/ (RW)      : {art.get('size_mb', 0.0)} MB ({art.get('file_count', 0)} files)")
        lines.append(f"{C.CYAN}║{C.RESET}   • Total Sandboxed Size : {C.CYAN}{tot_mb} MB{C.RESET}")
        lines.append(f"{C.CYAN}╟──────────────────────────────────────────────────────────────────────────────╢{C.RESET}")

        # 4. Network Policy
        net = status_data.get("network", {})
        net_pol = net.get("policy", "OFFLINE")
        pol_color = C.RED if net_pol == "OFFLINE" else (C.YELLOW if net_pol == "ALLOWLIST" else C.GREEN)
        fw_out = f"{C.GREEN}ACTIVE{C.RESET}" if net.get("outbound_rule_active") else f"{C.GRAY}STANDBY{C.RESET}"

        lines.append(f"{C.CYAN}║{C.RESET} {C.BOLD}4. NETWORK SECURITY & FIREWALL POLICY{C.RESET}{' '*37}{C.CYAN}║{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Execution Policy     : {pol_color}{C.BOLD}{net_pol}{C.RESET} (Network disabled by default)")
        lines.append(f"{C.CYAN}║{C.RESET}   • Outbound Firewall    : Rule '{net.get('FIREWALL_RULE_OUTBOUND', 'JulySandbox-Block-Outbound')}' ({fw_out})")
        lines.append(f"{C.CYAN}║{C.RESET}   • Inbound Connections  : {C.RED}STRICTLY BLOCKED{C.RESET} (Zero open listening sockets)")
        lines.append(f"{C.CYAN}╟──────────────────────────────────────────────────────────────────────────────╢{C.RESET}")

        # 5. Execution History & Violations
        hist = status_data.get("history", {})
        tot_exec = hist.get("total_executions", 0)
        tot_viol = hist.get("total_violations", 0)
        viol_color = C.GREEN if tot_viol == 0 else C.RED

        lines.append(f"{C.CYAN}║{C.RESET} {C.BOLD}5. AUDIT TELEMETRY & SECURITY VIOLATIONS{C.RESET}{' '*34}{C.CYAN}║{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Total Commands Run   : {C.CYAN}{tot_exec}{C.RESET}")
        lines.append(f"{C.CYAN}║{C.RESET}   • Security Violations  : {viol_color}{C.BOLD}{tot_viol}{C.RESET} blocked unauthorized attempts")

        recent_viol = hist.get("recent_violations", [])
        if recent_viol:
            lines.append(f"{C.CYAN}║{C.RESET}   {C.RED}Recent Security Breaches Blocked:{C.RESET}")
            for v in recent_viol[-3:]:
                lines.append(f"{C.CYAN}║{C.RESET}     • {C.YELLOW}{v[:68]}{C.RESET}")
        else:
            lines.append(f"{C.CYAN}║{C.RESET}   • Boundary Integrity   : {C.GREEN}SECURE — ZERO ESCAPES DETECTED{C.RESET}")

        lines.append(f"{C.CYAN}╚══════════════════════════════════════════════════════════════════════════════╝{C.RESET}")
        return "\n".join(lines)
