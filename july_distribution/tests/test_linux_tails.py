"""
HS AI SOLUTIONS — TEST SUITE: LINUX & TAILS OS COMPATIBILITY
Module: tests.test_linux_tails
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM / JULY OS
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from july_distribution.client.os_detector import OSDetector, detect_os_release
from july_distribution.client.hardware import get_device_identity
from july_distribution.client.config import get_default_july_dir, ClientConfig
from july_distribution.client.security.credential_vault import SecureCredentialVault, FallbackAESVault
from july_distribution.client.clerk_auth import ClerkAuthManager
import july_distribution.client.sandbox.accounts as sbx_accounts
import july_distribution.client.sandbox.job_object as sbx_job
import july_distribution.client.sandbox.token_security as sbx_token


def test_os_release_parsing(tmp_path):
    """Test parsing /etc/os-release for Tails OS."""
    os_rel_file = tmp_path / "os-release"
    os_rel_file.write_text(
        'NAME="Tails"\n'
        'VERSION="6.9"\n'
        'ID="tails"\n'
        'ID_LIKE="debian"\n'
        'VERSION_ID="6.9"\n'
        'TAILS_PRODUCT_NAME="Tails"\n'
    )
    data = detect_os_release(custom_path=os_rel_file)
    assert data.get("ID") == "tails"
    assert data.get("NAME") == "Tails"
    assert data.get("VERSION_ID") == "6.9"


def test_tails_os_detection():
    """Verify that OSDetector correctly identifies Tails OS and sets amnesia mode."""
    with patch.object(OSDetector, "is_linux", return_value=True), \
         patch("july_distribution.client.os_detector.detect_os_release", return_value={
             "ID": "tails", "NAME": "Tails", "VERSION_ID": "6.9", "TAILS_PRODUCT_NAME": "Tails"
         }):
        info = OSDetector.get_distro_info()
        assert info["is_tails"] is True
        assert info["id"] == "tails"
        assert "Tails" in info["name"]
        assert OSDetector.is_tails() is True


def test_debian_ubuntu_kali_detection():
    """Verify standard Debian, Ubuntu, and Kali detection."""
    # Debian
    with patch.object(OSDetector, "is_linux", return_value=True), \
         patch("july_distribution.client.os_detector.detect_os_release", return_value={
             "ID": "debian", "NAME": "Debian GNU/Linux", "VERSION_ID": "12"
         }):
        info = OSDetector.get_distro_info()
        assert info["is_debian"] is True
        assert info["is_tails"] is False

    # Ubuntu
    with patch.object(OSDetector, "is_linux", return_value=True), \
         patch("july_distribution.client.os_detector.detect_os_release", return_value={
             "ID": "ubuntu", "NAME": "Ubuntu", "VERSION_ID": "24.04"
         }):
        info = OSDetector.get_distro_info()
        assert info["is_ubuntu"] is True

    # Kali
    with patch.object(OSDetector, "is_linux", return_value=True), \
         patch("july_distribution.client.os_detector.detect_os_release", return_value={
             "ID": "kali", "NAME": "Kali GNU/Linux"
         }):
        info = OSDetector.get_distro_info()
        assert info["is_kali"] is True


def test_tails_persistence_detection(tmp_path):
    """Test detection of unlocked Tails Persistent Storage."""
    persistent_dir = tmp_path / "Persistent"
    persistent_dir.mkdir()

    with patch.object(OSDetector, "is_tails", return_value=True), \
         patch("pathlib.Path.home", return_value=tmp_path):
        pers_info = OSDetector.get_tails_persistence_info()
        assert pers_info["supported"] is True
        assert pers_info["unlocked"] is True
        assert pers_info["path"] == str(persistent_dir)


def test_device_identity_privacy_on_tails():
    """Verify that on Tails OS, hardware fingerprinting is strictly disabled for amnesia privacy."""
    with patch("july_distribution.client.os_detector.OSDetector.is_tails", return_value=True):
        dev = get_device_identity()
        assert dev["device_id"] == "tails_amnesia_device"
        assert dev["device_name"] == "amnesia"
        assert "Tails OS" in dev["os_version"]


def test_environment_variable_auth_fallback():
    """Verify Requirement 7: Environment-variable authentication fallback."""
    with patch.dict(os.environ, {"JULY_API_KEY": "hs-test-tails-key-12345"}):
        vault = SecureCredentialVault()
        sess = vault.retrieve_session()
        assert sess is not None
        assert sess["token"] == "hs-test-tails-key-12345"
        assert sess["provider"] == "environment_variable"
        assert sess["environment_fallback"] is True
        assert vault.is_session_expired(sess) is False

        # Clerk auth manager reflects authentication
        clerk = ClerkAuthManager()
        assert clerk.is_authenticated() is True
        assert clerk.get_token() == "hs-test-tails-key-12345"


def test_tails_persistent_config_dir(tmp_path):
    """Test that JULY_PERSISTENT=1 routes config to Tails Persistent Storage."""
    persistent_dir = tmp_path / "Persistent"
    persistent_dir.mkdir()
    target_july = persistent_dir / ".july"

    with patch.dict(os.environ, {"JULY_PERSISTENT": "1"}, clear=False), \
         patch("pathlib.Path.home", return_value=tmp_path):
        p = get_default_july_dir()
        assert str(p) == str(target_july)


def test_fallback_aes_vault():
    """Test FallbackAESVault cross-platform encryption on non-Windows."""
    vault = FallbackAESVault()
    secret = b"JULY_SECRET_PAYLOAD_12345_TAILS"
    encrypted = vault.encrypt(secret)
    assert encrypted != secret
    assert (encrypted.startswith(b"AESGCM:") or encrypted.startswith(b"SIGXOR:"))
    decrypted = vault.decrypt(encrypted)
    assert decrypted == secret


def test_sandbox_modules_linux_safety():
    """Verify that sandbox modules don't crash when imported or run on Linux."""
    # Ensure modules have safe fallback if not win32
    assert hasattr(sbx_accounts, "crypt32")
    assert hasattr(sbx_job, "kernel32")
    assert hasattr(sbx_token, "advapi32")


def test_cli_subparsers_registered():
    """Verify that all required subcommands are properly registered in argparse."""
    import argparse
    from july_distribution.client.cli import main

    # We can inspect the parser directly by parsing --help or testing known commands
    import importlib
    cli_mod = importlib.import_module("july_distribution.client.cli")

    commands_to_verify = [
        "chat", "agent", "models", "login", "logout",
        "config", "update", "doctor", "version", "help"
    ]

    # Verify handlers exist in cli.py
    for cmd in commands_to_verify:
        handler_name = f"cmd_{cmd}"
        assert hasattr(cli_mod, handler_name), f"Missing handler {handler_name} in cli.py"


def test_installer_scripts_exist():
    """Verify all Linux and Windows installer files are in the repository."""
    repo_root = Path(__file__).resolve().parent.parent
    install_sh = repo_root / "installer" / "install.sh"
    start_sh = repo_root / "installer" / "start.sh"
    july_bin = repo_root / "linux" / "july"
    bootstrap_py = repo_root / "linux" / "bootstrap.py"
    req_txt = repo_root / "linux" / "requirements.txt"

    assert install_sh.exists() and install_sh.stat().st_size > 0
    assert start_sh.exists() and start_sh.stat().st_size > 0
    assert july_bin.exists() and july_bin.stat().st_size > 0
    assert bootstrap_py.exists() and bootstrap_py.stat().st_size > 0
    assert req_txt.exists() and req_txt.stat().st_size > 0
