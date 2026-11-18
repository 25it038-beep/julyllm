"""
HS AI SOLUTIONS — CONVERSATIONAL VOICE INTELLIGENCE ENGINE (WHISPER STT & HUMAN-LIKE TTS)
Layer: VOICE INTERACTION SUBSYSTEM (july_distribution.client.voice)
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM, MINI-OMNI & GRAVITY LLM MULTI-MODEL CLI ENVIRONMENT

Features:
1. Microphone Audio Capture (sounddevice, 16kHz float32 mono PCM).
2. Whisper STT Integration (Automatic Hardware-Aware Model Sizing: tiny/base/small/medium).
3. Intelligent Conversational Speech Processing:
   - Strips code blocks, citations, emojis, Markdown, tables, and UI borders.
   - Expands abbreviations, technical units, acronyms, and symbols for natural spoken delivery.
4. Context-Aware Expressive Prosody Engine:
   - Modulates pitch, speaking rate, and emphasis based on intent (Question, Greeting, Technical, Serious, Enthusiastic).
   - Inserts natural clause-level and thought-level micro-pauses without robotic monotone.
5. High-Performance Zero-Latency SAPI COM & SSML Voice Engine:
   - In-process Windows SAPI COM (SAPI.SpVoice) with sub-millisecond audio dispatch.
   - Dynamic prosody control (<pitch>, <rate>, <emph>, <silence>).
   - Instant barge-in / speech purge on interruption.
   - Smooth fallback to pyttsx3, Piper, or Chatterbox.
6. Asynchronous, Non-Blocking Streaming Playback.
"""

from __future__ import annotations
import os
import re
import sys
import time
import shutil
import logging
import threading
import queue
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Tuple, List

logger = logging.getLogger("july.voice")


class ConversationalSpeechNormalizer:
    """
    Intelligently converts raw LLM outputs (markdown, formatting, citations, code,
    abbreviations, numbers, and technical symbols) into fluid, conversational spoken text.
    """

    ABBREVIATIONS = [
        (r"\be\.g\.,?\s*", "for example, "),
        (r"\bi\.e\.,?\s*", "that is, "),
        (r"\betc\.\s*", "etcetera. "),
        (r"\bvs\.?\s*", "versus "),
        (r"\bapprox\.?\s*", "approximately "),
        (r"\bwpm\b", "words per minute"),
        (r"\bmin\.\s*", "minimum "),
        (r"\bmax\.\s*", "maximum "),
        (r"\bsec\.\s*", "seconds "),
        (r"\bdept\.\s*", "department "),
        (r"\bfig\.\s*", "figure "),
    ]

    UNITS = [
        (r"(\d+(?:\.\d+)?)\s*[bB](?:illion)?\b", r"\1 billion"),
        (r"(\d+(?:\.\d+)?)\s*[mM](?:illion)?\b", r"\1 million"),
        (r"(\d+(?:\.\d+)?)\s*[kK]\b", r"\1 thousand"),
        (r"(\d+(?:\.\d+)?)\s*kHz\b", r"\1 kilohertz"),
        (r"(\d+(?:\.\d+)?)\s*Hz\b", r"\1 hertz"),
        (r"(\d+(?:\.\d+)?)\s*ms\b", r"\1 milliseconds"),
        (r"(\d+(?:\.\d+)?)\s*GB\b", r"\1 gigabytes"),
        (r"(\d+(?:\.\d+)?)\s*MB\b", r"\1 megabytes"),
        (r"(\d+(?:\.\d+)?)\s*TB\b", r"\1 terabytes"),
        (r"(\d+(?:\.\d+)?)\s*KB\b", r"\1 kilobytes"),
        (r"\b(?:version\s+)?v(\d+\.\d+(?:\.\d+)?)\b", r"version \1"),
        (r"(\d+)%", r"\1 percent"),
        (r"\$(\d+(?:\.\d+)?)", r"\1 dollars"),
        (r"€(\d+(?:\.\d+)?)", r"\1 euros"),
        (r"£(\d+(?:\.\d+)?)", r"\1 pounds"),
    ]

    OPERATORS = [
        (r"\b!=\b|!=", " is not equal to "),
        (r"\b==\b|==", " equals "),
        (r">=", " is greater than or equal to "),
        (r"<=", " is less than or equal to "),
        (r"-->|->|=>", " leads to "),
        (r"\bO\(n\)", "O of n"),
        (r"\bO\(1\)", "O of 1"),
        (r"\bO\(log\s*n\)", "O of log n"),
        (r"\bO\(n\^2\)", "O of n squared"),
    ]

    ACRONYMS = {
        r"\bLLM\b": "L L M",
        r"\bAPI\b": "A P I",
        r"\bCLI\b": "C L I",
        r"\bTTS\b": "T T S",
        r"\bSTT\b": "S T T",
        r"\bVAD\b": "V A D",
        r"\bGPU\b": "G P U",
        r"\bCPU\b": "C P U",
        r"\bRAM\b": "ram",
        r"\bVRAM\b": "V ram",
        r"\bUI\b": "U I",
        r"\bOS\b": "O S",
        r"\bURL\b": "U R L",
        r"\bSDK\b": "S D K",
        r"\bJSON\b": "Jason",
        r"\bSQL\b": "sequel",
        r"\bHTML\b": "H T M L",
        r"\bXML\b": "X M L",
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        if not text:
            return ""

        cleaned = text

        # 1. Remove <think>...</think> reasoning blocks
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE)

        # 2. Code blocks ```...``` -> convert to natural conversational cue
        cleaned = re.sub(r"```[\s\S]*?```", " Here is the code. ", cleaned)

        # 3. Inline code `...`
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

        # 4. Links & URLs
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
        cleaned = re.sub(r"https?://\S+", "link", cleaned)

        # 5. Citations and footnotes: [1], [2, 3], [^1]
        cleaned = re.sub(r"\[\^?[0-9,\s]+\]", "", cleaned)

        # 6. Markdown headers #{1,6} -> ensure sentence terminator and preserve line break
        cleaned = re.sub(r"#{1,6}\s*(.+?)(?:\n+|$)", r"\1.\n", cleaned)

        # 7. Bold and italics
        cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
        cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
        cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)

        # 8. Tables and pipes
        cleaned = re.sub(r"\|[-:\s|]+\|", " ", cleaned)
        cleaned = re.sub(r"\|", " ", cleaned)

        # 9. List bullets and numbers at line start (with optional indentation)
        cleaned = re.sub(r"^\s*[*\-•+]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

        # 10. Technical operators and symbols
        for pat, repl in cls.OPERATORS:
            cleaned = re.sub(pat, repl, cleaned)

        # UI borders, box drawing characters, and emojis
        cleaned = re.sub(r"[│┌└─┐┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬■▶▲▼►◄◆●~]", " ", cleaned)
        cleaned = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff]", "", cleaned)

        # 11. Technical units and scaled numbers
        for pat, repl in cls.UNITS:
            cleaned = re.sub(pat, repl, cleaned)

        # 12. Abbreviations
        for pat, repl in cls.ABBREVIATIONS:
            cleaned = re.sub(pat, repl, cleaned, flags=re.IGNORECASE)

        # 13. Acronyms
        for pat, repl in cls.ACRONYMS.items():
            cleaned = re.sub(pat, repl, cleaned)

        # 14. Normalize whitespace and clean up double punctuation
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s+([.,?!])", r"\1", cleaned)
        cleaned = re.sub(r"([.,?!]){2,}", r"\1", cleaned)

        return cleaned.strip()


def clean_text_for_speech(text: str) -> str:
    """Strips markdown, code formatting, citations, and converts text for clean natural speech."""
    return ConversationalSpeechNormalizer.normalize(text)


class ConversationalProsodyEngine:
    """
    Analyzes sentence intent, emotion, and punctuation to generate
    natural, expressive SAPI XML and SSML prosody markup.
    """

    GREETING_PATTERNS = [
        r"\b(?:hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|welcome|greetings)\b"
    ]
    SERIOUS_PATTERNS = [
        r"\b(?:warning|caution|error|critical|fatal|failed|danger|careful|crucial|security|vulnerability|alert)\b"
    ]
    ENTHUSIASTIC_PATTERNS = [
        r"\b(?:awesome|great|excellent|fascinating|amazing|wonderful|fantastic|brilliant|delighted|perfect|congratulations)\b"
    ]
    CONFIRMATION_PATTERNS = [
        r"^(?:sure|understood|got it|alright|no problem|certainly|of course|absolutely)\b"
    ]
    TECHNICAL_PATTERNS = [
        r"\b(?:algorithm|architecture|computational|neural|gradient|tensor|vector|matrix|inference|optimization|probability|theorem|asynchronous|latency|bandwidth)\b"
    ]

    def __init__(self):
        self._sentence_counter = 0

    def analyze_context(self, text: str) -> str:
        """Determines the contextual emotion/function of the sentence."""
        norm = text.lower().strip()
        if any(re.search(p, norm) for p in self.CONFIRMATION_PATTERNS):
            return "confirmation"
        if any(re.search(p, norm) for p in self.GREETING_PATTERNS):
            return "greeting"
        if any(re.search(p, norm) for p in self.SERIOUS_PATTERNS):
            return "serious"
        if any(re.search(p, norm) for p in self.ENTHUSIASTIC_PATTERNS) or norm.endswith("!"):
            return "enthusiastic"
        if norm.endswith("?") or re.search(r"^(?:how|what|why|when|where|who|which|could|would|can|is|are|do|does|did)\b", norm):
            return "question"
        if any(re.search(p, norm) for p in self.TECHNICAL_PATTERNS):
            return "technical"
        return "explanation"

    def build_sapi_xml(self, text: str, base_wpm: int = 180) -> str:
        """Constructs expressive SAPI XML with dynamic pitch, rate, pauses, and emphasis."""
        if not text:
            return ""

        context = self.analyze_context(text)
        self._sentence_counter += 1

        # Base rate conversion (-10 to +10, 180 wpm ~ 0 or 1)
        base_rate = max(-10, min(10, int((base_wpm - 180) / 15)))

        pitch_offset = 0
        rate_offset = 0

        if context == "greeting":
            pitch_offset = 1
            rate_offset = 1
        elif context == "enthusiastic":
            pitch_offset = 1
            rate_offset = 1
        elif context == "serious":
            pitch_offset = -1
            rate_offset = -1
        elif context == "question":
            pitch_offset = 1
            rate_offset = 0
        elif context == "confirmation":
            pitch_offset = 1
            rate_offset = 2
        elif context == "technical":
            pitch_offset = 0
            rate_offset = 0
        else: # explanation - conversational variation across sentences
            cycle = self._sentence_counter % 4
            if cycle == 1:
                pitch_offset = 1
                rate_offset = 0
            elif cycle == 2:
                pitch_offset = 0
                rate_offset = 1
            elif cycle == 3:
                pitch_offset = -1
                rate_offset = 0
            else:
                pitch_offset = 0
                rate_offset = 0

        target_rate = max(-10, min(10, base_rate + rate_offset))
        target_pitch = max(-10, min(10, pitch_offset))

        body = text

        # Escape XML entities in body
        body = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', '&quot;')

        # Natural micro-pauses for commas, semicolons, colons, dashes
        body = re.sub(r",\s*", ', <silence msec="90"/> ', body)
        body = re.sub(r";\s*", '; <silence msec="140"/> ', body)
        body = re.sub(r":\s*", ': <silence msec="120"/> ', body)
        body = re.sub(r"—\s*|--\s*", ' <silence msec="110"/> ', body)

        # For questions: raise pitch on the final words before question mark for natural inflection
        if context == "question" and body.endswith("?"):
            q_match = re.search(r"(\s+[\w\s]{2,20}\?)$", body)
            if q_match:
                end_segment = q_match.group(1)
                lifted = f'<pitch middle="+2">{end_segment}</pitch>'
                body = body[:q_match.start()] + lifted

        xml = f'<pitch middle="{target_pitch:+d}"><rate speed="{target_rate:+d}">{body}</rate></pitch><silence msec="220"/>'
        return xml


class SapiComVoiceSession:
    """
    Dedicated in-process Windows SAPI COM worker thread.
    Achieves sub-millisecond audio synthesis without spawning external processes,
    and supports instantaneous hardware-level barge-in interruption.
    """

    def __init__(self, gender: str = "Female", speed_wpm: int = 180):
        self.gender = gender
        self.speed = speed_wpm
        self.is_speaking = False
        self._cmd_queue: queue.Queue = queue.Queue()
        self._voice_name: Optional[str] = None
        self._active = False
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._run, name="july-sapi-worker", daemon=True)
        self._worker_thread.start()

    def _select_voice(self, v, gender: str):
        try:
            voices = v.GetVoices()
            target = "zira" if gender.lower() == "female" else "david"
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription()
                if target in desc.lower():
                    v.Voice = voices.Item(i)
                    self._voice_name = desc
                    return
            if voices.Count > 0:
                v.Voice = voices.Item(0)
                self._voice_name = v.Voice.GetDescription()
        except Exception as e:
            logger.warning(f"SAPI voice selection notice: {e}")

    def _run(self):
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
        except Exception as e:
            logger.warning(f"In-process SAPI COM not available: {e}")
            return

        self._active = True
        try:
            v = win32com.client.Dispatch("SAPI.SpVoice")
            self._select_voice(v, self.gender)
            rate = max(-10, min(10, int((self.speed - 180) / 15)))
            v.Rate = rate

            while True:
                item = self._cmd_queue.get()
                if item is None:
                    break
                cmd, arg, done_evt = item

                if cmd == "set_gender":
                    self.gender = arg
                    self._select_voice(v, self.gender)
                    if done_evt: done_evt.set()

                elif cmd == "set_speed":
                    self.speed = arg
                    rate = max(-10, min(10, int((self.speed - 180) / 15)))
                    v.Rate = rate
                    if done_evt: done_evt.set()

                elif cmd == "stop":
                    self.is_speaking = False
                    # SVSFPurgeBeforeSpeak = 2, SVSFlagsAsync = 1
                    try:
                        v.Speak("", 2 | 1)
                    except Exception:
                        pass
                    if done_evt: done_evt.set()

                elif cmd == "speak_xml":
                    xml_text, stop_evt = arg
                    self.is_speaking = True
                    try:
                        # SVSFIsXML = 8, SVSFlagsAsync = 1
                        v.Speak(xml_text, 8 | 1)
                        while True:
                            if stop_evt and stop_evt.is_set():
                                v.Speak("", 2 | 1)
                                break
                            status = v.Status
                            if status.RunningState in (0, 1): # 0 = uninit/idle, 1 = SRSEDone
                                break
                            time.sleep(0.01)
                    except Exception as spk_err:
                        logger.error(f"SAPI speak XML error: {spk_err}")
                    finally:
                        self.is_speaking = False
                        if done_evt: done_evt.set()

        except Exception as e:
            logger.error(f"SAPI COM thread error: {e}")
        finally:
            self._active = False
            v = None
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def speak(self, xml_text: str, stop_event: Optional[threading.Event] = None, block: bool = True):
        if not self._active:
            return False
        evt = threading.Event() if block else None
        self._cmd_queue.put(("speak_xml", (xml_text, stop_event), evt))
        if block and evt:
            evt.wait()
        return True

    def stop(self):
        # Purge pending speech queue
        while not self._cmd_queue.empty():
            try:
                item = self._cmd_queue.get_nowait()
                if item and item[2]:
                    item[2].set()
            except Exception:
                break
        evt = threading.Event()
        self._cmd_queue.put(("stop", None, evt))
        evt.wait(timeout=0.2)

    def set_gender(self, gender: str):
        evt = threading.Event()
        self._cmd_queue.put(("set_gender", gender, evt))
        evt.wait(timeout=0.2)

    def set_speed(self, speed_wpm: int):
        evt = threading.Event()
        self._cmd_queue.put(("set_speed", speed_wpm, evt))
        evt.wait(timeout=0.2)

    def is_available(self) -> bool:
        return self._active


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
                temperature=0.0,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                without_timestamps=True,
            )

            text = (result.get("text") or "").strip()
            detected_lang = result.get("language", self.language)
            return text, detected_lang
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise RuntimeError(f"Whisper transcription error: {e}")


class TTSVoiceOutput:
    """
    Manages natural, conversational text-to-speech voice generation
    with prosodic modulation, sentence-aware rhythm, and non-blocking playback.
    """

    def __init__(self):
        self.is_enabled: bool = False
        self.speed: int = 200  # Rapid conversational rate (approx. 200 words per minute)
        self.voice_gender: str = "Female"
        self.voice_name: Optional[str] = self._detect_female_voice()
        self.is_speaking: bool = False
        self._current_process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        self._active_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.backend = self._detect_backend()
        self.prosody = ConversationalProsodyEngine()

        # In-process SAPI COM session for instant low-latency speech on Windows
        self._sapi_session: Optional[SapiComVoiceSession] = None
        if sys.platform == "win32":
            try:
                self._sapi_session = SapiComVoiceSession(gender=self.voice_gender, speed_wpm=self.speed)
                time.sleep(0.05)
            except Exception:
                self._sapi_session = None

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

        if self._sapi_session and self._sapi_session.is_available():
            self._sapi_session.set_gender(self.voice_gender)

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

        # 3. pyttsx3 check (Primary cross-platform / Windows COM adapter)
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
        if self._sapi_session and self._sapi_session.is_available():
            self._sapi_session.set_speed(self.speed)
        return self.speed

    def stop(self):
        """Immediately interrupts active speech playback."""
        self._stop_event.set()
        self.is_speaking = False

        if self._sapi_session and self._sapi_session.is_available():
            self._sapi_session.stop()

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
                # 1. Primary in-process SAPI COM session on Windows with Prosody XML
                if self._sapi_session and self._sapi_session.is_available():
                    self.is_speaking = True
                    xml = self.prosody.build_sapi_xml(clean_text, base_wpm=self.speed)
                    self._sapi_session.speak(xml, stop_event=self._stop_event, block=True)
                    self.is_speaking = False
                    return

                # 2. Secondary Engine Fallbacks
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
            finally:
                self.is_speaking = False

        if non_blocking:
            with self._lock:
                self._active_thread = threading.Thread(target=_worker, name="july-tts-playback", daemon=True)
                self._active_thread.start()
        else:
            _worker()

    def _speak_pyttsx3(self, text: str):
        """Native Windows / Cross-Platform pyttsx3 speech synthesis with conversational rate."""
        if self._stop_event.is_set():
            return
        try:
            self.is_speaking = True
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self.speed)
            if self.voice_name:
                engine.setProperty("voice", self.voice_name)

            if self._stop_event.is_set():
                return

            engine.say(text)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
        except Exception:
            if sys.platform == "win32":
                self._speak_sapi5(text)
        finally:
            self.is_speaking = False

    def _speak_sapi5(self, text: str):
        """Windows SAPI5 speech synthesis via PowerShell with prosody markup."""
        if self._stop_event.is_set():
            return
        clean = text.replace("'", "''").replace('"', '""').replace("\n", " ")
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
    """Unified Voice Subsystem Coordinator for July, Mini-Omni, and Gravity models."""

    _instance: Optional[CLIHardwareVoiceCoordinator] = None

    def __init__(self):
        self.stt = WhisperVoiceInput()
        self.tts = TTSVoiceOutput()

    @classmethod
    def get_instance(cls) -> CLIHardwareVoiceCoordinator:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
