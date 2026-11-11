"""
HS AI SOLUTIONS — CLI VOICE INTELLIGENCE ENGINE (WHISPER STT & MULTILINGUAL TTS)
Layer: VOICE INTERACTION SUBSYSTEM (july_distribution.client.voice)
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & GRAVITY LLM DUAL-MODEL CLI ENVIRONMENT

Features:
1. Microphone Audio Capture (sounddevice, 16kHz float32 mono PCM).
2. Whisper STT Integration (Automatic Hardware-Aware Model Sizing: tiny/base/small/medium).
3. Multilingual Automatic Language Detection & Explicit Language Switching.
4. Voice Transcription Preview & Pre-Submission Editing.
5. Multilingual TTS Voice Output with Graceful Fallback:
   - Priority 1: Chatterbox Multilingual Engine (if available)
   - Priority 2: Piper Neural TTS (lightweight fallback)
   - Priority 3: Native High-Performance Windows SAPI5 / pyttsx3 (built-in, zero external binary dependency)
6. Asynchronous, Non-Blocking Speech Playback & Instant Playback Interruption.
7. Total Decoupling from LLM Inference Engine & Robust Error Containment.
"""

from __future__ import annotations
import os
import re
import sys
import time
import shutil
import logging
import threading
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Tuple

logger = logging.getLogger("july.voice")


def clean_text_for_speech(text: str) -> str:
    """Strips markdown code blocks, think tags, URLs, and formatting for clean natural speech."""
    if not text:
        return ""
    # Remove <think>...</think> blocks
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove code blocks ```...```
    cleaned = re.sub(r"```.*?```", " [code snippet omitted] ", cleaned, flags=re.DOTALL)
    # Remove inline code `...`
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Remove URLs
    cleaned = re.sub(r"https?://\S+", "link", cleaned)
    # Remove Markdown headers, bold, italics, bullets
    cleaned = re.sub(r"#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"^[*\-•]\s+", "", cleaned, flags=re.MULTILINE)
    # Normalize whitespaces
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


class WhisperVoiceInput:
    """Manages microphone input capture and Whisper speech-to-text transcription."""

    SUPPORTED_MODELS = ("tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en")

    def __init__(self, hardware_info: Optional[Dict[str, Any]] = None):
        self.is_enabled: bool = False
        self.language: str = "auto"
        self._model = None
        self._lock = threading.Lock()
        self.model_name = self._select_default_model(hardware_info)

    def _select_default_model(self, hardware_info: Optional[Dict[str, Any]]) -> str:
        """Selects optimal model size based on available GPU VRAM and system RAM."""
        try:
            cache_dir = Path.home() / ".cache" / "whisper"
            if (cache_dir / "base.pt").exists() and (cache_dir / "base.pt").stat().st_size > 100_000_000:
                return "base"
            if (cache_dir / "tiny.pt").exists():
                return "tiny"

            if not hardware_info:
                from .hardware import detect_client_hardware
                hardware_info = detect_client_hardware()

            gpu_avail = hardware_info.get("gpu_available", False)
            vram_mb = hardware_info.get("vram_total_mb", 0.0)
            ram_gb = hardware_info.get("ram_total_gb", 8.0)

            if gpu_avail and vram_mb >= 4000 and ram_gb >= 12.0:
                return "base"
            else:
                return "tiny"
        except Exception:
            return "tiny"

    def get_model(self):
        """Loads and caches the Whisper model instance thread-safely."""
        with self._lock:
            if self._model is None:
                try:
                    import whisper
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info(f"Loading Whisper model '{self.model_name}' on {device}...")
                    self._model = whisper.load_model(self.model_name, device=device)
                except Exception as e:
                    logger.error(f"Failed to load Whisper model: {e}")
                    raise RuntimeError(f"Could not load Whisper model '{self.model_name}': {e}")
            return self._model

    def set_model(self, model_name: str) -> str:
        """Switches the Whisper model size and invalidates cached instance."""
        norm = model_name.lower().strip()
        if norm not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported Whisper model '{model_name}'. Choose from: {', '.join(self.SUPPORTED_MODELS)}")
        with self._lock:
            if norm != self.model_name:
                self.model_name = norm
                self._model = None
        return self.model_name

    def set_language(self, lang: str) -> str:
        """Sets transcription language code (e.g., 'en', 'es', 'fr') or 'auto'."""
        norm = lang.lower().strip()
        self.language = "auto" if norm in ("auto", "none", "detect", "") else norm
        return self.language

    def record_audio(self, duration_seconds: float = 6.0, sample_rate: int = 16000) -> Optional[Any]:
        """Captures microphone audio via sounddevice as a mono float32 numpy array."""
        try:
            import sounddevice as sd
            import numpy as np

            # Query default input device to verify microphone availability
            try:
                dev_info = sd.query_devices(kind="input")
                if not dev_info:
                    raise RuntimeError("No audio input device detected.")
            except Exception as dev_err:
                raise RuntimeError(f"Microphone access error: {dev_err}")

            total_frames = int(duration_seconds * sample_rate)
            recording = sd.rec(total_frames, samplerate=sample_rate, channels=1, dtype="float32")
            sd.wait()
            # Flatten to 1D float32 array
            return recording.flatten()
        except Exception as e:
            logger.error(f"Microphone recording failed: {e}")
            raise RuntimeError(f"Microphone capture error: {e}")

    def transcribe_audio(self, audio_data: Any) -> Tuple[str, str]:
        """Transcribes PCM float32 audio data into text using Whisper."""
        try:
            import numpy as np
            import torch
            model = self.get_model()

            # Ensure 1D float32
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data, dtype=np.float32)
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            lang_param = None if self.language == "auto" else self.language
            use_fp16 = torch.cuda.is_available() and getattr(model, "device", "cpu") != "cpu"

            result = model.transcribe(
                audio_data,
                language=lang_param,
                fp16=use_fp16,
                temperature=0.0
            )

            text = (result.get("text") or "").strip()
            detected_lang = result.get("language", self.language)
            return text, detected_lang
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise RuntimeError(f"Whisper transcription error: {e}")


class TTSVoiceOutput:
    """Manages multilingual text-to-speech voice generation with non-blocking playback."""

    def __init__(self):
        self.is_enabled: bool = False
        self.speed: int = 180  # words per minute
        self.voice_gender: str = "Female"
        self.voice_name: Optional[str] = self._detect_female_voice()
        self.is_speaking: bool = False
        self._current_process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        self._active_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.backend = self._detect_backend()

    def _detect_female_voice(self) -> Optional[str]:
        """Detects and returns the best available female TTS voice ID."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            # 1. Search for known female voice names (Zira, Hazel, Catherine, etc.)
            for v in voices:
                name = (v.name or "").lower()
                if any(k in name for k in ("zira", "hazel", "catherine", "susan", "eva", "female")):
                    return v.id
            # 2. Check gender property if present
            for v in voices:
                g = str(getattr(v, "gender", "")).lower()
                if "female" in g or g == "2":
                    return v.id
            # 3. Second voice on Windows is typically Microsoft Zira Desktop
            if len(voices) > 1:
                return voices[1].id
            elif voices:
                return voices[0].id
        except Exception:
            pass
        return None

    def set_gender(self, gender: str) -> str:
        """Sets voice gender to Female or Male."""
        norm = gender.lower().strip()
        if norm in ("female", "f", "woman", "girl"):
            self.voice_gender = "Female"
            self.voice_name = self._detect_female_voice()
        elif norm in ("male", "m", "man", "boy"):
            self.voice_gender = "Male"
            try:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty("voices")
                for v in voices:
                    name = (v.name or "").lower()
                    if any(k in name for k in ("david", "george", "male")):
                        self.voice_name = v.id
                        break
            except Exception:
                pass
        return self.voice_gender

    def _detect_backend(self) -> str:
        """Selects highest-priority available TTS engine."""
        # 1. Chatterbox Multilingual check
        try:
            import chatterbox  # type: ignore
            return "chatterbox"
        except ImportError:
            pass

        # 2. Piper check
        if shutil.which("piper") or shutil.which("piper.exe"):
            return "piper"

        # 3. pyttsx3 check
        try:
            import pyttsx3
            return "pyttsx3"
        except ImportError:
            pass

        # 4. Windows SAPI5 PowerShell fallback
        if sys.platform == "win32":
            return "windows_sapi5"

        return "none"

    def set_speed(self, speed_wpm: int) -> int:
        """Sets speaking speed rate (wpm clamped between 80 and 320)."""
        self.speed = max(80, min(320, int(speed_wpm)))
        return self.speed

    def stop(self):
        """Immediately interrupts active speech playback."""
        self._stop_event.set()
        self.is_speaking = False
        if self._current_process is not None:
            try:
                self._current_process.terminate()
                self._current_process.kill()
            except Exception:
                pass
            self._current_process = None

    def speak(self, text: str, non_blocking: bool = True):
        """Synthesizes text into spoken audio in a separate thread without blocking CLI."""
        if not text:
            return

        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return

        self._stop_event.clear()

        def _worker():
            try:
                if self.backend == "chatterbox":
                    self._speak_chatterbox(clean_text)
                elif self.backend == "piper":
                    self._speak_piper(clean_text)
                elif self.backend == "pyttsx3":
                    self._speak_pyttsx3(clean_text)
                elif self.backend == "windows_sapi5":
                    self._speak_sapi5(clean_text)
                else:
                    logger.warning("No TTS backend available for speech output.")
            except Exception as e:
                logger.error(f"TTS synthesis error: {e}")

        if non_blocking:
            with self._lock:
                self._active_thread = threading.Thread(target=_worker, name="july-tts-playback", daemon=True)
                self._active_thread.start()
        else:
            _worker()

    def _speak_pyttsx3(self, text: str):
        """Native Windows / Cross-Platform pyttsx3 speech synthesis."""
        if self._stop_event.is_set():
            return
        try:
            self.is_speaking = True
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self.speed)
            if self.voice_name:
                engine.setProperty("voice", self.voice_name)
            
            # Check stop event before starting
            if self._stop_event.is_set():
                return

            engine.say(text)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
        except Exception:
            # Fallback to SAPI5 if pyttsx3 fails COM initialization
            if sys.platform == "win32":
                self._speak_sapi5(text)
        finally:
            self.is_speaking = False

    def _speak_sapi5(self, text: str):
        """Windows SAPI5 speech synthesis via PowerShell."""
        if self._stop_event.is_set():
            return
        clean = text.replace("'", "''").replace('"', '""').replace("\n", " ")
        # Convert WPM to SAPI5 Rate (-10 to +10)
        # default 180 wpm ~ Rate 1
        rate = max(-10, min(10, int((self.speed - 180) / 15)))
        voice_hint = "try { $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female) } catch { try { $s.SelectVoice('Microsoft Zira Desktop') } catch {} }; " if self.voice_gender.lower() == "female" else ""
        ps_cmd = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"{voice_hint}"
            f"$s.Rate = {rate}; "
            f"$s.Speak('{clean}'); "
            f"$s.Dispose()"
        )
        try:
            self.is_speaking = True
            p = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self._current_process = p
            while p.poll() is None:
                if self._stop_event.is_set():
                    p.terminate()
                    p.kill()
                    break
                time.sleep(0.02)
        except Exception:
            pass
        finally:
            self.is_speaking = False
            self._current_process = None

    def _speak_piper(self, text: str):
        """Lightweight neural TTS fallback via Piper executable if available."""
        if self._stop_event.is_set():
            return
        try:
            cmd = ["piper", "--output-raw"]
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = p.communicate(input=text.encode("utf-8"), timeout=20)
            if stdout:
                import sounddevice as sd
                import numpy as np
                audio = np.frombuffer(stdout, dtype=np.int16).astype(np.float32) / 32768.0
                sd.play(audio, samplerate=22050)
                sd.wait()
        except Exception:
            self._speak_pyttsx3(text)

    def _speak_chatterbox(self, text: str):
        """Chatterbox multilingual engine integration."""
        if self._stop_event.is_set():
            return
        try:
            import chatterbox  # type: ignore
            chatterbox.speak(text, speed=self.speed)
        except Exception:
            self._speak_pyttsx3(text)


class CLIHardwareVoiceCoordinator:
    """Unified Voice Subsystem Coordinator for July and Gravity models."""

    _instance: Optional[CLIHardwareVoiceCoordinator] = None

    def __init__(self):
        self.stt = WhisperVoiceInput()
        self.tts = TTSVoiceOutput()

    @classmethod
    def get_instance(cls) -> CLIHardwareVoiceCoordinator:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
