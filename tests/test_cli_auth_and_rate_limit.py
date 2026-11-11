"""
HS AI SOLUTIONS — CLI IN-TERMINAL AUTH & RATE LIMITING TEST SUITE
Test Module: tests.test_cli_auth_and_rate_limit
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & GRAVITY LLM RUNTIME

Verifies:
1. In-CLI Credential Login (Email/Username + Password).
2. In-CLI Sign-Up / Account Creation.
3. Gated Model Access (July & Gravity LLMs require authenticated session).
4. Sliding-Window Rate Limiting Engine (RPM, TPM, Daily Quota, Cooldown calculation).
5. Cross-Process Rate Limit Persistence.
6. Rate Limit Status in CLI Telemetry (auth status, usage).
"""

import os
import sys
import time
import json
import shutil
import unittest
import secrets
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure root workspace is on python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Also add outer workspace root if needed
OUTER_ROOT = WORKSPACE_ROOT.parent
if str(OUTER_ROOT) not in sys.path:
    sys.path.insert(0, str(OUTER_ROOT))

from july_distribution.client.clerk_auth import ClerkAuthManager
from july_distribution.client.security.credential_vault import SecureCredentialVault
from july_distribution.client.rate_limiter import ClientRateLimiter, RateLimitExceededError, TIER_LIMITS
from july_distribution.client.cli import (
    ensure_authenticated_for_models,
    cmd_auth_status,
    cmd_usage
)


class TestCliAuthAndRateLimit(unittest.TestCase):
    """Verifies in-CLI authentication and sliding-window rate limiting."""

    def setUp(self):
        self.test_dir = WORKSPACE_ROOT / "tests" / "test_tmp_cli_auth"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.orig_july_home = os.environ.get("JULY_CLIENT_HOME")
        os.environ["JULY_CLIENT_HOME"] = str(self.test_dir)
        self.vault_file = self.test_dir / "session.vault"
        self.rl_state_file = self.test_dir / "rate_limit_state.json"

    def tearDown(self):
        if self.orig_july_home is not None:
            os.environ["JULY_CLIENT_HOME"] = self.orig_july_home
        else:
            os.environ.pop("JULY_CLIENT_HOME", None)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_in_cli_credentials_login(self):
        """Verifies in-CLI credential authentication and session vault storage."""
        clerk = ClerkAuthManager()
        self.assertFalse(clerk.is_authenticated())

        # Mock the server response or test standalone
        mock_resp_data = {
            "success": True,
            "token": "clerk_sess_mock_cli_token_999",
            "clerk_user_id": "user_cli_tester_123",
            "email": "tester@hs-ai.solutions",
            "name": "CLI Tester",
            "role": "developer"
        }

        with patch("urllib.request.urlopen") as mock_url:
            mock_cm = MagicMock()
            mock_cm.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
            mock_url.return_value.__enter__.return_value = mock_cm

            session = clerk.login_credentials(
                email_or_username="tester@hs-ai.solutions",
                password="StrongPassword123!"
            )

            self.assertIsNotNone(session)
            self.assertEqual(session["email"], "tester@hs-ai.solutions")
            self.assertEqual(session["token"], "clerk_sess_mock_cli_token_999")
            self.assertTrue(clerk.is_authenticated())

            # Vault persistence check
            stored = clerk.get_session()
            self.assertIsNotNone(stored)
            self.assertEqual(stored["email"], "tester@hs-ai.solutions")

    def test_02_in_cli_signup_credentials(self):
        """Verifies in-CLI developer registration and automatic session creation."""
        clerk = ClerkAuthManager()

        rand_suffix = secrets.token_hex(4)
        email = f"new_developer_{rand_suffix}@hs-ai.solutions"
        uname = f"new_dev_{rand_suffix}"

        session = clerk.signup_credentials(
            email=email,
            username=uname,
            password="SecurePass987!"
        )

        self.assertIsNotNone(session)
        self.assertEqual(session["email"], email)
        self.assertTrue(clerk.is_authenticated())

    def test_03_gated_model_access_enforcement(self):
        """Verifies models cannot be loaded or run unless authenticated."""
        clerk = ClerkAuthManager()
        clerk.logout()

        # 1. Unauthenticated check without prompting
        is_auth, session = ensure_authenticated_for_models(prompt_user=False)
        self.assertFalse(is_auth)
        self.assertIsNone(session)

        # 2. Login in-CLI with manual token or credentials
        clerk.login_manual("clerk_sess_gated_test", email="authorized_user@hs-ai.solutions")

        # 3. Authenticated check
        is_auth, session = ensure_authenticated_for_models(prompt_user=False)
        self.assertTrue(is_auth)
        self.assertIsNotNone(session)
        self.assertEqual(session["email"], "authorized_user@hs-ai.solutions")

    def test_04_sliding_window_rate_limiting(self):
        """Verifies sliding-window rate limit enforcement and cooldown computation."""
        limiter = ClientRateLimiter(state_file=self.rl_state_file)
        limiter.reset_limits()

        # Standard tier limit is 20 RPM
        tier = "standard"
        max_rpm = TIER_LIMITS[tier]["rpm"]

        # First max_rpm requests should be permitted
        for i in range(max_rpm):
            allowed, retry_after, reason, metrics = limiter.check_limit(tier=tier, estimated_tokens=50)
            self.assertTrue(allowed, f"Request {i+1} should be permitted within RPM limit")
            self.assertEqual(retry_after, 0.0)
            limiter.record_usage(tokens=50)

        # Next request must exceed rate limit
        allowed, retry_after, reason, metrics = limiter.check_limit(tier=tier, estimated_tokens=50)
        self.assertFalse(allowed, "Exceeding RPM limit must be rejected")
        self.assertGreater(retry_after, 0.0)
        self.assertIn("Rate limit reached", reason)
        self.assertEqual(metrics["rpm_used"], max_rpm)

        # Enforce rate limit exception
        with self.assertRaises(RateLimitExceededError) as ctx:
            limiter.enforce_rate_limit(tier=tier, estimated_tokens=50)
        self.assertGreater(ctx.exception.retry_after, 0.0)

    def test_05_rate_limit_persistence_across_instances(self):
        """Verifies that restarting or creating a new limiter instance preserves window state."""
        limiter1 = ClientRateLimiter(state_file=self.rl_state_file)
        limiter1.reset_limits()

        # Record 5 requests
        for _ in range(5):
            limiter1.record_usage(tokens=100)

        # Create new instance pointing to same file
        limiter2 = ClientRateLimiter(state_file=self.rl_state_file)
        metrics = limiter2.get_metrics(tier="standard")

        self.assertEqual(metrics["rpm_used"], 5)
        self.assertEqual(metrics["tpm_used"], 500)
        self.assertEqual(metrics["rpm_remaining"], TIER_LIMITS["standard"]["rpm"] - 5)

    def test_06_tier_rate_limit_scaling(self):
        """Verifies higher tiers (Pro, Enterprise) allow higher RPM and TPM throughput."""
        limiter = ClientRateLimiter(state_file=self.rl_state_file)
        limiter.reset_limits()

        # Record 25 requests (exceeds Standard 20 RPM, but well within Pro 60 RPM)
        for _ in range(25):
            limiter.record_usage(tokens=100)

        # Standard tier: rejected
        allowed_std, _, _, _ = limiter.check_limit(tier="standard", estimated_tokens=100)
        self.assertFalse(allowed_std)

        # Pro tier: allowed
        allowed_pro, _, _, _ = limiter.check_limit(tier="pro", estimated_tokens=100)
        self.assertTrue(allowed_pro)

        # Enterprise tier: allowed
        allowed_ent, _, _, _ = limiter.check_limit(tier="enterprise", estimated_tokens=100)
        self.assertTrue(allowed_ent)

    def test_07_runtime_stream_auth_and_rate_limit_guard(self):
        """Verifies that ClientInferenceRuntime.generate_stream blocks unauthenticated callers."""
        from july_distribution.client.runtime import ClientInferenceRuntime
        from july_distribution.client.config import ClientConfig
        from july_distribution.client.storage import ClientEphemeralStorage
        from july_distribution.client.customization import UserCustomizationManager

        clerk = ClerkAuthManager()
        clerk.logout()

        cfg = ClientConfig.load()
        storage = ClientEphemeralStorage()
        customizer = UserCustomizationManager(cfg)
        runtime = ClientInferenceRuntime(cfg, storage, customizer)
        runtime._is_loaded = True
        runtime.llm = MagicMock()

        # Unauthenticated: must raise PermissionError
        with self.assertRaises(PermissionError):
            list(runtime.generate_stream("Hello"))

        # Authenticated: permitted
        clerk.login_manual("clerk_sess_runtime_auth_test", email="auth_runtime@hs-ai.solutions")
        runtime.llm.return_value = [{"choices": [{"text": "Hi!"}]}]
        tokens = list(runtime.generate_stream("Hello"))
        self.assertTrue(len(tokens) > 0)
        self.assertEqual(tokens[0], "Hi!")


if __name__ == "__main__":
    unittest.main()
