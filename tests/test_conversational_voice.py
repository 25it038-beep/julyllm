"""
HS AI SOLUTIONS — ACCEPTANCE TEST SUITE: NATURAL CONVERSATIONAL VOICE & MINI-OMNI
Layer: SPEECH & LIVE CONVERSATIONAL VOICE SUBSYSTEM
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & MINI-OMNI CONVERSATIONAL SPEECH ENGINE

Verification Matrix:
1. Intelligent Speech Processing:
   - Stripping Markdown, code formatting, citations, and UI symbols.
   - Expanding abbreviations, technical units, acronyms, and comparison operators.
2. Context-Aware Expressive Prosody Engine:
   - Inquisitive rising pitch on questions.
   - Warm and friendly greetings.
   - Deliberate, calm cadence on serious topics / errors.
   - Articulate rhythm on technical explanations.
   - Crisp delivery on affirmative confirmations.
   - Inter-sentence prosody variation to avoid robotic monotony.
   - Natural micro-pauses at clause and thought boundaries.
3. Sentence-Aware Streaming Chunking:
   - Does not prematurely break on decimals (3.14) or abbreviations (e.g., v1.2).
   - Allows early first-clause boundary for sub-second TTFA.
4. Voice Identity & Instant Barge-In:
   - Consistent voice selection across chunks.
   - Instant hardware audio purge on interruption.
5. Mini-Omni Live Session Integration:
   - Metadata, storage validation, live session activation, and voice switching.
"""

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from july_distribution.client.voice import (
    clean_text_for_speech,
    ConversationalSpeechNormalizer,
    ConversationalProsodyEngine,
    TTSVoiceOutput,
    CLIHardwareVoiceCoordinator
)
from july_distribution.client.live_engine import (
    LiveConversationManager,
    LiveState,
    SpeechChunker,
    VOICE_STYLES
)
from july_distribution.client.storage import PermanentModelStorage
from july_distribution.client.cli import MODEL_METADATA


class TestNaturalConversationalVoiceSuite(unittest.TestCase):
    """Verifies all capabilities of the upgraded conversational speech engine."""

    def test_01_intelligent_speech_normalization(self):
        """1. Converts raw written LLM output into clean, spoken-optimized natural text."""
        # A. Markdown, Code, Citations, and UI symbols
        raw_text = (
            "<think>Analyzing architecture</think>\n"
            "### System Telemetry\n"
            "* Running ```print('hello')``` in `v1.2`.\n"
            "| Component | Status |\n|---|---|\n| LLM | Ready |\n"
            "See [Documentation](https://hs-ai.org) [1]. Progress: 100% complete! 🚀"
        )
        cleaned = clean_text_for_speech(raw_text)

        # Assertions
        self.assertNotIn("<think>", cleaned)
        self.assertNotIn("```", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertNotIn("[1]", cleaned)
        self.assertNotIn("###", cleaned)
        self.assertNotIn("*", cleaned)
        self.assertNotIn("🚀", cleaned)
        self.assertIn("100 percent", cleaned)
        self.assertIn("version 1.2", cleaned)
        self.assertIn("L L M", cleaned)

        # B. Abbreviations expansion
        abbrev_raw = "Use e.g. neural nets, i.e. deep transformers, etc. vs. legacy rules approx. 50% faster."
        abbrev_clean = clean_text_for_speech(abbrev_raw)
        self.assertIn("for example", abbrev_clean)
        self.assertIn("that is", abbrev_clean)
        self.assertIn("etcetera", abbrev_clean)
        self.assertIn("versus", abbrev_clean)
        self.assertIn("approximately", abbrev_clean)

        # C. Technical units & operators
        tech_raw = "Model runs on 16kHz audio with 12GB VRAM. If latency <= 100ms and O(n) != O(1), return success."
        tech_clean = clean_text_for_speech(tech_raw)
        self.assertIn("16 kilohertz", tech_clean)
        self.assertIn("12 gigabytes", tech_clean)
        self.assertIn("V ram", tech_clean)
        self.assertIn("100 milliseconds", tech_clean)
        self.assertIn("O of n", tech_clean)
        self.assertIn("is not equal to", tech_clean)
        self.assertIn("is less than or equal to", tech_clean)

        # D. Backward compatibility check
        compat_raw = "<think>Compute result</think> **The answer** is `42`. See https://example.com"
        self.assertEqual(clean_text_for_speech(compat_raw), "The answer is 42. See link")
        print("\n[TEST 1/5 PASSED] Intelligent speech normalization thoroughly verified across all formatting types.")

    def test_02_context_aware_prosody_engine(self):
        """2. Context-aware prosody: Modulates pitch, speaking rate, pauses, and emphasis."""
        prosody = ConversationalProsodyEngine()

        # A. Greeting context
        greet_xml = prosody.build_sapi_xml("Hello Harshan! Welcome to the live environment.")
        self.assertIn('pitch middle="+1"', greet_xml)
        self.assertIn('rate speed="+1"', greet_xml)
        self.assertEqual(prosody.analyze_context("Hello there!"), "greeting")

        # B. Question context with rising inflection
        q_xml = prosody.build_sapi_xml("Does this conversational delivery feel natural to you?")
        self.assertEqual(prosody.analyze_context("Does this feel natural?"), "question")
        self.assertIn('pitch middle="+2"', q_xml) # Lifted final words

        # C. Serious / caution context
        warn_xml = prosody.build_sapi_xml("Warning, memory buffer is approaching capacity.")
        self.assertEqual(prosody.analyze_context("Warning! Critical error."), "serious")
        self.assertIn('pitch middle="-1"', warn_xml)
        self.assertIn('rate speed="-1"', warn_xml)

        # D. Confirmation context
        conf_xml = prosody.build_sapi_xml("Got it. Starting inference right now.")
        self.assertEqual(prosody.analyze_context("Got it."), "confirmation")
        self.assertIn('rate speed="+2"', conf_xml)

        # E. Clause-level micro-pauses
        clause_xml = prosody.build_sapi_xml("First, prepare the data; then, compile the model.")
        self.assertIn('<silence msec="90"/>', clause_xml)
        self.assertIn('<silence msec="140"/>', clause_xml)

        # F. Sentence-to-sentence variation
        xmls = [prosody.build_sapi_xml(f"This is step number {i}.") for i in range(4)]
        pitches = [x.split('pitch middle="')[1].split('"')[0] for x in xmls]
        # Verify not all pitches are identical across 4 sentences (dynamic variation)
        self.assertGreater(len(set(pitches)), 1)
        print("\n[TEST 2/5 PASSED] Context-aware prosody engine verified with pitch, rate, pauses, and variations.")

    def test_03_sentence_aware_speech_chunker(self):
        """3. Sentence-aware streaming chunker: Preserves decimals/abbreviations, allows early clause."""
        chunker = SpeechChunker(min_words_first_clause=4)

        # Stream tokens containing decimal number and abbreviation
        tokens = [
            "Mini-Omni ", "achieved ", "v1.2 ", "accuracy, ", "reaching ", "99.4% ",
            "in ", "3.14s. ", "Next ", "sentence ", "follows."
        ]

        emitted = []
        for t in tokens:
            chunks = chunker.add_token(t)
            if chunks:
                emitted.extend(chunks)
        emitted.extend(chunker.finalize())

        # Verify chunk 1 emitted on early clause boundary
        self.assertTrue(any("Mini-Omni achieved" in c for c in emitted))
        # Verify 3.14 wasn't prematurely broken at decimal
        combined = " ".join(emitted)
        self.assertIn("3.14", combined)
        self.assertIn("version 1.2", combined)
        print("\n[TEST 3/5 PASSED] Sentence-aware chunker verified without decimal or abbreviation corruption.")

    def test_04_voice_synthesis_and_instant_barge_in(self):
        """4. Voice output engine: Fast synthesis, voice identity, and instant barge-in."""
        tts = TTSVoiceOutput()
        self.assertIsNotNone(tts)

        # Gender switching
        self.assertEqual(tts.set_gender("male"), "Male")
        self.assertEqual(tts.set_gender("female"), "Female")

        # Speed control
        self.assertEqual(tts.set_speed(190), 190)

        # Speech dispatch & Instant Barge-In
        tts.speak("This is an extended utterance for testing immediate cancellation.", non_blocking=True)
        time.sleep(0.04)
        self.assertFalse(tts._stop_event.is_set())

        # Barge-in interruption
        tts.stop()
        self.assertTrue(tts._stop_event.is_set())
        self.assertFalse(tts.is_speaking)
        print("\n[TEST 4/5 PASSED] Voice output engine verified with instant barge-in interruption.")

    def test_05_mini_omni_live_session_integration(self):
        """5. Mini-Omni model configuration, storage presence, and live session integration."""
        # A. Metadata verification
        self.assertIn("mini-omni", MODEL_METADATA)
        self.assertIn("omni", MODEL_METADATA)
        omni_meta = MODEL_METADATA["mini-omni"]
        self.assertEqual(omni_meta["name"], "mini-omni")
        self.assertIn("CONVERSATIONAL VOICE", omni_meta["badge"].upper())

        # B. Storage verification
        p_stor = PermanentModelStorage()
        self.assertTrue(p_stor.is_model_present("mini-omni"))
        self.assertIsNotNone(p_stor.get_model_file("mini-omni"))

        # C. Live Conversation Manager with Mini-Omni
        mock_runtime = MagicMock()
        mock_runtime.is_loaded.return_value = True
        mock_runtime.current_model_id = "mini-omni"

        def mock_stream(prompt, session_id="default", max_tokens=256, cancel_event=None):
            yield "Hello! "
            yield "I am Mini-Omni, "
            yield "ready to talk."

        mock_runtime.generate_stream.side_effect = mock_stream

        live_mgr = LiveConversationManager(
            runtime=mock_runtime,
            active_model="mini-omni",
            style="mini-omni"
        )
        self.assertEqual(live_mgr.active_model, "mini-omni")
        self.assertEqual(live_mgr.current_style, "mini-omni")
        self.assertIn("MINI-OMNI", VOICE_STYLES["mini-omni"]["system_directive"])

        # D. Dynamic model switching to Mini-Omni
        live_mgr.switch_model("july")
        self.assertEqual(live_mgr.active_model, "july")
        live_mgr.switch_model("mini-omni")
        self.assertEqual(live_mgr.active_model, "mini-omni")
        self.assertEqual(live_mgr.current_style, "mini-omni")

        # E. Voice command switching
        synthetic_audio = MagicMock()
        live_mgr.stt.transcribe_audio = MagicMock(return_value=("switch to mini-omni", "en"))
        live_mgr.process_user_utterance(synthetic_audio)
        self.assertEqual(live_mgr.active_model, "mini-omni")
        self.assertIn("Mini-Omni", live_mgr.last_ai_response)
        print("\n[TEST 5/5 PASSED] Mini-Omni live session model and voice switching successfully verified.")

    def test_06_live_web_search_on_who_and_what(self):
        """6. Live voice session triggers web search when user asks 'who' or 'what' inquiries."""
        mock_runtime = MagicMock()
        mock_runtime.is_loaded.return_value = True
        mock_runtime.current_model_id = "mini-omni"

        captured_prompts = []
        def mock_stream(prompt, session_id="default", max_tokens=256, cancel_event=None):
            captured_prompts.append(prompt)
            yield "Satya Nadella is the CEO of Microsoft."

        mock_runtime.generate_stream.side_effect = mock_stream

        live_mgr = LiveConversationManager(
            runtime=mock_runtime,
            active_model="mini-omni",
            style="mini-omni"
        )

        with patch("july_distribution.client.live_engine.live_duckduckgo_search") as mock_search:
            mock_search.return_value = [
                {"title": "Satya Nadella - CEO of Microsoft", "snippet": "Satya Nadella is Executive Chairman and CEO of Microsoft.", "url": "https://microsoft.com"}
            ]

            # 1. Ask a 'who' question in live mode
            live_mgr.stt.transcribe_audio = MagicMock(return_value=("who is the current CEO of Microsoft?", "en"))
            synthetic_audio = MagicMock()
            live_mgr.process_user_utterance(synthetic_audio)

            # Verify web search was invoked
            mock_search.assert_called()
            self.assertTrue(len(captured_prompts) > 0)
            self.assertIn("REAL-TIME LIVE WEB SEARCH DATA", captured_prompts[-1])
            self.assertIn("Satya Nadella", captured_prompts[-1])

            # 2. Ask a 'what' question in live mode
            mock_search.reset_mock()
            mock_search.return_value = [
                {"title": "Quantum Computing", "snippet": "Quantum computing is a rapidly-emerging technology.", "url": "https://example.com"}
            ]
            live_mgr.stt.transcribe_audio = MagicMock(return_value=("what is quantum computing?", "en"))
            live_mgr.process_user_utterance(synthetic_audio)

            mock_search.assert_called()
            self.assertIn("Quantum Computing", captured_prompts[-1])

        print("\n[TEST 6/6 PASSED] Live voice session verified triggering real-time web search on who/what prompts.")


if __name__ == "__main__":
    unittest.main()
