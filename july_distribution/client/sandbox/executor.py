"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.executor
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Executes sandboxed processes under strict Windows security controls:
- Assignment to Windows Job Object immediately on spawn
- Hard process memory and CPU rate ceilings
- Execution timeout management with atomic process-tree termination
- Environment variable sanitization (stripping all host secrets and credentials)
- Working directory confinement to JulySandbox/Workspace
- Pre-execution validation via CommandSecurityValidator
- Pre-execution network policy enforcement via SandboxNetworkPolicy
- Fail-Closed: Never falls back to unrestricted execution
"""

from __future__ import annotations
import os
import sys
import time
import datetime
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .job_object import WindowsJobObject
from .filesystem import SandboxFilesystem, SecurityViolation
from .validator import CommandSecurityValidator, ValidationResult
from .network import SandboxNetworkPolicy, NetworkPolicyType


@dataclass
class ExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    peak_memory_mb: float
    cpu_time_seconds: float
    killed_by_timeout: bool
    security_blocked: bool
    violation_reason: Optional[str] = None
    telemetry: Optional[Dict[str, Any]] = None


class SandboxProcessExecutor:
    """
    Spawns and manages restricted processes within the Windows Sandbox.
    """

    def __init__(
        self,
        filesystem: SandboxFilesystem,
        network_policy: SandboxNetworkPolicy,
        validator: Optional[CommandSecurityValidator] = None,
        max_process_memory_mb: int = 512,
        max_job_memory_mb: int = 1024,
        cpu_rate_percent: float = 50.0,
        default_timeout_sec: float = 30.0
    ):
        self.fs = filesystem
        self.net = network_policy
        self.validator = validator or CommandSecurityValidator()
        self.max_process_memory_mb = max_process_memory_mb
        self.max_job_memory_mb = max_job_memory_mb
        self.cpu_rate_percent = cpu_rate_percent
        self.default_timeout_sec = default_timeout_sec

        self.execution_log = self.fs.logs_dir / "execution.log"
        self.violations_log = self.fs.logs_dir / "violations.log"

    def build_sanitized_environment(self) -> Dict[str, str]:
        """
        Builds a minimal, secure environment block with no host secrets or personal paths.
        """
        system_root = os.getenv("SystemRoot", "C:\\Windows")
        system_drive = os.getenv("SystemDrive", "C:")
        comspec = os.getenv("ComSpec", f"{system_root}\\System32\\cmd.exe")

        # Minimal safe PATH: System32 and sandbox Runtime
        safe_path_elements = [
            str(self.fs.runtime_dir),
            f"{system_root}\\System32",
            f"{system_root}",
            f"{system_root}\\System32\\WindowsPowerShell\\v1.0"
        ]

        # Check if Python is installed in a system directory or runtime
        py_dir = str(Path(sys.executable).parent)
        safe_path_elements.insert(0, py_dir)

        sanitized = {
            "ALLUSERSPROFILE": f"{system_drive}\\ProgramData",
            "APPDATA": str(self.fs.workspace_dir / ".appdata"),
            "COMMONPROGRAMFILES": f"{system_drive}\\Program Files\\Common Files",
            "COMPUTERNAME": os.getenv("COMPUTERNAME", "JULY-SANDBOX"),
            "COMSPEC": comspec,
            "HOMEDRIVE": system_drive,
            "HOMEPATH": str(self.fs.workspace_dir),
            "LOCALAPPDATA": str(self.fs.workspace_dir / ".localappdata"),
            "NUMBER_OF_PROCESSORS": os.getenv("NUMBER_OF_PROCESSORS", "4"),
            "OS": "Windows_NT",
            "PATH": ";".join(safe_path_elements),
            "PATHEXT": ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC",
            "PROCESSOR_ARCHITECTURE": os.getenv("PROCESSOR_ARCHITECTURE", "AMD64"),
            "PROGRAMDATA": f"{system_drive}\\ProgramData",
            "PROGRAMFILES": f"{system_drive}\\Program Files",
            "PSMODULEPATH": f"{system_root}\\System32\\WindowsPowerShell\\v1.0\\Modules",
            "PUBLIC": str(self.fs.workspace_dir / ".public"),
            "SYSTEMDRIVE": system_drive,
            "SYSTEMROOT": system_root,
            "TEMP": str(self.fs.temporary_dir),
            "TMP": str(self.fs.temporary_dir),
            "USERDOMAIN": "JULY-SANDBOX",
            "USERNAME": "july-sandbox-worker",
            "USERPROFILE": str(self.fs.workspace_dir),
            "WINDIR": system_root,
            "JULY_SANDBOX": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1"
        }

        # Explicitly verify no secret environment variables leak
        for k in list(sanitized.keys()):
            k_upper = k.upper()
            if any(k_upper.startswith(p) for p in ("AWS_", "AZURE_", "GITHUB_", "OPENAI_", "ANTHROPIC_", "GOOGLE_")):
                del sanitized[k]
            elif any(s in k_upper for s in ("TOKEN", "SECRET", "KEY", "PASSWORD", "CREDENTIAL")):
                del sanitized[k]

        return sanitized

    def log_execution(self, command: str, result: ExecutionResult):
        """Appends structured audit record to execution log."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_line = (
            f"[{timestamp}] EXIT={result.exit_code} DURATION={result.duration_seconds}s "
            f"PEAK_MEM={result.peak_memory_mb}MB TIMEOUT={result.killed_by_timeout} "
            f"BLOCKED={result.security_blocked} CMD='{command[:150]}'\n"
        )
        try:
            with open(self.execution_log, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass

    def log_violation(self, command: str, reason: str):
        """Appends security breach attempt to violations log."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_line = f"[{timestamp}] VIOLATION='{reason}' CMD='{command}'\n"
        try:
            with open(self.violations_log, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass

    def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        allow_network: bool = False,
        user_confirmed: bool = False
    ) -> ExecutionResult:
        """
        Executes a command inside the Windows Job Object sandbox.
        Guarantees Fail-Closed: Never falls back to unsandboxed execution.
        """
        t0 = time.time()
        eff_timeout = timeout if timeout is not None else self.default_timeout_sec

        # 1. Command Validation
        val_res = self.validator.validate_command(command)
        if not val_res.allowed:
            self.log_violation(command, val_res.reason)
            return ExecutionResult(
                command=command,
                exit_code=126,
                stdout="",
                stderr=f"SANDBOX SECURITY ERROR: {val_res.reason}\n",
                duration_seconds=0.0,
                peak_memory_mb=0.0,
                cpu_time_seconds=0.0,
                killed_by_timeout=False,
                security_blocked=True,
                violation_reason=val_res.reason
            )

        if val_res.requires_user_approval and not user_confirmed:
            reason = f"Human Approval Required: {val_res.reason}"
            self.log_violation(command, reason)
            return ExecutionResult(
                command=command,
                exit_code=125,
                stdout="",
                stderr=f"SANDBOX APPROVAL REQUIRED: {reason}\n",
                duration_seconds=0.0,
                peak_memory_mb=0.0,
                cpu_time_seconds=0.0,
                killed_by_timeout=False,
                security_blocked=True,
                violation_reason=reason
            )

        # 2. Network Policy Inspection
        if not allow_network:
            net_ok, net_reason = self.net.inspect_command(command)
            if not net_ok:
                self.log_violation(command, net_reason or "Network policy violation")
                return ExecutionResult(
                    command=command,
                    exit_code=126,
                    stdout="",
                    stderr=f"SANDBOX NETWORK BLOCKED: {net_reason}\n",
                    duration_seconds=0.0,
                    peak_memory_mb=0.0,
                    cpu_time_seconds=0.0,
                    killed_by_timeout=False,
                    security_blocked=True,
                    violation_reason=net_reason
                )

        # 3. Initialize Windows Job Object
        try:
            job = WindowsJobObject(
                max_process_memory_mb=self.max_process_memory_mb,
                max_job_memory_mb=self.max_job_memory_mb,
                cpu_rate_percent=self.cpu_rate_percent,
                kill_on_close=True
            )
        except Exception as e:
            # FAIL-CLOSED: Refuse to execute unsandboxed
            err_msg = f"SANDBOX FAILURE: Failed to initialize Windows Job Object ({e}). Execution aborted to preserve security boundary."
            self.log_violation(command, err_msg)
            return ExecutionResult(
                command=command,
                exit_code=127,
                stdout="",
                stderr=err_msg + "\n",
                duration_seconds=0.0,
                peak_memory_mb=0.0,
                cpu_time_seconds=0.0,
                killed_by_timeout=False,
                security_blocked=True,
                violation_reason=err_msg
            )

        # 4. Prepare Environment & Working Directory
        env = self.build_sanitized_environment()
        cwd = str(self.fs.workspace_dir)

        # 5. Spawn Process
        proc = None
        killed_by_timeout = False
        stdout_text = ""
        stderr_text = ""
        telemetry = {}

        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )

            # 6. Assign immediately to Job Object
            job.assign_process(proc._handle, pid=proc.pid)

            # 7. Wait with timeout
            try:
                stdout_text, stderr_text = proc.communicate(timeout=eff_timeout)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                killed_by_timeout = True
                # Atomically terminate entire process tree in Job Object
                job.terminate(exit_code=124)
                proc.kill()
                try:
                    stdout_text, stderr_text = proc.communicate(timeout=2)
                except Exception:
                    pass
                exit_code = 124
                stderr_text += f"\n[SANDBOX ENGINE] Process tree terminated: Execution exceeded timeout of {eff_timeout}s."

            # Query kernel telemetry before job closes
            telemetry = job.get_telemetry()

        except Exception as e:
            exit_code = 1
            stderr_text += f"\n[SANDBOX ENGINE ERROR] {e}"
        finally:
            job.close()

        elapsed = round(time.time() - t0, 3)
        res = ExecutionResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_text or "",
            stderr=stderr_text or "",
            duration_seconds=elapsed,
            peak_memory_mb=telemetry.get("peak_memory_mb", 0.0),
            cpu_time_seconds=telemetry.get("user_time_sec", 0.0) + telemetry.get("kernel_time_sec", 0.0),
            killed_by_timeout=killed_by_timeout,
            security_blocked=False,
            telemetry=telemetry
        )

        self.log_execution(command, res)
        return res
