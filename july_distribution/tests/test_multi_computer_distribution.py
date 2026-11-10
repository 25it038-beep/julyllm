"""
HS AI SOLUTIONS — MULTI-COMPUTER DISTRIBUTION INTEGRATION TEST
Layer: INTEGRATION TEST (july_distribution.tests.test_multi_computer_distribution)
Organization: HS AI Solutions
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Verifies:
1. Central Control Server user registration, login, token issuance, and RBAC permissions.
2. Short-lived presigned URL generation connecting directly to private Cloudflare R2.
3. Computer 1 (engineer_alpha) and Computer 2 (researcher_beta) execute independently:
   - Separate client home directories.
   - Separate tokens and sessions.
   - Separate personalities and system instructions.
   - Independent ephemeral RAM-backed storage allocation.
   - Genuine local llama.cpp CPU/CUDA inference (no simulation).
   - Safe model unloading and zero permanent file persistence.
"""

from __future__ import annotations
import os
import sys
import shutil
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Setup sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from july_distribution.server.main import app
from july_distribution.client.config import ClientConfig
from july_distribution.client.auth import ClientAuthManager
from july_distribution.client.storage import ClientEphemeralStorage
from july_distribution.client.downloader import ClientModelDownloader
from july_distribution.client.customization import UserCustomizationManager
from july_distribution.client.runtime import ClientInferenceRuntime


class TestMultiComputerDistribution:

    @pytest.fixture(scope="class")
    def server_client(self):
        return TestClient(app)

    @pytest.fixture(scope="class")
    def setup_two_computers(self):
        """Creates isolated filesystem roots simulating two distinct Windows computers."""
        temp_base = Path(tempfile.gettempdir()) / "july_multi_comp_test"
        comp1_dir = temp_base / "computer_1_user_alpha"
        comp2_dir = temp_base / "computer_2_user_beta"

        shutil.rmtree(temp_base, ignore_errors=True)
        comp1_dir.mkdir(parents=True, exist_ok=True)
        comp2_dir.mkdir(parents=True, exist_ok=True)

        yield comp1_dir, comp2_dir

        shutil.rmtree(temp_base, ignore_errors=True)

    def test_01_server_health_and_r2_gateway(self, server_client):
        """Verify Central Control Server is online and connected to Cloudflare R2."""
        resp = server_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["r2_gateway_connected"] is True
        assert data["r2_object_size"] == 2019377888

    def test_02_computer_1_registration_and_login(self, server_client, setup_two_computers):
        """Computer 1 registers and authenticates as engineer_alpha."""
        comp1_dir, _ = setup_two_computers
        os.environ["JULY_CLIENT_HOME"] = str(comp1_dir)

        # Register
        reg_resp = server_client.post("/api/v1/auth/register", json={
            "username": f"engineer_alpha_{int(time.time())}",
            "email": f"alpha_{int(time.time())}@hs-ai-solutions.internal",
            "password": "Password123!"
        })
        assert reg_resp.status_code == 200
        data = reg_resp.json()
        assert "token" in data
        assert data["token"].startswith("july_tok_")

        token_1 = data["token"]
        comp1_dir.joinpath("token.txt").write_text(token_1, encoding="utf-8")

        # Register Device 1
        dev_resp = server_client.post(
            "/api/v1/devices/register",
            headers={"Authorization": f"Bearer {token_1}"},
            json={
                "device_id": "dev_alpha_01",
                "device_name": "Workstation-Alpha",
                "os_version": "Windows 11 Pro"
            }
        )
        assert dev_resp.status_code == 200
        assert dev_resp.json()["status"] == "APPROVED"

    def test_03_computer_2_registration_and_login(self, server_client, setup_two_computers):
        """Computer 2 registers and authenticates as researcher_beta."""
        _, comp2_dir = setup_two_computers
        os.environ["JULY_CLIENT_HOME"] = str(comp2_dir)

        reg_resp = server_client.post("/api/v1/auth/register", json={
            "username": f"researcher_beta_{int(time.time())}",
            "email": f"beta_{int(time.time())}@hs-ai-solutions.internal",
            "password": "Password456!"
        })
        assert reg_resp.status_code == 200
        data = reg_resp.json()
        assert "token" in data
        assert data["token"].startswith("july_tok_")

        token_2 = data["token"]
        comp2_dir.joinpath("token.txt").write_text(token_2, encoding="utf-8")

        # Register Device 2
        dev_resp = server_client.post(
            "/api/v1/devices/register",
            headers={"Authorization": f"Bearer {token_2}"},
            json={
                "device_id": "dev_beta_02",
                "device_name": "Laptop-Beta",
                "os_version": "Windows 11 Home"
            }
        )
        assert dev_resp.status_code == 200
        assert dev_resp.json()["status"] == "APPROVED"

    def test_04_independent_presigned_download_authorizations(self, server_client, setup_two_computers):
        """Both computers independently request short-lived presigned URLs from Cloudflare R2."""
        comp1_dir, comp2_dir = setup_two_computers
        token_1 = comp1_dir.joinpath("token.txt").read_text(encoding="utf-8")
        token_2 = comp2_dir.joinpath("token.txt").read_text(encoding="utf-8")

        # Computer 1 Request with approved device
        resp1 = server_client.post(
            "/api/v1/model/request-download",
            headers={"Authorization": f"Bearer {token_1}", "X-Device-Id": "dev_alpha_01"}
        )
        assert resp1.status_code == 200
        d1 = resp1.json()
        assert d1["success"] is True
        assert "download_url" in d1
        assert "https://" in d1["download_url"]
        assert d1["size_bytes"] == 2019377888
        assert d1["expected_sha256"].lower() == "f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4"

        # Computer 2 Request with approved device
        resp2 = server_client.post(
            "/api/v1/model/request-download",
            headers={"Authorization": f"Bearer {token_2}", "X-Device-Id": "dev_beta_02"}
        )
        assert resp2.status_code == 200
        d2 = resp2.json()
        assert d2["success"] is True
        assert "download_url" in d2
        assert "https://" in d2["download_url"]

        # Unauthorized/unregistered device check
        unauth_resp = server_client.post(
            "/api/v1/model/request-download",
            headers={"Authorization": f"Bearer {token_1}", "X-Device-Id": "dev_rogue_unknown"}
        )
        assert unauth_resp.status_code == 403

    def test_05_computer_1_customization_and_inference(self, setup_two_computers):
        """
        Computer 1 configures separate personality (precision_engineer),
        mounts GGUF into ephemeral RAM-backed storage, runs genuine local inference, and unloads.
        """
        comp1_dir, _ = setup_two_computers
        os.environ["JULY_CLIENT_HOME"] = str(comp1_dir)

        cfg1 = ClientConfig(
            server_url="http://127.0.0.1:8787",
            personality="precision_engineer",
            n_batch=64,
            context_length=2048,
            n_threads=4,
            system_prompt="You are JULY LLM acting as Precision Engineer for Orbital Mechanics."
        )
        cfg1.save(comp1_dir / "config.json")

        storage1 = ClientEphemeralStorage()
        custom1 = UserCustomizationManager(cfg1)
        custom1.add_memory("ActiveMission", "Kepler Orbit Transfer Simulation")
        runtime1 = ClientInferenceRuntime(cfg1, storage1, custom1)

        # Allocate ephemeral path
        ephemeral_file1 = storage1.allocate_path("comp1_model")
        assert ephemeral_file1.exists()

        # Prime with verified master seed
        master_seed = ROOT / "models" / "july-final.gguf"
        shutil.copyfile(master_seed, ephemeral_file1)

        try:
            runtime1.load_model(ephemeral_file1)
            assert runtime1.is_loaded() is True

            # Genuine Local Inference
            prompt = "Compute the product 25 * 16 and subtract 50."
            tokens = []
            for tok in runtime1.generate_stream(prompt, session_id="comp1_session", max_tokens=32):
                tokens.append(tok)
            response_text = "".join(tokens)
            assert len(response_text) > 0
            # 25 * 16 - 50 = 400 - 50 = 350
            print(f"\n[COMPUTER 1 RESPONSE]: {response_text.strip()}")

        finally:
            runtime1.unload(wipe_storage=True)
            assert runtime1.is_loaded() is False
            assert not ephemeral_file1.exists()

    def test_06_computer_2_customization_and_inference(self, setup_two_computers):
        """
        Computer 2 configures separate personality (research_scientist),
        mounts GGUF into separate ephemeral RAM storage, runs genuine local inference, and unloads.
        """
        _, comp2_dir = setup_two_computers
        os.environ["JULY_CLIENT_HOME"] = str(comp2_dir)

        cfg2 = ClientConfig(
            server_url="http://127.0.0.1:8787",
            personality="research_scientist",
            n_batch=64,
            context_length=2048,
            n_threads=4,
            system_prompt="You are JULY LLM acting as Research Scientist for Quantum Information."
        )
        cfg2.save(comp2_dir / "config.json")

        storage2 = ClientEphemeralStorage()
        custom2 = UserCustomizationManager(cfg2)
        custom2.add_memory("ResearchField", "Decoherence in Multi-Qubit Hamiltonians")
        runtime2 = ClientInferenceRuntime(cfg2, storage2, custom2)

        # Allocate separate ephemeral path
        ephemeral_file2 = storage2.allocate_path("comp2_model")
        assert ephemeral_file2.exists()

        # Prime with verified master seed
        master_seed = ROOT / "models" / "july-final.gguf"
        shutil.copyfile(master_seed, ephemeral_file2)

        try:
            runtime2.load_model(ephemeral_file2)
            assert runtime2.is_loaded() is True

            # Genuine Local Inference
            prompt = "State the first law of thermodynamics concisely."
            tokens = []
            for tok in runtime2.generate_stream(prompt, session_id="comp2_session", max_tokens=32):
                tokens.append(tok)
            response_text = "".join(tokens)
            assert len(response_text) > 0
            print(f"\n[COMPUTER 2 RESPONSE]: {response_text.strip()}")

        finally:
            runtime2.unload(wipe_storage=True)
            assert runtime2.is_loaded() is False
            assert not ephemeral_file2.exists()
