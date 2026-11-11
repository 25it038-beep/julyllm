"""
HS AI SOLUTIONS — REAL-TIME FULL-DUPLEX LIVE CONVERSATIONAL VOICE ENGINE
Layer: REAL-TIME CONVERSATIONAL SUBSYSTEM (july_distribution.client.live_engine)
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & GRAVITY LLM DUAL-MODEL CLI ENVIRONMENT

Features:
1. Continuous Microphone Listening & Real-Time Turn-Taking (Zero Enter Key Required).
2. Streaming Multi-Tier Voice Activity Detection (VAD) with Echo-Aware Gating.
3. Instant Barge-In Interruption: Cuts AI audio and aborts stale LLM token generation immediately.
4. Streaming Sentence Chunker for Sub-Second First-Audio Latency (Streaming TTS).
5. Dynamic Spoken Personality Styles: Natural, Friendly, Professional, Tutor, Companion.
6. Seamless Model Integration: Dual July/Gravity support with uninterrupted background downloads.
7. Real-Time Telemetry & Latency Diagnostics: Detection, Transcription, First-Token, First-Audio.
8. Terminal-Based Reactive Audio Waveform Visualization.
"""

from __future__ import annotations
import os
import re
import sys
import time
import queue
import math
import logging
import threading
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Generator
import numpy as np

from .vad import RealtimeVAD
from .voice import WhisperVoiceInput, TTSVoiceOutput, clean_text_for_speech, CLIHardwareVoiceCoordinator
from .runtime import ClientInferenceRuntime
from .state_manager import DualModelStateManager
from .storage import PermanentModelStorage
from .ui_renderer import render_live_box, make_audio_waveform

logger = logging.getLogger("july.live")


class LiveState(str, Enum):
    LISTENING = "Listening"
    PROCESSING = "Processing"
    THINKING = "Thinking"
    SPEAKING = "Speaking"
    INTERRUPTED = "Interrupted"
    RECONNECTING = "Reconnecting"
    ERROR = "Error"


VOICE_STYLES: Dict[str, Dict[str, str]] = {
    "natural": {
        "title": "Natural",
        "description": "Everyday companion, balanced, concise, conversational",
        "system_directive": (
            "You are in LIVE REAL-TIME VOICE CONVERSATION mode. "
            "Speak naturally, directly, and conversationally, exactly as a human speaks aloud. "
            "Give concise initial answers (1 to 3 spoken sentences). Do not read long essays. "
            "Never use markdown headers, asterisks, bullet points, numbers, tables, or code blocks. "
            "Avoid introductory filler like 'Certainly!' or 'As an AI'. "
            "Answer the user's intent immediately and invite natural follow-ups."
        ),
    },
    "friendly": {
        "title": "Friendly",
        "description": "Warm, engaging, positive, conversational",
        "system_directive": (
            "You are in LIVE VOICE mode with a FRIENDLY conversational personality. "
            "Speak with warmth, genuine kindness, and conversational energy. "
            "Keep initial responses brief and lively (1 to 3 spoken sentences). "
            "Avoid all markdown, bullets, and lists. Speak like a close, helpful friend."
        ),
    },
    "professional": {
        "title": "Professional",
        "description": "Executive advisor, crisp, precise, polite",
        "system_directive": (
            "You are in LIVE VOICE mode with a PROFESSIONAL executive persona. "
            "Deliver crisp, articulate, high-signal spoken answers without fluff or excessive jargon. "
            "Keep answers concise (1 to 3 sentences). Strictly avoid markdown formatting and lists."
        ),
    },
    "tutor": {
        "title": "Tutor",
        "description": "Pedagogical, clear, patient, step-by-step",
        "system_directive": (
            "You are in LIVE VOICE mode with a TUTOR conversational persona. "
            "Explain concepts with clarity, simple intuitive analogies, and encouraging tone. "
            "Explain one clear idea at a time in 2 to 3 natural sentences, then check for understanding. "
            "Avoid formatting, bullets, or lectures."
        ),
    },
    "companion": {
        "title": "Companion",
        "description": "Thoughtful, attentive, empathetic, supportive",
        "system_directive": (
            "You are in LIVE VOICE mode as a dedicated AI COMPANION. "
            "Listen attentively, validate the user's thoughts, and converse with genuine presence. "
            "Speak conversationally in 1 to 3 natural sentences. Avoid lists and markdown."
        ),
    },
}


class SpeechChunker:
    """Splits streaming LLM tokens into sentence-level chunks for incremental low-latency TTS."""

    def __init__(self, min_words_first_clause: int = 5):
        self.buffer: str = ""
        self.min_words_first_clause = min_words_first_clause
        self.is_first_chunk: bool = True

    def reset(self):
        self.buffer = ""
        self.is_first_chunk = True

    def add_token(self, token: str) -> List[str]:
        self.buffer += token
        ready_chunks = []

        while True:
            # 1. Match complete sentence terminators (. ? ! \n)
            m = re.search(r"([.?!:\n]+)(\s+|$)", self.buffer)
            if m:
                end_pos = m.end()
                raw_chunk = self.buffer[:end_pos].strip()
                self.buffer = self.buffer[end_pos:]
                clean = clean_text_for_speech(raw_chunk)
                if clean:
                    ready_chunks.append(clean)
                    self.is_first_chunk = False
                continue

            # 2. For the first chunk, allow early clause boundary (comma, semicolon) for sub-second TTFA
            if self.is_first_chunk:
                words = self.buffer.split()
                if len(words) >= self.min_words_first_clause:
                    for punct in (",", ";", "—", "-"):
                        p_idx = self.buffer.find(punct)
                        if p_idx != -1 and len(self.buffer[:p_idx].split()) >= self.min_words_first_clause:
                            raw_chunk = self.buffer[:p_idx + 1].strip()
                            self.buffer = self.buffer[p_idx + 1:]
                            clean = clean_text_for_speech(raw_chunk)
                            if clean:
                                ready_chunks.append(clean)
                                self.is_first_chunk = False
                            break
            break

        return ready_chunks

    def finalize(self) -> List[str]:
        rem = clean_text_for_speech(self.buffer.strip())
        self.buffer = ""
        return [rem] if rem else []


class LiveConversationManager:
    """
    Coordinates the full-duplex live conversation loop:
    Microphone -> VAD -> Streaming Whisper -> LLM Inference -> Streaming TTS -> Audio Playback.
    """

    def __init__(
        self,
        runtime: ClientInferenceRuntime,
        active_model: str = "july",
        style: str = "natural",
        vad_silence_duration: float = 0.8,
    ):
        self.runtime = runtime
        self.active_model = active_model.lower().strip()
        self.current_style = style.lower().strip() if style.lower().strip() in VOICE_STYLES else "natural"

        # Voice & Audio Subsystems
        v_coord = CLIHardwareVoiceCoordinator.get_instance()
        self.stt: WhisperVoiceInput = v_coord.stt
        self.tts: TTSVoiceOutput = v_coord.tts

        # Real-time Voice Activity Detector
        self.vad = RealtimeVAD(silence_duration_seconds=vad_silence_duration)

        # Threading & Control Flags
        self.is_running: bool = False
        self.cancel_generation_event = threading.Event()
        self._lock = threading.Lock()

        # State tracking
        self.state: LiveState = LiveState.LISTENING
        self.last_user_prompt: str = ""
        self.last_ai_response: str = ""
        self.recent_history: List[Dict[str, str]] = []

        # Playback Chunk Queue for streaming speech
        self._tts_chunk_queue: queue.Queue[Optional[str]] = queue.Queue()
        self._tts_worker_thread: Optional[threading.Thread] = None
        self._mic_stream = None

        # Diagnostic Latency Telemetry Metrics
        self.metrics: Dict[str, float] = {
            "speech_detection_sec": 0.0,
            "transcription_sec": 0.0,
            "first_token_sec": 0.0,
            "first_audio_sec": 0.0,
            "total_latency_sec": 0.0,
        }

        # Animated audio metering
        self.mic_level: float = 0.0
        self.speaker_level: float = 0.0
        self.waveform_phase: float = 0.0

        # Sentence chunker
        self.chunker = SpeechChunker()

    def set_style(self, style: str) -> str:
        """Configures the live conversational style."""
        norm = style.lower().strip()
        if norm in VOICE_STYLES:
            self.current_style = norm
        return self.current_style

    def switch_model(self, model_id: str) -> str:
        """Switches active reasoning model during live voice session."""
        target = model_id.lower().strip()
        if target not in ("july", "gravity"):
            return self.active_model

        if target == self.active_model:
            return self.active_model

        # Cancel any active generation
        self.interrupt()

        # Check if model downloaded
        p_stor = PermanentModelStorage()
        if not p_stor.is_model_present(target):
            # Trigger background download coordinator
            from .dual_engine import DualModelCoordinator
            coord = DualModelCoordinator(runtime=self.runtime, storage=p_stor)
            coord._launch_background_download(target, auto_activate=False)
            self.last_ai_response = f"Gravity is downloading in the background. I'll stay as July until it's ready."
            self.enqueue_speech(self.last_ai_response)
            return self.active_model

        try:
            self.state = LiveState.THINKING
            f = p_stor.get_model_file(target)
            self.runtime.switch_model(target, f)
            self.active_model = target
            logger.info(f"Switched live model to {target.upper()}")
        except Exception as e:
            logger.error(f"Error switching model in live session: {e}")
            self.state = LiveState.ERROR
            self.last_ai_response = f"Could not switch to {target}: {e}"

        return self.active_model

    def interrupt(self):
        """Natural barge-in: immediately stops speaker output and cancels ongoing LLM token streaming."""
        with self._lock:
            # 1. Halt TTS playback and purge audio queue
            self.tts.stop()
            while not self._tts_chunk_queue.empty():
                try:
                    self._tts_chunk_queue.get_nowait()
                except Exception:
                    break

            # 2. Cancel LLM generation loop
            self.cancel_generation_event.set()
            self.chunker.reset()

            # 3. Notify VAD that speaker playback stopped
            self.vad.set_playback_active(False)
            self.state = LiveState.INTERRUPTED

    def enqueue_speech(self, text: str):
        """Enqueues a clean spoken sentence for immediate non-blocking audio playback."""
        clean = clean_text_for_speech(text)
        if clean:
            self._tts_chunk_queue.put(clean)

    def _tts_playback_loop(self):
        """Dedicated audio playback worker for sequential streaming TTS chunks."""
        while self.is_running:
            try:
                chunk = self._tts_chunk_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if chunk is None:
                break

            if self.cancel_generation_event.is_set():
                continue

            try:
                self.vad.set_playback_active(True)
                self.speaker_level = 0.22
                self.state = LiveState.SPEAKING
                # Non-blocking or blocking speech per chunk
                self.tts.speak(chunk, non_blocking=False)
            except Exception as e:
                logger.error(f"Error speaking chunk: {e}")
            finally:
                self.speaker_level = 0.0
                if self._tts_chunk_queue.empty() and not self.cancel_generation_event.is_set():
                    self.vad.set_playback_active(False)
                    if self.state == LiveState.SPEAKING:
                        self.state = LiveState.LISTENING

    def process_user_utterance(self, audio_data: np.ndarray):
        """Handles a completed user speech utterance through Whisper and LLM inference."""
        t_detect_end = time.time()
        self.state = LiveState.PROCESSING

        # 1. Speech-to-Text Transcription via Whisper
        t_stt_start = time.time()
        try:
            trans_text, detected_lang = self.stt.transcribe_audio(audio_data)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            self.state = LiveState.ERROR
            self.last_ai_response = "Sorry, I had trouble hearing that. Please speak again."
            self.enqueue_speech(self.last_ai_response)
            return

        t_stt_end = time.time()
        self.metrics["transcription_sec"] = max(0.01, round(t_stt_end - t_stt_start, 3))

        trans_clean = trans_text.strip()
        if not trans_clean or len(trans_clean) < 2:
            self.state = LiveState.LISTENING
            return

        self.last_user_prompt = trans_clean
        norm = trans_clean.lower().strip()

        # 2. Voice-activated Commands
        if any(w in norm for w in ("exit live", "stop live", "quit live", "/exit-live", "leave live")):
            self.last_ai_response = "Exiting live mode. Returning to standard chat."
            self.enqueue_speech(self.last_ai_response)
            self.is_running = False
            return

        if "switch to gravity" in norm:
            self.switch_model("gravity")
            self.last_ai_response = "Switched to Gravity reasoning model. How can I help?"
            self.enqueue_speech(self.last_ai_response)
            return

        if "switch to july" in norm:
            self.switch_model("july")
            self.last_ai_response = "Switched to July. Ready to chat!"
            self.enqueue_speech(self.last_ai_response)
            return

        # 3. LLM Streaming Generation Worker
        self.state = LiveState.THINKING
        self.cancel_generation_event.clear()
        self.chunker.reset()

        t_prompt_submit = time.time()
        first_token_received = False
        first_audio_dispatched = False

        # Build style-adapted voice prompt
        style_dir = VOICE_STYLES.get(self.current_style, VOICE_STYLES["natural"])["system_directive"]
        session_id = f"live_session_{self.active_model}"

        # Prepend voice directive to system prompt
        effective_prompt = f"[SYSTEM VOICE INSTRUCTION: {style_dir}]\nUser said aloud: {self.last_user_prompt}"

        full_response_parts: List[str] = []

        try:
            stream = self.runtime.generate_stream(
                prompt=effective_prompt,
                session_id=session_id,
                max_tokens=256
            )

            for token in stream:
                if self.cancel_generation_event.is_set():
                    logger.info("Generation interrupted by user barge-in.")
                    break

                if not first_token_received:
                    first_token_received = True
                    self.metrics["first_token_sec"] = round(time.time() - t_prompt_submit, 3)

                full_response_parts.append(token)
                self.last_ai_response = "".join(full_response_parts)

                # Chunk stream into sentence units
                ready_chunks = self.chunker.add_token(token)
                for c in ready_chunks:
                    if not first_audio_dispatched:
                        first_audio_dispatched = True
                        now = time.time()
                        self.metrics["first_audio_sec"] = round(now - t_prompt_submit, 3)
                        self.metrics["total_latency_sec"] = round(now - t_detect_end, 3)

                    self.enqueue_speech(c)

            # Finalize remaining text in chunker
            if not self.cancel_generation_event.is_set():
                for c in self.chunker.finalize():
                    if not first_audio_dispatched:
                        first_audio_dispatched = True
                        now = time.time()
                        self.metrics["first_audio_sec"] = round(now - t_prompt_submit, 3)
                        self.metrics["total_latency_sec"] = round(now - t_detect_end, 3)
                    self.enqueue_speech(c)

        except Exception as gen_err:
            logger.error(f"Error during streaming generation: {gen_err}")
            self.state = LiveState.ERROR
            self.last_ai_response = f"Inference notice: {gen_err}"

    def start_live_loop(self, on_tick_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Runs the continuous full-duplex conversational voice loop.
        Non-blocking to audio interruptions, streaming from mic through VAD to LLM.
        """
        self.is_running = True
        self.state = LiveState.LISTENING

        # Start background TTS player thread
        self._tts_worker_thread = threading.Thread(
            target=self._tts_playback_loop,
            name="july-live-tts",
            daemon=True
        )
        self._tts_worker_thread.start()

        # Initialize audio input stream with sounddevice
        import sounddevice as sd

        frame_samples = self.vad.frame_size  # e.g. 480 samples @ 16kHz
        audio_stream_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=120)

        def audio_callback(indata, frames, time_info, status):
            if self.is_running:
                # indata shape: (frames, 1), copy as 1D float32
                audio_stream_queue.put(indata[:, 0].copy())

        try:
            self._mic_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                blocksize=frame_samples,
                callback=audio_callback,
            )
            self._mic_stream.start()
            logger.info("Live microphone audio stream opened successfully.")
        except Exception as e:
            logger.error(f"Could not open microphone stream: {e}")
            self.state = LiveState.ERROR
            self.is_running = False
            return

        last_tick_time = time.time()

        try:
            while self.is_running:
                try:
                    frame = audio_stream_queue.get(timeout=0.04)
                except queue.Empty:
                    # Periodic UI tick
                    now = time.time()
                    if now - last_tick_time >= 0.08:
                        self.waveform_phase += 0.35
                        if on_tick_callback:
                            on_tick_callback(self.get_telemetry_snapshot())
                        last_tick_time = now
                    continue

                # Process frame in VAD
                is_speaking_now, completed_audio = self.vad.process_frame(frame)
                self.mic_level = self.vad.current_rms

                # Natural barge-in interruption detection
                if is_speaking_now and self.state == LiveState.SPEAKING:
                    self.interrupt()

                # If user finished speaking, process speech segment
                if completed_audio is not None and len(completed_audio) > 0:
                    self.process_user_utterance(completed_audio)

                # Periodic UI tick
                now = time.time()
                if now - last_tick_time >= 0.08:
                    self.waveform_phase += 0.35
                    if on_tick_callback:
                        on_tick_callback(self.get_telemetry_snapshot())
                    last_tick_time = now

        finally:
            self.stop()

    def stop(self):
        """Safely terminates live conversation loop and releases hardware streams."""
        self.is_running = False
        self.interrupt()

        if self._mic_stream is not None:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None

        if self._tts_worker_thread and self._tts_worker_thread.is_alive():
            self._tts_chunk_queue.put(None)
            self._tts_worker_thread.join(timeout=1.0)

        self.state = LiveState.LISTENING
        logger.info("Live voice conversation manager safely stopped.")

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Returns snapshot of current live voice telemetry for UI rendering."""
        # Active audio level reacts to mic when listening, and speaker when speaking
        level = self.speaker_level if self.state == LiveState.SPEAKING else self.mic_level
        audio_state_desc = "Playing" if self.state == LiveState.SPEAKING else ("Listening" if self.state == LiveState.LISTENING else "Processing")

        return {
            "state": self.state.value,
            "active_model": self.active_model.upper(),
            "style": VOICE_STYLES.get(self.current_style, {}).get("title", "Natural"),
            "voice_gender": self.tts.voice_gender,
            "voice_name": self.tts.voice_name or "Microsoft Zira Desktop",
            "whisper_model": self.stt.model_name,
            "whisper_lang": self.stt.language.upper(),
            "user_prompt": self.last_user_prompt,
            "ai_response": self.last_ai_response,
            "level": level,
            "waveform_phase": self.waveform_phase,
            "metrics": dict(self.metrics),
            "audio_state": audio_state_desc,
        }
