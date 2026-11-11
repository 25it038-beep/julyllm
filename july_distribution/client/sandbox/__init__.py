"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Package: july_distribution.client.sandbox
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Exposes the full Windows Sandbox Execution Suite:
- SandboxManager: Unified orchestration manager
- WindowsJobObject: Kernel-level process tree & resource control
- WindowsRestrictedToken: Win32 restricted token enforcement
- WindowsAccountManager: JulySandboxUsers, july-sbx-r1, july-sbx-u1
- SandboxFilesystem: Hierarchy management & path confinement
- SandboxNetworkPolicy: Firewall & connection restriction policies
- CommandSecurityValidator: Pre-execution dangerous command AST validator
- SandboxProcessExecutor: Secure process spawning and telemetry
- SandboxDashboard: Real-time visual terminal dashboard
"""

from .manager import SandboxManager
from .job_object import WindowsJobObject
from .token_security import WindowsRestrictedToken
from .accounts import WindowsAccountManager, GROUP_NAME, ACCOUNT_R1, ACCOUNT_U1, generate_secure_password, DPAPIVault
from .filesystem import SandboxFilesystem, SecurityViolation
from .network import SandboxNetworkPolicy, NetworkPolicyType
from .validator import CommandSecurityValidator, ValidationResult
from .executor import SandboxProcessExecutor, ExecutionResult
from .dashboard import SandboxDashboard

__all__ = [
    "SandboxManager",
    "WindowsJobObject",
    "WindowsRestrictedToken",
    "WindowsAccountManager",
    "SandboxFilesystem",
    "SecurityViolation",
    "SandboxNetworkPolicy",
    "NetworkPolicyType",
    "CommandSecurityValidator",
    "ValidationResult",
    "SandboxProcessExecutor",
    "ExecutionResult",
    "SandboxDashboard",
    "GROUP_NAME",
    "ACCOUNT_R1",
    "ACCOUNT_U1",
    "generate_secure_password",
    "DPAPIVault",
]
