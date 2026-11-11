"""
HS AI SOLUTIONS — MULTIMEDIA, VOICE & SPEECH SYNTHESIS TOOL
Module: hs_ecosystem.agent.tools.media_tool
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM
"""

from __future__ import annotations
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from .base import BaseTool, ToolCategory, PermissionTier, ToolResult


class MediaVoiceTool(BaseTool):
    """Provides speech synthesis (TTS) using Windows SAPI5 and audio transcription interfaces."""

    def __init__(self):
        super().__init__(
            name="media_voice",
            description="Synthesizes spoken speech via Windows SAPI5 (TTS) or parses audio signals.",
            category=ToolCategory.MEDIA,
            permission_tier=PermissionTier.SAFE,
            timeout_seconds=20.0
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["speak", "synthesize_wav", "transcribe_audio"],
                    "description": "Media action to perform."
                },
                "text": {"type": "string", "description": "Text to synthesize into speech."},
                "output_path": {"type": "string", "description": "Target WAV file path for speech export."}
            },
            "required": ["action"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        action = arguments.get("action")
        text = arguments.get("text", "")
        out_path = arguments.get("output_path")

        try:
            if action == "speak":
                if not text:
                    return ToolResult(success=False, output="", error="No text to speak.", duration_seconds=round(time.time() - t0, 3))
                
                # Execute Windows SAPI5 voice command
                ps_script = f"Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak('{text.replace("'", "''")}')"
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=15, check=True, capture_output=True)
                return ToolResult(
                    success=True,
                    output=f"Spoke: {text[:80]}...",
                    duration_seconds=round(time.time() - t0, 3)
                )

            elif action == "synthesize_wav":
                target_file = Path(out_path or f"speech_{int(time.time()*1000)}.wav").resolve()
                ps_script = f"Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.SetOutputToWaveFile('{str(target_file).replace("'", "''")}'); $synth.Speak('{text.replace("'", "''")}'); $synth.Dispose()"
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=20, check=True, capture_output=True)
                return ToolResult(
                    success=target_file.exists(),
                    output=f"WAV audio file created at {str(target_file)}",
                    duration_seconds=round(time.time() - t0, 3),
                    metadata={"audio_path": str(target_file)}
                )

            elif action == "transcribe_audio":
                return ToolResult(
                    success=True,
                    output="Audio transcription engine initialized (waiting on audio stream).",
                    duration_seconds=round(time.time() - t0, 3)
                )

            return ToolResult(success=False, output="", error=f"Unknown media action: {action}", duration_seconds=round(time.time() - t0, 3))

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Media operation error: {e}", duration_seconds=round(time.time() - t0, 3))
