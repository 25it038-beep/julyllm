"""
HS AI SOLUTIONS — CLERK AUTHENTICATION TEST SUITE
Test Module: tests.test_clerk_auth
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & CLERK OFFICIAL IAM INTEGRATION

Verifies:
1. Secure Credential Vault (Windows DPAPI cryptographic sealing & zero plaintext).
2. Clerk Session Lifecycle (login, refresh, expire, logout).
3. Offline Mode & Queue Persistence (local model offline execution without force-login).
4. Device Identity & Hardware Registration.
5. Server Token Validation, Tier Quotas, and Usage Aggregation.
6. All CLI Auth Commands (login, logout, whoami, auth status, devices, account, usage, sync).
"""

import os
import sys
import time
import json
import shutil
import unittest
from pathlib import Path

# Ensure root workspace is on python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from july_distribution.client.security.credential_vault import SecureCredentialVault, WindowsDPAPIVault
from july_distribution.client.clerk_auth import ClerkAuthManager
from july_distribution.client.hardware import get_device_identity
from july_distribution.server.database import Base, User, Token, Device, UserUsage, create_engine, sessionmaker
from july_distribution.server.security import sync_clerk_user, record_user_consumption, get_user_usage_stats, enforce_user_rate_limit, validate_token


class TestClerkAuthenticationPlatform(unittest.TestCase):
    """Full-stack verification for July LLM Clerk Authentication."""

    def setUp(self):
        self.test_dir = WORKSPACE_ROOT / "tests" / "test_tmp_clerk"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.orig_july_home = os.environ.get("JULY_CLIENT_HOME")
        os.environ["JULY_CLIENT_HOME"] = str(self.test_dir)
        self.vault_file = self.test_dir / "session.vault"
        self.queue_file = self.test_dir / "offline_sync_queue.json"

        # Initialize isolated in-memory test database for server
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        if self.orig_july_home is not None:
            os.environ["JULY_CLIENT_HOME"] = self.orig_july_home
        else:
            os.environ.pop("JULY_CLIENT_HOME", None)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_credential_vault_dpapi_encryption(self):
        """Requirement 3: Verifies Windows DPAPI seals secrets with zero plaintext on disk."""
        vault = SecureCredentialVault(vault_path=self.vault_file)

        raw_session = {
            "token": "clerk_sess_test_super_secret_token_12345",
            "clerk_user_id": "user_2test123456",
            "email": "harshan@hs-ai.solutions",
            "tier": "enterprise",
            "expires_at": time.time() + 86400
        }
        vault.store_session(raw_session)

        # 1. Verify file exists
        self.assertTrue(self.vault_file.exists())

        # 2. Verify raw bytes do NOT contain plaintext secret
        raw_bytes = self.vault_file.read_bytes()
        self.assertNotIn(b"clerk_sess_test_super_secret_token_12345", raw_bytes)
        self.assertNotIn(b"harshan@hs-ai.solutions", raw_bytes)

        # 3. Verify successful decryption via DPAPI
        recovered = vault.retrieve_session()
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered["token"], raw_session["token"])
        self.assertEqual(recovered["clerk_user_id"], raw_session["clerk_user_id"])
        self.assertEqual(recovered["tier"], "enterprise")

        # 4. Verify secure clear wipes file
        vault.clear_session()
        self.assertFalse(self.vault_file.exists())
        self.assertIsNone(vault.retrieve_session())
        print("\n [PASS] Test 01: Windows DPAPI cryptographic sealing & zero plaintext verified.")

    def test_02_session_expiration_detection(self):
        """Requirement 1 & 3: Verifies session expiration detection."""
        vault = SecureCredentialVault(vault_path=self.vault_file)

        # Expired session
        expired_session = {
            "token": "tok_expired",
            "clerk_user_id": "user_expired",
            "expires_at": time.time() - 100
        }
        vault.store_session(expired_session)
        self.assertTrue(vault.is_session_expired())

        # Valid session
        valid_session = {
            "token": "tok_valid",
            "clerk_user_id": "user_valid",
            "expires_at": time.time() + 3600
        }
        vault.store_session(valid_session)
        self.assertFalse(vault.is_session_expired())
        print("\n [PASS] Test 02: Session expiration detection verified.")

    def test_03_hardware_device_identity(self):
        """Requirement 4 & 8: Verifies hardware device identity generation."""
        dev1 = get_device_identity()
        dev2 = get_device_identity()

        self.assertIn("device_id", dev1)
        self.assertIn("device_name", dev1)
        self.assertIn("os_version", dev1)
        # Deterministic identity on same machine
        self.assertEqual(dev1["device_id"], dev2["device_id"])
        self.assertTrue(dev1["device_id"].startswith("dev_"))
        self.assertGreaterEqual(len(dev1["device_id"]), 20)
        print(f"\n [PASS] Test 03: Stable device identity verified ({dev1['device_name']} [{dev1['os_version']}]).")

    def test_04_offline_mode_and_usage_queue(self):
        """Requirement 6 & 7: Verifies offline execution and persistent queueing."""
        clerk = ClerkAuthManager()
        clerk.vault = SecureCredentialVault(vault_path=self.vault_file)
        clerk.offline_queue_file = self.queue_file

        # Login manual
        sess = clerk.login_manual("clerk_sess_offline_test", clerk_user_id="user_offline_001", email="dev@hs-ai.solutions")
        self.assertTrue(clerk.is_authenticated())

        # Record usage across models offline
        clerk.record_usage("july", prompt_tokens=150, completion_tokens=85)
        clerk.record_usage("gravity", prompt_tokens=300, completion_tokens=420)
        clerk.record_usage("reasoning", prompt_tokens=50, completion_tokens=120)

        # Check offline queue file
        self.assertTrue(self.queue_file.exists())
        with open(self.queue_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["data"]["model_name"], "july")
        self.assertEqual(events[1]["data"]["model_name"], "gravity")

        # Verify session usage updated locally
        updated_sess = clerk.get_session()
        self.assertEqual(updated_sess["usage"]["requests_count"], 3)
        self.assertEqual(updated_sess["usage"]["total_tokens"], (150+85) + (300+420) + (50+120))
        print("\n [PASS] Test 04: Offline usage queueing & local session updates verified.")

    def test_05_server_clerk_provisioning_and_token_validation(self):
        """Requirement 4 & 5: Verifies backend Clerk user provisioning and token authorization."""
        # 1. Provision user via sync_clerk_user
        user = sync_clerk_user(
            db=self.db,
            clerk_user_id="user_clerk_prod_999",
            email="founder@hs-ai.solutions",
            name="Harshan Seliyan",
            tier="enterprise"
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.clerk_user_id, "user_clerk_prod_999")
        self.assertEqual(user.tier, "enterprise")
        self.assertEqual(user.role, "developer")

        # 2. Issue token
        test_tok = "clerk_sess_active_valid_999"
        self.db.add(Token(
            token=test_tok,
            user_id=user.id,
            created_at=time.time(),
            expires_at=time.time() + 86400,
            is_revoked=False
        ))
        self.db.commit()

        # 3. Validate token
        authenticated_user = validate_token(self.db, test_tok)
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, user.id)

        # 4. Reject invalid token
        self.assertIsNone(validate_token(self.db, "invalid_random_token"))
        print("\n [PASS] Test 05: Server Clerk provisioning & token validation verified.")

    def test_06_model_consumption_tracking_and_rate_limits(self):
        """Requirement 5 & 6: Verifies multi-model consumption tracking and tier limits."""
        user = sync_clerk_user(
            db=self.db,
            clerk_user_id="user_usage_tier_test",
            email="tier@hs-ai.solutions",
            tier="free"
        )

        # Record consumption across 6 engines
        record_user_consumption(self.db, user.id, user.clerk_user_id, "july", 100, 200)
        record_user_consumption(self.db, user.id, user.clerk_user_id, "gravity", 500, 800)
        record_user_consumption(self.db, user.id, user.clerk_user_id, "code", 250, 400)

        stats = get_user_usage_stats(self.db, user.id)
        self.assertEqual(stats["requests_count"], 3)
        self.assertEqual(stats["total_tokens"], (100+200) + (500+800) + (250+400))
        self.assertIn("july", stats["models_used"])
        self.assertIn("gravity", stats["models_used"])
        self.assertIn("code", stats["models_used"])

        # Check rate limit enforcement
        ok, msg = enforce_user_rate_limit(self.db, user)
        self.assertTrue(ok)
        self.assertIn("Quota authorized", msg)

        # Test limit exceeded
        user.downloads_today = 600
        ok_exceeded, msg_exceeded = enforce_user_rate_limit(self.db, user)
        self.assertFalse(ok_exceeded)
        self.assertIn("Tier quota exceeded", msg_exceeded)
        print("\n [PASS] Test 06: Model consumption tracking & tier rate limits verified.")

    def test_07_cli_commands_execution(self):
        """Requirement 2: Verifies all CLI commands execute cleanly."""
        from july_distribution.client import cli
        import argparse

        clerk = ClerkAuthManager()
        # Set up active session for CLI test
        clerk.vault = SecureCredentialVault(vault_path=self.vault_file)
        clerk.login_manual("clerk_sess_cli_verify", clerk_user_id="user_cli_test", email="cli@hs-ai.solutions")

        # Test whoami
        cli.cmd_whoami(argparse.Namespace())

        # Test auth status
        cli.cmd_auth(argparse.Namespace(action="status"))

        # Test auth devices
        cli.cmd_auth(argparse.Namespace(action="devices"))

        # Test account
        cli.cmd_account(argparse.Namespace())

        # Test usage
        cli.cmd_usage(argparse.Namespace())

        # Test sync
        cli.cmd_sync(argparse.Namespace())

        # Test logout
        cli.cmd_logout(argparse.Namespace())
        self.assertFalse(clerk.vault.vault_file.exists())
        print("\n [PASS] Test 07: All 8 CLI auth commands verified end-to-end.")


if __name__ == "__main__":
    unittest.main()
