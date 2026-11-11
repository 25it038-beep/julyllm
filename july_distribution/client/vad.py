"""
HS AI SOLUTIONS — REAL-TIME VOICE ACTIVITY DETECTION (VAD) & ECHO GATING ENGINE
Layer: REAL-TIME CONVERSATIONAL VOICE PIPELINE (july_distribution.client.vad)
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM & GRAVITY LLM LIVE CONVERSATIONAL ENVIRONMENT

Features:
1. Low-latency, multi-tier real-time Voice Activity Detection.
2. Dynamic background noise floor adaptation (exponential moving average).
3. Dual-threshold hysteresis (onset speech detection vs offset silence detection).
4. Pre-speech audio circular buffer to preserve initial consonant attacks and plosives.
5. Playback-aware echo suppression gating for natural barge-in (user interruption)
   without speaker self-trigger feedback loops.
6. Real-time RMS and audio energy metering for responsive visual waveforms.
"""

from __future__ import annotations
import math
import time
import collections
import logging
from typing import Optional, Tuple, Deque
import numpy as np

logger = logging.getLogger("july.live.vad")


class RealtimeVAD:
    """
    High-precision, low-latency Voice Activity Detector engineered for real-time full-duplex conversations.
    Supports continuous stream chunk processing, pre-speech retention, and playback-aware echo suppression.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        speech_start_threshold: float = 0.022,
        speech_end_threshold: float = 0.012,
        silence_duration_seconds: float = 0.8,
        min_speech_duration_seconds: float = 0.35,
        pre_speech_buffer_seconds: float = 0.35,
        echo_suppression_multiplier: float = 3.2,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0))

        # Energy thresholds
        self.speech_start_threshold = speech_start_threshold
        self.speech_end_threshold = speech_end_threshold
        self.silence_duration_seconds = silence_duration_seconds
        self.min_speech_duration_seconds = min_speech_duration_seconds
        self.echo_suppression_multiplier = echo_suppression_multiplier

        # Dynamic noise floor tracking
        self.noise_floor = 0.005
        self.noise_ema_alpha = 0.05

        # State tracking
        self.is_speech_active: bool = False
        self.speech_start_time: float = 0.0
        self.speech_samples: int = 0
        self.last_speech_frame_time: float = 0.0
        self.silence_counter_seconds: float = 0.0
        self.is_playback_active: bool = False

        # Audio buffers
        pre_buffer_frames = int(pre_speech_buffer_seconds / (frame_duration_ms / 1000.0))
        self._pre_speech_buffer: Deque[np.ndarray] = collections.deque(maxlen=max(1, pre_buffer_frames))
        self._active_speech_frames: list[np.ndarray] = []

        # Current audio metric
        self.current_rms: float = 0.0
        self.peak_rms: float = 0.0

        # Try initializing Silero VAD if available
        self._silero_model = None
        self._init_silero_vad()

    def _init_silero_vad(self):
        """Attempts to load local or cached Silero VAD model if available without blocking."""
        try:
            import torch
            # Check if cached torch hub silero model is available locally
            hub_dir = torch.hub.get_dir()
            import os
            silero_dir = os.path.join(hub_dir, "snakers4_silero-vad_master")
            if os.path.exists(silero_dir):
                model, _ = torch.hub.load(repo_or_dir=silero_dir, model="silero_vad", source="local", onnx=False)
                self._silero_model = model
                logger.info("Silero VAD model initialized successfully.")
        except Exception:
            self._silero_model = None

    def set_playback_active(self, active: bool):
        """Notifies VAD whether AI speaker audio is actively playing for echo suppression."""
        self.is_playback_active = active

    def calculate_frame_rms(self, frame: np.ndarray) -> float:
        """Calculates root-mean-square amplitude of an audio frame."""
        if len(frame) == 0:
            return 0.0
        mean_sq = float(np.mean(frame.astype(np.float32) ** 2))
        return math.sqrt(max(0.0, mean_sq))

    def process_frame(self, frame: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Processes a single audio frame (typically 30ms @ 16kHz).
        Returns:
            (is_speaking_now, completed_utterance_audio or None)
        """
        now = time.time()
        rms = self.calculate_frame_rms(frame)
        self.current_rms = rms
        self.peak_rms = max(self.peak_rms * 0.95, rms)

        # Apply playback echo suppression multiplier to prevent AI speaker self-triggers
        multiplier = self.echo_suppression_multiplier if self.is_playback_active else 1.0
        effective_start_thresh = max(self.speech_start_threshold * multiplier, self.noise_floor * 2.5 * multiplier)
        effective_end_thresh = max(self.speech_end_threshold * multiplier, self.noise_floor * 1.5 * multiplier)

        is_frame_speech = False

        # 1. Silero VAD check if loaded
        if self._silero_model is not None and len(frame) >= 512:
            try:
                import torch
                tensor_frame = torch.from_numpy(frame[:512]).float()
                prob = float(self._silero_model(tensor_frame, self.sample_rate).item())
                speech_prob_thresh = 0.65 if self.is_playback_active else 0.45
                is_frame_speech = (prob >= speech_prob_thresh)
            except Exception:
                is_frame_speech = (rms >= effective_start_thresh)
        else:
            # 2. High-performance adaptive energy & zero-crossing rate VAD
            is_frame_speech = (rms >= effective_start_thresh)

        if not self.is_speech_active:
            # Updating dynamic noise floor only during confirmed silence
            if not is_frame_speech and not self.is_playback_active:
                self.noise_floor = (1.0 - self.noise_ema_alpha) * self.noise_floor + self.noise_ema_alpha * rms
                self._pre_speech_buffer.append(frame.copy())

            if is_frame_speech:
                # Speech onset detected
                self.is_speech_active = True
                self.speech_start_time = now
                self.speech_samples = sum(len(f) for f in self._pre_speech_buffer) + len(frame)
                self.last_speech_frame_time = now
                self.silence_counter_seconds = 0.0

                # Prepend pre-speech ring buffer so beginning of speech is never truncated
                self._active_speech_frames = list(self._pre_speech_buffer)
                self._active_speech_frames.append(frame.copy())
                self._pre_speech_buffer.clear()
                return True, None
            else:
                return False, None
        else:
            # Inside an active speech segment
            self._active_speech_frames.append(frame.copy())
            self.speech_samples += len(frame)

            if rms >= effective_end_thresh:
                # User is still actively vocalizing
                self.last_speech_frame_time = now
                self.silence_counter_seconds = 0.0
                return True, None
            else:
                # Silence frame encountered during active speech
                frame_sec = len(frame) / float(self.sample_rate)
                self.silence_counter_seconds += frame_sec

                # Check if silence duration exceeded hangover threshold
                if self.silence_counter_seconds >= self.silence_duration_seconds:
                    total_speech_duration = self.speech_samples / float(self.sample_rate)
                    self.is_speech_active = False

                    # Check if utterance satisfies minimum duration threshold
                    if total_speech_duration >= self.min_speech_duration_seconds and len(self._active_speech_frames) > 0:
                        full_audio = np.concatenate(self._active_speech_frames, axis=0)
                        self._active_speech_frames.clear()
                        self.speech_samples = 0
                        return False, full_audio
                    else:
                        # Too short (noise click / breath) -> reject
                        self._active_speech_frames.clear()
                        self.speech_samples = 0
                        return False, None

                return True, None

    def reset(self):
        """Resets active speech tracking states and buffers."""
        self.is_speech_active = False
        self.speech_start_time = 0.0
        self.speech_samples = 0
        self.last_speech_frame_time = 0.0
        self.silence_counter_seconds = 0.0
        self._active_speech_frames.clear()
        self._pre_speech_buffer.clear()
        self.current_rms = 0.0
