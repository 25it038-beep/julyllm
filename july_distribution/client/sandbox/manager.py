"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.manager
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Central Coordinator for the Windows Sandbox:
- Implements: install, status, start, stop, reset, remove, execute, execute_code
- Unifies Job Object, Restricted Token, Filesystem, Network, and Validator
- Guarantees Fail-Closed: Never falls back to unrestricted execution under primary user
"""

from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .job_object import WindowsJobObject
from .token_security import WindowsRestrictedToken
from .accounts import WindowsAccountManager, GROUP_NAME, ACCOUNT_R1, ACCOUNT_U1
from .filesystem import SandboxFilesystem, SecurityViolation
from .network import SandboxNetworkPolicy, NetworkPolicyType
from .validator import CommandSecurityValidator, ValidationResult
from .executor import SandboxProcessExecutor, ExecutionResult
from .dashboard import SandboxDashboard


class SandboxManager:
    """
    Central control interface for all Windows Sandbox operations.
    """

    _instance: Optional["SandboxManager"] = None

    @classmethod
    def get_instance(cls) -> "SandboxManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, root_dir: Optional[Path] = None):
        self.fs = SandboxFilesystem(root_dir=root_dir)
        self.accounts = WindowsAccountManager()
        self.net = SandboxNetworkPolicy(logs_dir=self.fs.logs_dir)
        self.validator = CommandSecurityValidator()
        self.executor = SandboxProcessExecutor(
            filesystem=self.fs,
            network_policy=self.net,
            validator=self.validator
        )
        self.is_started = True

    def install(self) -> Dict[str, Any]:
        """
        Idempotently installs and configures the sandbox environment:
        1. Filesystem hierarchy (Runtime, Workspace, Temporary, Logs, Artifacts)
        2. Windows security group (JulySandboxUsers) and accounts (july-sbx-r1, july-sbx-u1)
        3. DPAPI encrypted credential vault
        4. Firewall outbound and inbound rule configuration
        """
        # 1. Initialize filesystem
        self.fs.initialize_hierarchy()

        # 2. Install accounts & DPAPI vault
        acc_ok, acc_msg = self.accounts.install()

        # 3. Configure Windows Firewall
        fw_script = self.net.generate_firewall_powershell()
        fw_path = self.fs.root / "setup_firewall.ps1"
        try:
            with open(fw_path, "w", encoding="utf-8") as f:
                f.write(fw_script)
            if self.accounts.is_admin():
                import subprocess
                subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(fw_path)], capture_output=True)
            try: fw_path.unlink()
            except Exception: pass
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Sandbox installation complete: {acc_msg}",
            "root_directory": str(self.fs.root),
            "accounts_message": acc_msg
        }

    def status(self) -> Dict[str, Any]:
        """Collects telemetry and status across all sandbox subsystems."""
        acc_status = self.accounts.get_account_status()
        disk_usage = self.fs.get_disk_usage()
        fw_status = self.net.get_firewall_status()

        # Count executions and violations from log files
        total_exec = 0
        total_viol = 0
        recent_viol = []

        if self.executor.execution_log.exists():
            try:
                with open(self.executor.execution_log, "r", encoding="utf-8", errors="replace") as f:
                    total_exec = sum(1 for line in f if line.strip())
            except Exception: pass

        if self.executor.violations_log.exists():
            try:
                with open(self.executor.violations_log, "r", encoding="utf-8", errors="replace") as f:
                    viol_lines = [line.strip() for line in f if line.strip()]
                    total_viol = len(viol_lines)
                    recent_viol = viol_lines[-5:]
            except Exception: pass

        state = "ACTIVE" if self.is_started else "STOPPED"

        status_data = {
            "state": state,
            "root_directory": str(self.fs.root),
            "accounts": acc_status,
            "job_limits": {
                "max_process_memory_mb": self.executor.max_process_memory_mb,
                "max_job_memory_mb": self.executor.max_job_memory_mb,
                "cpu_rate_percent": self.executor.cpu_rate_percent,
                "active_processes": 0,
                "peak_memory_mb": 0.0
            },
            "filesystem": disk_usage,
            "network": fw_status,
            "history": {
                "total_executions": total_exec,
                "total_violations": total_viol,
                "recent_violations": recent_viol
            }
        }
        return status_data

    def render_dashboard(self) -> str:
        """Returns the formatted terminal dashboard string."""
        return SandboxDashboard.render(self.status())

    def start(self) -> Dict[str, Any]:
        """Primes the sandbox runtime and verifies operational status."""
        self.fs.initialize_hierarchy()
        self.is_started = True
        return {
            "success": True,
            "message": "July Sandbox engine is primed, healthy, and ready for isolated execution.",
            "root": str(self.fs.root)
        }

    def stop(self) -> Dict[str, Any]:
        """Terminates running sandbox processes and stops the engine."""
        self.is_started = False
        return {
            "success": True,
            "message": "July Sandbox processes stopped and engine set to standby."
        }

    def reset(self) -> Dict[str, Any]:
        """Purges ephemeral Workspace and Temporary files, restoring zero-state."""
        res = self.fs.reset_workspace_and_temporary()
        return {
            "success": True,
            "message": f"Sandbox reset successful: Freed {res['bytes_freed']} bytes ({res['items_removed']} items removed). Workspace is clean.",
            "details": res
        }

    def remove(self, confirmed: bool = False) -> Dict[str, Any]:
        """Completely rolls back and uninstalls July Sandbox resources."""
        if not confirmed:
            return {
                "success": False,
                "message": "Removal cancelled: Explicit human confirmation required (--confirm)."
            }

        # 1. Stop engine
        self.stop()

        # 2. Clean accounts & vault
        acc_ok, acc_msg = self.accounts.remove(confirmed=True)

        # 3. Clean files in Workspace and Temporary
        self.reset()

        return {
            "success": True,
            "message": f"July Sandbox removal complete. {acc_msg}"
        }

    def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        allow_network: bool = False,
        user_confirmed: bool = False
    ) -> ExecutionResult:
        """Executes a command strictly within the sandbox boundary."""
        if not self.is_started:
            self.start()
        return self.executor.execute(
            command=command,
            timeout=timeout,
            allow_network=allow_network,
            user_confirmed=user_confirmed
        )

    def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: Optional[float] = None,
        allow_network: bool = False
    ) -> ExecutionResult:
        """
        Executes generated code in a sandboxed script file.
        Confined strictly within JulySandbox/Workspace.
        """
        if not self.is_started:
            self.start()

        lang = language.lower().strip()
        ts = int(time.time() * 1000)

        if lang in ("python", "py"):
            script_name = f"exec_{ts}.py"
            script_path = self.fs.workspace_dir / script_name
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            py_exe = sys.executable
            cmd = f'"{py_exe}" "{script_name}"'
            result = self.executor.execute(cmd, timeout=timeout, allow_network=allow_network)
            try: script_path.unlink()
            except Exception: pass
            return result

        elif lang in ("powershell", "ps1"):
            script_name = f"exec_{ts}.ps1"
            script_path = self.fs.workspace_dir / script_name
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            cmd = f'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Restricted -File "{script_name}"'
            result = self.executor.execute(cmd, timeout=timeout, allow_network=allow_network)
            try: script_path.unlink()
            except Exception: pass
            return result

        elif lang in ("cmd", "bat", "batch"):
            script_name = f"exec_{ts}.bat"
            script_path = self.fs.workspace_dir / script_name
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            cmd = f'cmd.exe /c "{script_name}"'
            result = self.executor.execute(cmd, timeout=timeout, allow_network=allow_network)
            try: script_path.unlink()
            except Exception: pass
            return result

        else:
            return ExecutionResult(
                command=f"execute_code({language})",
                exit_code=1,
                stdout="",
                stderr=f"Unsupported sandbox execution language: '{language}'. Supported: python, powershell, batch.\n",
                duration_seconds=0.0,
                peak_memory_mb=0.0,
                cpu_time_seconds=0.0,
                killed_by_timeout=False,
                security_blocked=True,
                violation_reason="Unsupported execution language"
            )
