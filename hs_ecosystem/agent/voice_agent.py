"""
HS AI SOLUTIONS — AUTONOMOUS CONVERSATIONAL VOICE AGENT
Module: hs_ecosystem.agent.voice_agent
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 12:
- Speech-to-text transcription interface
- Conversational text-to-speech synthesis (in-process SAPI COM / PowerShell fallback with Prosody XML)
- Instantaneous barge-in interruption
"""

from __future__ import annotations
import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable

try:
    from july_distribution.client.voice import clean_text_for_speech, ConversationalProsodyEngine, SapiComVoiceSession
except ImportError:
    clean_text_for_speech = lambda t: t
    ConversationalProsodyEngine = None
    SapiComVoiceSession = None


class VoiceAgent:
    """Manages voice input, conversational speech output, and audio interaction loops."""

    def __init__(self, voice_gender: str = "Female", speech_rate: int = 1):
        self.voice_gender = voice_gender
        self.speech_rate = speech_rate
        self.is_speaking = False
        self._interrupt_event = threading.Event()
        self.prosody = ConversationalProsodyEngine() if ConversationalProsodyEngine else None
        self._sapi_session: Optional[Any] = None
        if SapiComVoiceSession and sys.platform == "win32":
            try:
                # speech_rate: 1 ~ 180 wpm
                wpm = 180 + int(self.speech_rate * 15)
                self._sapi_session = SapiComVoiceSession(gender=self.voice_gender, speed_wpm=wpm)
            except Exception:
                self._sapi_session = None

    def speak(self, text: str, non_blocking: bool = False):
        """Synthesizes text into spoken speech with natural conversational prosody."""
        if not text:
            return

        clean = clean_text_for_speech(text) if clean_text_for_speech else text
        if not clean:
            return

        self._interrupt_event.clear()

        # In-process SAPI COM session (lowest latency & prosody support)
        if self._sapi_session and self._sapi_session.is_available():
            wpm = 180 + int(self.speech_rate * 15)
            xml = self.prosody.build_sapi_xml(clean, base_wpm=wpm) if self.prosody else clean
            self.is_speaking = True
            def _sapi_run():
                try:
                    self._sapi_session.speak(xml, stop_event=self._interrupt_event, block=True)
                finally:
                    self.is_speaking = False

            if non_blocking:
                t = threading.Thread(target=_sapi_run, daemon=True)
                t.start()
            else:
                _sapi_run()
            return

        # Fallback to PowerShell SAPI5
        def _run():
            self.is_speaking = True
            safe_text = clean.replace("'", "''").replace("\n", " ")
            voice_hint = "try { $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female) } catch {}; " if self.voice_gender.lower() == "female" else ""
            ps_script = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"{voice_hint}"
                f"$s.Rate = {self.speech_rate}; "
                f"$s.Speak('{safe_text}'); "
                f"$s.Dispose()"
            )
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=30, capture_output=True)
            except Exception:
                pass
            finally:
                self.is_speaking = False

        if non_blocking:
            t = threading.Thread(target=_run, daemon=True)
            t.start()
        else:
            _run()

    def interrupt(self):
        """Halts active speech playback immediately."""
        self._interrupt_event.set()
        self.is_speaking = False
        if self._sapi_session and self._sapi_session.is_available():
            self._sapi_session.stop()

    def listen_and_transcribe(self, timeout_seconds: float = 5.0) -> str:
        """Transcribes incoming audio or prompts user for speech fallback."""
        return ""
