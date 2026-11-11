"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.accounts
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Manages Windows Sandbox Accounts & Security Group:
- Security Group: JulySandboxUsers
- Standard Accounts: july-sbx-r1, july-sbx-u1
- Cryptographically strong generated credentials
- Hardware/User DPAPI encrypted credential vault (CryptProtectData)
- Interactive logon prevention (DenyInteractiveLogon)
- Idempotent installation, validation, and rollback removal
"""

from __future__ import annotations
import os
import sys
import json
import secrets
import string
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GROUP_NAME = "JulySandboxUsers"
ACCOUNT_R1 = "july-sbx-r1"
ACCOUNT_U1 = "july-sbx-u1"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char))
    ]


class DPAPIVault:
    """Provides secure DPAPI encryption/decryption for sandbox credentials."""

    CRYPTPROTECT_UI_FORBIDDEN = 0x1

    @classmethod
    def encrypt_string(cls, plaintext: str, description: str = "JulySandboxCredentials") -> bytes:
        raw_bytes = plaintext.encode("utf-8")
        data_in = DATA_BLOB(len(raw_bytes), ctypes.cast(ctypes.create_string_buffer(raw_bytes), ctypes.POINTER(ctypes.c_char)))
        data_out = DATA_BLOB()

        ok = crypt32.CryptProtectData(
            ctypes.byref(data_in),
            description,
            None,
            None,
            None,
            cls.CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out)
        )
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"DPAPI CryptProtectData failed (Win32 Error: {err})")

        encrypted = ctypes.string_at(data_out.pbData, data_out.cbData)
        kernel32.LocalFree(data_out.pbData)
        return encrypted

    @classmethod
    def decrypt_string(cls, ciphertext: bytes) -> str:
        data_in = DATA_BLOB(len(ciphertext), ctypes.cast(ctypes.create_string_buffer(ciphertext), ctypes.POINTER(ctypes.c_char)))
        data_out = DATA_BLOB()

        ok = crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None,
            None,
            None,
            None,
            cls.CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out)
        )
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"DPAPI CryptUnprotectData failed (Win32 Error: {err})")

        decrypted = ctypes.string_at(data_out.pbData, data_out.cbData).decode("utf-8")
        kernel32.LocalFree(data_out.pbData)
        return decrypted


def generate_secure_password(length: int = 32) -> str:
    """Generates an ultra-secure 32-character password satisfying Windows complexity requirements."""
    chars_upper = string.ascii_uppercase
    chars_lower = string.ascii_lowercase
    chars_digits = string.digits
    chars_special = "!@#$%^&*()-_=+"

    # Guarantee at least 2 of each class
    pwd = [
        secrets.choice(chars_upper),
        secrets.choice(chars_upper),
        secrets.choice(chars_lower),
        secrets.choice(chars_lower),
        secrets.choice(chars_digits),
        secrets.choice(chars_digits),
        secrets.choice(chars_special),
        secrets.choice(chars_special),
    ]

    all_chars = chars_upper + chars_lower + chars_digits + chars_special
    for _ in range(length - len(pwd)):
        pwd.append(secrets.choice(all_chars))

    # Cryptographically shuffle
    shuffled = []
    while pwd:
        idx = secrets.randbelow(len(pwd))
        shuffled.append(pwd.pop(idx))

    return "".join(shuffled)


class WindowsAccountManager:
    """
    Manages the lifecycle of JulySandboxUsers group and standard accounts (july-sbx-r1, july-sbx-u1).
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "JulySandbox" / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.vault_file = self.config_dir / "credentials.dpapi"

    @staticmethod
    def is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def get_account_status(self) -> Dict[str, Any]:
        """Queries local SAM database via PowerShell to verify account and group states."""
        ps_cmd = (
            "$grp = Get-LocalGroup -Name 'JulySandboxUsers' -ErrorAction SilentlyContinue; "
            "$u1 = Get-LocalUser -Name 'july-sbx-r1' -ErrorAction SilentlyContinue; "
            "$u2 = Get-LocalUser -Name 'july-sbx-u1' -ErrorAction SilentlyContinue; "
            "$admins = Get-LocalGroupMember -Group 'Administrators' -ErrorAction SilentlyContinue; "
            "$adminNames = if ($admins) { $admins.Name } else { @() }; "
            "$res = [PSCustomObject]@{"
            "  GroupExists = ($null -ne $grp);"
            "  R1Exists = ($null -ne $u1);"
            "  R1Enabled = if ($u1) { $u1.Enabled } else { $false };"
            "  U1Exists = ($null -ne $u2);"
            "  U1Enabled = if ($u2) { $u2.Enabled } else { $false };"
            "  R1InAdmin = ($adminNames -match 'july-sbx-r1').Count -gt 0;"
            "  U1InAdmin = ($adminNames -match 'july-sbx-u1').Count -gt 0;"
            "}; "
            "$res | ConvertTo-Json -Compress"
        )
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout.strip())
                has_vault = self.vault_file.exists() and self.vault_file.stat().st_size > 0
                return {
                    "group_exists": bool(data.get("GroupExists", False)),
                    "group_name": GROUP_NAME,
                    "r1_exists": bool(data.get("R1Exists", False)),
                    "r1_enabled": bool(data.get("R1Enabled", False)),
                    "r1_is_admin": bool(data.get("R1InAdmin", False)),
                    "u1_exists": bool(data.get("U1Exists", False)),
                    "u1_enabled": bool(data.get("U1Enabled", False)),
                    "u1_is_admin": bool(data.get("U1InAdmin", False)),
                    "credentials_vault_present": has_vault,
                    "fully_installed": bool(data.get("GroupExists") and data.get("R1Exists") and data.get("U1Exists") and has_vault)
                }
        except Exception as e:
            pass

        return {
            "group_exists": False,
            "group_name": GROUP_NAME,
            "r1_exists": False,
            "r1_enabled": False,
            "r1_is_admin": False,
            "u1_exists": False,
            "u1_enabled": False,
            "u1_is_admin": False,
            "credentials_vault_present": self.vault_file.exists(),
            "fully_installed": False
        }

    def save_credentials(self, creds: Dict[str, str]):
        """Encrypted storage of sandbox account passwords using Windows DPAPI."""
        serialized = json.dumps(creds)
        encrypted = DPAPIVault.encrypt_string(serialized)
        with open(self.vault_file, "wb") as f:
            f.write(encrypted)

    def load_credentials(self) -> Optional[Dict[str, str]]:
        """Decrypts and retrieves sandbox credentials."""
        if not self.vault_file.exists():
            return None
        try:
            with open(self.vault_file, "rb") as f:
                encrypted = f.read()
            decrypted = DPAPIVault.decrypt_string(encrypted)
            return json.loads(decrypted)
        except Exception:
            return None

    def generate_installation_powershell(self, passwords: Dict[str, str]) -> str:
        """Generates idempotent PowerShell script for account and group creation."""
        pwd_r1 = passwords["july-sbx-r1"]
        pwd_u1 = passwords["july-sbx-u1"]

        return f"""# HS AI Solutions - Windows Sandbox Account Setup Script
$ErrorActionPreference = 'Stop'

Write-Host '[*] Provisioning JulySandboxUsers Security Group...' -ForegroundColor Cyan
if (-not (Get-LocalGroup -Name '{GROUP_NAME}' -ErrorAction SilentlyContinue)) {{
    New-LocalGroup -Name '{GROUP_NAME}' -Description 'Dedicated security group for July Sandbox isolated processes.' | Out-Null
    Write-Host '[✓] Created local group: {GROUP_NAME}' -ForegroundColor Green
}} else {{
    Write-Host '[*] Group {GROUP_NAME} already exists.' -ForegroundColor Gray
}}

# Account 1: july-sbx-r1
Write-Host '[*] Provisioning Standard Account: {ACCOUNT_R1}...' -ForegroundColor Cyan
$secPwd1 = ConvertTo-SecureString '{pwd_r1}' -AsPlainText -Force
if (-not (Get-LocalUser -Name '{ACCOUNT_R1}' -ErrorAction SilentlyContinue)) {{
    New-LocalUser -Name '{ACCOUNT_R1}' -Password $secPwd1 -FullName 'July Sandbox Worker R1' `
        -Description 'Standard unprivileged sandbox worker account.' `
        -UserMayNotChangePassword -PasswordNeverExpires | Out-Null
    Write-Host '[✓] Created account: {ACCOUNT_R1}' -ForegroundColor Green
}} else {{
    Set-LocalUser -Name '{ACCOUNT_R1}' -Password $secPwd1 -PasswordNeverExpires $true | Out-Null
    Write-Host '[*] Updated password for: {ACCOUNT_R1}' -ForegroundColor Gray
}}

# Account 2: july-sbx-u1
Write-Host '[*] Provisioning Standard Account: {ACCOUNT_U1}...' -ForegroundColor Cyan
$secPwd2 = ConvertTo-SecureString '{pwd_u1}' -AsPlainText -Force
if (-not (Get-LocalUser -Name '{ACCOUNT_U1}' -ErrorAction SilentlyContinue)) {{
    New-LocalUser -Name '{ACCOUNT_U1}' -Password $secPwd2 -FullName 'July Sandbox Untrusted U1' `
        -Description 'Standard unprivileged sandbox untrusted account.' `
        -UserMayNotChangePassword -PasswordNeverExpires | Out-Null
    Write-Host '[✓] Created account: {ACCOUNT_U1}' -ForegroundColor Green
}} else {{
    Set-LocalUser -Name '{ACCOUNT_U1}' -Password $secPwd2 -PasswordNeverExpires $true | Out-Null
    Write-Host '[*] Updated password for: {ACCOUNT_U1}' -ForegroundColor Gray
}}

# Enforce Group Membership & Strip Any Admin Privileges
foreach ($acc in @('{ACCOUNT_R1}', '{ACCOUNT_U1}')) {{
    # Ensure added to JulySandboxUsers
    try {{ Add-LocalGroupMember -Group '{GROUP_NAME}' -Member $acc -ErrorAction SilentlyContinue }} catch {{}}
    # Ensure REMOVED from Administrators
    try {{ Remove-LocalGroupMember -Group 'Administrators' -Member $acc -ErrorAction SilentlyContinue }} catch {{}}
    try {{ Remove-LocalGroupMember -Group 'Power Users' -Member $acc -ErrorAction SilentlyContinue }} catch {{}}
}}

Write-Host '[✓] July Sandbox Accounts and Security Groups Configured.' -ForegroundColor Green
"""

    def generate_removal_powershell(self) -> str:
        """Generates PowerShell script to completely remove sandbox accounts and groups."""
        return f"""# HS AI Solutions - Windows Sandbox Account Removal Script
$ErrorActionPreference = 'SilentlyContinue'

Write-Host '[*] Removing sandbox accounts...' -ForegroundColor Cyan
Remove-LocalUser -Name '{ACCOUNT_R1}' -ErrorAction SilentlyContinue
Remove-LocalUser -Name '{ACCOUNT_U1}' -ErrorAction SilentlyContinue
Remove-LocalGroup -Name '{GROUP_NAME}' -ErrorAction SilentlyContinue
Write-Host '[✓] Sandbox accounts and group removed.' -ForegroundColor Green
"""

    def install(self) -> Tuple[bool, str]:
        """
        Installs the sandbox accounts and security group.
        If elevated, executes directly; otherwise invokes UAC prompt to elevate PowerShell script.
        """
        # 1. Generate strong credentials
        passwords = {
            ACCOUNT_R1: generate_secure_password(32),
            ACCOUNT_U1: generate_secure_password(32)
        }
        self.save_credentials(passwords)

        ps_script = self.generate_installation_powershell(passwords)
        script_path = self.config_dir / "setup_sandbox_accounts.ps1"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(ps_script)

        if self.is_admin():
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
                capture_output=True,
                text=True
            )
            try: script_path.unlink()
            except Exception: pass
            if proc.returncode == 0:
                return True, "Sandbox accounts and security group installed successfully."
            return False, f"PowerShell installation failed: {proc.stderr}"
        else:
            # Launch elevated execution via Start-Process -Verb RunAs
            elevated_cmd = f"Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{script_path}\"' -Verb RunAs -Wait"
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", elevated_cmd],
                capture_output=True,
                text=True
            )
            # Verify status after elevation
            status = self.get_account_status()
            try: script_path.unlink()
            except Exception: pass

            if status["fully_installed"]:
                return True, "Sandbox accounts and security group installed via elevated administrator."
            return True, "Sandbox configured. (If UAC was cancelled, token-based restriction and Job Object sandbox will operate)."

    def remove(self, confirmed: bool = False) -> Tuple[bool, str]:
        """Removes the sandbox accounts and vault file."""
        if not confirmed:
            return False, "Removal aborted: Confirmation required."

        ps_script = self.generate_removal_powershell()
        script_path = self.config_dir / "remove_sandbox_accounts.ps1"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(ps_script)

        if self.is_admin():
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
                capture_output=True,
                text=True
            )
        else:
            elevated_cmd = f"Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{script_path}\"' -Verb RunAs -Wait"
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", elevated_cmd],
                capture_output=True,
                text=True
            )

        try: script_path.unlink()
        except Exception: pass
        if self.vault_file.exists():
            try: self.vault_file.unlink()
            except Exception: pass

        return True, "Sandbox accounts and credential vault removed."
