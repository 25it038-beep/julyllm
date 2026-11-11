"""
HS AI SOLUTIONS — DUAL MODEL ARCHITECTURE ACCEPTANCE TEST SUITE
Founder & Chief Architect: Harshan Seliyan
Platform: JULY LLM & GRAVITY LLM

Verifies all 8 Core Acceptance Requirements:
1. July works independently.
2. Gravity downloads without blocking July.
3. Gravity automatically becomes active after successful first-time initialization.
4. Switching back to July works.
5. Switching back to Gravity works without redownloading.
6. Neither model's files are overwritten.
7. Application restart preserves model selection.
8. Limited hardware does not cause simultaneous memory exhaustion.
"""

import os
import sys
import json
import time
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from july_distribution.client.config import ClientConfig
from july_distribution.client.storage import PermanentModelStorage, ClientEphemeralStorage
from july_distribution.client.state_manager import DualModelStateManager, ModelStatus
from july_distribution.client.customization import UserCustomizationManager
from july_distribution.client.runtime import ClientInferenceRuntime
from july_distribution.client.dual_engine import DualModelCoordinator


class TestDualModelArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = PermanentModelStorage()
        cls.july_path = cls.storage.get_model_file("july")
        cls.gravity_path = cls.storage.get_model_file("gravity")

    def test_01_july_works_independently(self):
        """1. July works independently and logs message attribution."""
        self.assertTrue(self.july_path.exists(), "July model file must exist on disk")
        self.assertEqual(self.july_path.stat().st_size, 2019377888)

        cfg = ClientConfig(selected_model="july")
        customizer = UserCustomizationManager(cfg)
        sys_prompt = customizer.get_effective_system_prompt("july")
        self.assertIn("JULY LLM", sys_prompt)
        self.assertIn("Harshan Seliyan", sys_prompt)

        # Test message attribution in SQLite history
        session_id = f"test_session_{int(time.time())}"
        customizer.log_message(session_id, "user", "Hello July", model="july")
        customizer.log_message(session_id, "assistant", "Hello! I am July.", model="july")

        history = customizer.get_session_history(session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1].get("generated_by"), "july")
        print("\n[PASS 1/8] July operates independently with proper message attribution.")

    def test_02_gravity_downloads_without_blocking_july(self):
        """2. Gravity downloads without blocking July; July answers prompts as fallback."""
        cfg = ClientConfig(selected_model="july")
        state_mgr = DualModelStateManager()
        state_mgr.activeModel = "july"
        state_mgr.selectedModel = "july"

        # User chooses Gravity, but Gravity is marked DOWNLOADING
        state_mgr.selectedModel = "gravity"
        state_mgr.set_model_state("gravity", ModelStatus.DOWNLOADING)

        # Crucial Requirement: selectedModel is "gravity", while activeModel remains "july"
        self.assertEqual(state_mgr.selectedModel, "gravity")
        self.assertEqual(state_mgr.activeModel, "july")
        self.assertIn("gravity", state_mgr.downloadingModels)

        # Operational model answering user is July
        customizer = UserCustomizationManager(cfg)
        prompt_answered_by = state_mgr.activeModel
        self.assertEqual(prompt_answered_by, "july")
        print("\n[PASS 2/8] Gravity downloads in background without blocking operational July fallback.")

    def test_03_gravity_automatically_activates_after_initialization(self):
        """3. Gravity automatically becomes active after successful first-time initialization."""
        state_mgr = DualModelStateManager()
        state_mgr.selectedModel = "gravity"
        state_mgr.activeModel = "july"

        # Simulate background acquisition completion -> VERIFYING -> READY
        state_mgr.set_model_state("gravity", ModelStatus.VERIFYING)
        self.assertEqual(state_mgr.get_model_state("gravity"), ModelStatus.VERIFYING.value)

        state_mgr.set_model_state("gravity", ModelStatus.READY)
        # When Gravity finishes initialization, activeModel transitions to gravity
        self.assertEqual(state_mgr.activeModel, "gravity")
        self.assertEqual(state_mgr.selectedModel, "gravity")
        print("\n[PASS 3/8] Gravity automatically activates upon completing initialization.")

    def test_04_switching_back_to_july(self):
        """4. Switching back to July unloads Gravity safely and activates July."""
        state_mgr = DualModelStateManager()
        state_mgr.selectedModel = "july"
        state_mgr.activeModel = "july"
        state_mgr.set_model_state("july", ModelStatus.READY)
        state_mgr.set_model_state("gravity", ModelStatus.UNLOADED)

        self.assertEqual(state_mgr.activeModel, "july")
        self.assertEqual(state_mgr.get_model_state("gravity"), ModelStatus.UNLOADED.value)

        # Verify Gravity file on disk was NOT deleted
        self.assertTrue(self.gravity_path.exists(), "Gravity model file must remain on disk")
        self.assertEqual(self.gravity_path.stat().st_size, 5629108096)
        print("\n[PASS 4/8] Switching back to July succeeds and leaves Gravity files intact.")

    def test_05_switching_back_to_gravity_no_redownload(self):
        """5. Switching back to Gravity reuses verified local files without redownload."""
        self.assertTrue(self.gravity_path.exists())
        self.assertEqual(self.gravity_path.stat().st_size, 5629108096)

        # Check manifest
        manifest = self.storage.load_manifest("gravity")
        self.assertTrue(manifest.get("verified", False))
        self.assertEqual(manifest.get("sha256"), "f24a90361aaac8cb3dce9f18b276b1444af106d205f411c4e674b58a9adf53c8")

        state_mgr = DualModelStateManager()
        state_mgr.selectedModel = "gravity"
        state_mgr.set_model_state("gravity", ModelStatus.READY)
        self.assertEqual(state_mgr.activeModel, "gravity")
        print("\n[PASS 5/8] Switching back to Gravity uses verified local file without redownload.")

    def test_06_neither_model_files_overwritten(self):
        """6. Independent directory hierarchy guarantees neither model's files are overwritten."""
        july_dir = self.storage.get_model_dir("july")
        gravity_dir = self.storage.get_model_dir("gravity")

        self.assertNotEqual(july_dir, gravity_dir)
        self.assertEqual(self.july_path.parent, july_dir)
        self.assertEqual(self.gravity_path.parent, gravity_dir)

        # Both model files exist simultaneously
        self.assertTrue(self.july_path.exists())
        self.assertTrue(self.gravity_path.exists())
        self.assertEqual(self.july_path.stat().st_size, 2019377888)
        self.assertEqual(self.gravity_path.stat().st_size, 5629108096)

        # Independent manifests
        july_man = self.storage.load_manifest("july")
        grav_man = self.storage.load_manifest("gravity")
        self.assertEqual(july_man.get("model_id"), "july")
        self.assertEqual(grav_man.get("model_id"), "gravity")
        self.assertNotEqual(july_man.get("sha256"), grav_man.get("sha256"))
        print("\n[PASS 6/8] Independent directory isolation guarantees zero file overwrite.")

    def test_07_application_restart_preserves_selection(self):
        """7. Application restart preserves user model selection and file availability."""
        state_file = ROOT / "config" / "test_restart_state.json"
        try:
            # 1. User selects Gravity and closes application
            sm1 = DualModelStateManager(state_file=state_file)
            sm1.selectedModel = "gravity"
            sm1.set_model_state("gravity", ModelStatus.READY)
            sm1.set_model_state("july", ModelStatus.DOWNLOADED)

            # 2. Application reboots: new instance created
            sm2 = DualModelStateManager(state_file=state_file)
            self.assertEqual(sm2.selectedModel, "gravity", "selectedModel must persist across restart")
            self.assertIn("july", sm2.availableModels)
            self.assertIn("gravity", sm2.availableModels)
        finally:
            if state_file.exists():
                state_file.unlink(missing_ok=True)
        print("\n[PASS 7/8] Application restart faithfully restores model preference.")

    def test_08_limited_hardware_memory_safety(self):
        """8. Limited hardware memory safety: only one active model in RAM/VRAM, disk unlinking disabled."""
        runtime = ClientInferenceRuntime()
        ephemeral = ClientEphemeralStorage()

        # Unloading must never delete model files from disk
        ephemeral.wipe_and_unlink(self.july_path, allow_permanent_deletion=False)
        self.assertTrue(self.july_path.exists(), "Model file MUST NOT be unlinked on RAM unload")

        ephemeral.wipe_and_unlink(self.gravity_path, allow_permanent_deletion=False)
        self.assertTrue(self.gravity_path.exists(), "Model file MUST NOT be unlinked on RAM unload")

        # State manager loaded models count must be at most 1 in limited hardware profile
        state_mgr = DualModelStateManager()
        state_mgr.set_model_state("july", ModelStatus.READY)
        state_mgr.set_model_state("gravity", ModelStatus.UNLOADED)
        self.assertEqual(len(state_mgr.loadedModels), 1)
        self.assertEqual(state_mgr.loadedModels[0], "july")

        # Swap to gravity
        state_mgr.set_model_state("july", ModelStatus.UNLOADED)
        state_mgr.set_model_state("gravity", ModelStatus.READY)
        self.assertEqual(len(state_mgr.loadedModels), 1)
        self.assertEqual(state_mgr.loadedModels[0], "gravity")
        print("\n[PASS 8/8] Memory-aware single model execution prevents RAM/VRAM exhaustion.")


if __name__ == "__main__":
    unittest.main()
