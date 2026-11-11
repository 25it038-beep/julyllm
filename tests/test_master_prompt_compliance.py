"""
Unit and integration tests for Master Implementation Prompt compliance:
- HS AI Solutions Account branding
- july login (already authenticated & unauthenticated flows)
- july logout (cryptographic DPAPI vault wiped)
- july auth status
- july auth refresh
- july account (complete Section 5 User Dashboard)
"""

import unittest
import io
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from july_distribution.client.clerk_auth import ClerkAuthManager, SecureCredentialVault
from july_distribution.client import cli
import argparse


class TestMasterPromptCompliance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_file = Path(self.temp_dir.name) / "credentials.vault"
        self.vault = SecureCredentialVault(vault_path=self.vault_file)
        self.clerk = ClerkAuthManager()
        self.clerk.vault = self.vault

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_login_already_authenticated_workflow(self):
        """Workflow 1: Checks whether user is already authenticated."""
        self.clerk.login_manual("test_token_123", email="harshan@hs-ai.solutions")
        # Update name for display
        sess = self.clerk.get_session()
        sess["name"] = "Harshan"
        self.clerk.vault.store_session(sess)

        captured = io.StringIO()
        with patch("sys.stdout", captured), patch("july_distribution.client.cli.ClerkAuthManager", return_value=self.clerk):
            cli.cmd_login(argparse.Namespace(force=False, token=None, sso=None, server=None))

        output = captured.getvalue()
        self.assertIn("JULY LLM", output)
        self.assertIn("Powered by HS AI Solutions", output)
        self.assertIn("Already authenticated!", output)
        self.assertIn("Welcome, Harshan.", output)
        self.assertIn("Account: harshan@hs-ai.solutions", output)
        self.assertIn("Authentication: Verified", output)
        self.assertIn("July LLM is ready.", output)

    def test_02_login_manual_token_workflow(self):
        """Workflow 2: Authenticate via token with verified output format."""
        captured = io.StringIO()
        with patch("sys.stdout", captured), patch("july_distribution.client.cli.ClerkAuthManager", return_value=self.clerk):
            cli.cmd_login(argparse.Namespace(force=True, token="clerk_sess_xyz987", email="harshan@hs-ai.solutions", server=None))

        output = captured.getvalue()
        self.assertIn("Successfully authenticated!", output)
        self.assertIn("Account: harshan@hs-ai.solutions", output)
        self.assertIn("Authentication: Verified", output)
        self.assertIn("July LLM is ready.", output)

    def test_03_logout_workflow(self):
        """Workflow 3: Log out and securely wipe local vault."""
        self.clerk.login_manual("token_to_wipe", email="user@hs-ai.solutions")
        self.assertTrue(self.clerk.is_authenticated())

        captured = io.StringIO()
        with patch("sys.stdout", captured), \
             patch("july_distribution.client.cli.ClerkAuthManager", return_value=self.clerk), \
             patch("urllib.request.urlopen"):
            cli.cmd_logout(argparse.Namespace())

        output = captured.getvalue()
        self.assertIn("Logged out successfully.", output)
        self.assertIn("Local cryptographic credential vault wiped.", output)
        self.assertFalse(self.vault_file.exists())
        self.assertFalse(self.clerk.is_authenticated())

    def test_04_auth_status_workflow(self):
        """Workflow 4: july auth status outputs full telemetry."""
        with patch("urllib.request.urlopen"):
            self.clerk.login_manual("token_status", email="dev@hs-ai.solutions")

        captured = io.StringIO()
        with patch("sys.stdout", captured), patch("july_distribution.client.cli.ClerkAuthManager", return_value=self.clerk):
            cli.cmd_auth(argparse.Namespace(action="status", device_id=None))

        output = captured.getvalue()
        self.assertIn("HS AI SOLUTIONS", output)
        self.assertIn("IDENTITY & CREDENTIAL VAULT", output)
        self.assertIn("Clerk Identity & Access Management", output)
        self.assertIn("HARDWARE DEVICE BOUNDARY", output)
        self.assertIn("RATE LIMITING & MODEL ACCESS QUOTAS", output)

    def test_05_auth_refresh_workflow(self):
        """Workflow 5: july auth refresh re-seals vault."""
        with patch("urllib.request.urlopen"):
            self.clerk.login_manual("token_refresh", email="refresh@hs-ai.solutions")

        captured = io.StringIO()
        with patch("sys.stdout", captured), \
             patch("july_distribution.client.cli.ClerkAuthManager", return_value=self.clerk), \
             patch("urllib.request.urlopen"):
            cli.cmd_auth(argparse.Namespace(action="refresh", device_id=None))

        output = captured.getvalue()
        self.assertIn("Session Refreshed Successfully!", output)
        self.assertIn("refresh@hs-ai.solutions", output)
        self.assertIn("Windows DPAPI Re-sealed", output)

    def test_06_account_dashboard_section_5_compliance(self):
        """
        Workflow 6: july account satisfies all Section 5 requirements:
        - Profile picture
        - Name
        - Email
        - Account verification status
        - Account creation date
        - Current authentication session
        - Token usage statistics
        - Rate limits
        - Available models (July, Gravity, Auto)
        - Sign-out instructions
        """
        self.clerk.login_manual("token_acc", email="harshan@hs-ai.solutions")
        sess = self.clerk.get_session()
        sess["name"] = "Harshan Seliyan"
        sess["image_url"] = "https://img.clerk.com/harshan-avatar.png"
        sess["usage"] = {
            "total_tokens": 5200,
            "requests_count": 18,
            "models_used": {
                "july": {"tokens": 3000, "requests": 12},
                "gravity": {"tokens": 2200, "requests": 6}
            }
        }
        self.clerk.vault.store_session(sess)

        captured = io.StringIO()
        with patch("sys.stdout", captured), patch("july_distribution.client.cli.ClerkAuthManager", return_value=self.clerk):
            cli.cmd_account(argparse.Namespace())

        output = captured.getvalue()

        # Check all Section 5 requirements:
        self.assertIn("Profile Picture", output)
        self.assertIn("https://img.clerk.com/harshan-avatar.png", output)
        self.assertIn("Name", output)
        self.assertIn("Harshan Seliyan", output)
        self.assertIn("Email", output)
        self.assertIn("harshan@hs-ai.solutions", output)
        self.assertIn("Verification", output)
        self.assertIn("Verified (Clerk Identity & Access Management)", output)
        self.assertIn("Account Created", output)
        self.assertIn("CURRENT AUTHENTICATION SESSION", output)
        self.assertIn("TOKEN USAGE STATISTICS", output)
        self.assertIn("5,200", output)
        self.assertIn("RATE LIMITS & QUOTAS", output)
        self.assertIn("AVAILABLE FOUNDATION MODELS", output)
        self.assertIn("July", output)
        self.assertIn("Gravity", output)
        self.assertIn("Auto", output)
        self.assertIn("SIGN-OUT INSTRUCTIONS", output)
        self.assertIn("july logout", output)


if __name__ == "__main__":
    unittest.main()
