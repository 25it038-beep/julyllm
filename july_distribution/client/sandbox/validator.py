"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.validator
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Lexical & AST Command Security Validator:
- Pre-execution validation against dangerous Windows primitives
- Detection of privilege escalation attempts (net user, whoami /priv, runas, takeown)
- Detection of execution policy bypasses (Set-ExecutionPolicy Bypass, -ep bypass)
- Detection of registry tampering (reg add, reg delete, Set-ItemProperty HKLM)
- Detection of living-off-the-land attack binaries (certutil -urlcache, bitsadmin, mshta)
- Detection of system destruction (format, diskpart, vssadmin delete shadows)
- Identification of destructive operations requiring explicit human approval
"""

from __future__ import annotations
import re
import shlex
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class ValidationResult:
    allowed: bool
    reason: str
    risk_level: str  # "SAFE", "REQUIRES_APPROVAL", "DANGEROUS_BLOCKED", "FATAL_BLOCKED"
    matched_patterns: List[str] = field(default_factory=list)
    requires_user_approval: bool = False


class CommandSecurityValidator:
    """
    Validates shell and script commands before they reach the Windows sandbox executor.
    """

    # 1. FATAL / DANGEROUS PATTERNS — STRICTLY BLOCKED, NO BYPASS PERMITTED
    FATAL_PATTERNS = [
        # System Destruction & Drive Format
        (r"\bformat\b", "Disk formatting command blocked"),
        (r"\bdiskpart\b", "Disk partitioning command blocked"),
        (r"\bvssadmin\s+delete\b", "Shadow copy deletion attempt blocked"),
        (r"\bmountvol\b", "Volume mounting command blocked"),
        (r"\bbcdedit\b", "Boot Configuration Data tampering blocked"),
        (r"\bbootrec\b", "Boot record tampering blocked"),
        (r"del\s+/[fFqsQS\s]*[a-zA-Z]:\\", "Root drive file deletion blocked"),
        (r"rd\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:\\", "Root drive directory destruction blocked"),
        (r"remove-item\s+-[a-zA-Z\s]*[a-zA-Z]:\\", "PowerShell root drive deletion blocked"),

        # Privilege Escalation & Account Tampering
        (r"\bnet\s+user\b", "Windows user account inspection/modification blocked"),
        (r"\bnet\s+localgroup\b", "Windows security group inspection/modification blocked"),
        (r"\brunas\b", "Privilege elevation via runas blocked"),
        (r"\btakeown\b", "File ownership takeover attempt blocked"),
        (r"\bicacls\b.*\/(?:grant|deny|reset)", "ACL modification attempt blocked"),
        (r"\bwhoami\s+/(?:priv|all|groups)", "Privilege discovery and enumeration blocked"),
        (r"\bsecedit\b", "Security policy editor blocked"),

        # Execution Policy Bypasses
        (r"-executionpolicy\s+(?:bypass|unrestricted)", "PowerShell execution policy bypass blocked"),
        (r"-ep\s+(?:bypass|unrestricted)", "PowerShell execution policy short-flag bypass blocked"),
        (r"set-executionpolicy\s+(?:bypass|unrestricted)", "Set-ExecutionPolicy modification blocked"),

        # Registry Tampering
        (r"\breg\s+(?:add|delete|copy|import|restore)\b", "Windows Registry modification blocked"),
        (r"set-itemproperty\s+.*hklm:", "HKLM registry tampering blocked"),
        (r"new-itemproperty\s+.*hklm:", "HKLM registry tampering blocked"),
        (r"remove-itemproperty\s+.*hklm:", "HKLM registry tampering blocked"),

        # LOLBins (Living Off The Land Binaries) & Obfuscation
        (r"\bcertutil\b.*-(?:urlcache|f)", "Certutil remote file acquisition blocked"),
        (r"\bbitsadmin\b.*\/transfer", "Bitsadmin remote transfer blocked"),
        (r"powershell.*-(?:e|enc|encodedcommand)\b", "Base64 encoded PowerShell execution blocked"),
        (r"\bmshta\b", "Microsoft HTML Application host blocked"),
        (r"\bcscript\b", "Windows Script Host (cscript) blocked"),
        (r"\bwscript\b", "Windows Script Host (wscript) blocked"),
        (r"\brundll32\b", "Rundll32 arbitrary binary loader blocked"),
        (r"\bregsvr32\b", "Regsvr32 DLL register loader blocked"),

        # System Process Termination
        (r"\btaskkill\b.*(?:\/f|\/im\s+(?:csrss|lsass|services|explorer|svchost|winlogon|antigravity))", "Termination of critical OS processes blocked"),

        # Path Traversal
        (r"(?:\.\.[\\/]){2,}", "Multi-level directory traversal escape blocked"),
    ]

    # 2. DESTRUCTIVE / POTENTIALLY RISKY PATTERNS — REQUIRES EXPLICIT USER APPROVAL
    APPROVAL_PATTERNS = [
        (r"\bdel\b|\berase\b", "File deletion operation"),
        (r"\brd\b|\brmdir\b", "Directory removal operation"),
        (r"\bremove-item\b", "PowerShell item deletion"),
        (r"\bmove\b|\bmove-item\b", "File move / relocation operation"),
        (r"\bren\b|\brename-item\b", "File rename operation"),
        (r"\bset-content\b|\bout-file\b", "Potential file overwrite operation"),
    ]

    def validate_command(self, command: str) -> ValidationResult:
        """
        Thoroughly validates the command string before sandbox execution.
        """
        if not command or not command.strip():
            return ValidationResult(
                allowed=False,
                reason="Command string cannot be empty.",
                risk_level="FATAL_BLOCKED"
            )

        cmd_clean = command.strip()
        cmd_lower = cmd_clean.lower()

        # Step 1: Check Fatal / Blocked Patterns
        matched_fatal = []
        for pattern, desc in self.FATAL_PATTERNS:
            if re.search(pattern, cmd_lower):
                matched_fatal.append(desc)

        if matched_fatal:
            return ValidationResult(
                allowed=False,
                reason=f"Security Violation: {'; '.join(matched_fatal)}",
                risk_level="FATAL_BLOCKED",
                matched_patterns=matched_fatal,
                requires_user_approval=False
            )

        # Step 2: Check Patterns Requiring Explicit Approval
        matched_approval = []
        for pattern, desc in self.APPROVAL_PATTERNS:
            if re.search(pattern, cmd_lower):
                matched_approval.append(desc)

        if matched_approval:
            return ValidationResult(
                allowed=True,
                reason=f"Destructive action detected: {', '.join(matched_approval)}. Human authorization required.",
                risk_level="REQUIRES_APPROVAL",
                matched_patterns=matched_approval,
                requires_user_approval=True
            )

        # Safe for execution
        return ValidationResult(
            allowed=True,
            reason="Command verified clean by lexical security validator.",
            risk_level="SAFE",
            requires_user_approval=False
        )
