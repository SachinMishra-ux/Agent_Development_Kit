"""Neural Multi-Speaker Audio Generation Tool (generate_podcast_audio).

This module handles the synthesis of multi-speaker dialogue scripts into master MP3 files:
1. Voice Casting: Maps speaker names (Alex, Morgan, Taylor) to Microsoft Neural TTS voices.
2. Async Speech Synthesis: Generates per-turn MP3 audio snippets via edge-tts WebSockets.
3. Binary Audio Stitching: Concatenates independent MP3 frames into a single continuous track.
4. ADK Session Artifacts: Saves the MP3 to ADK's Artifact Service, triggering in-browser playback
   in the ADK Web UI ('Artifacts' tab) without requiring local disk access.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Union

import edge_tts
from google.genai import types

from google.adk.tools.tool_context import ToolContext
from podcast_agent.schemas import DialogueTurn, PodcastScript

# ── 1. Voice Mapping Configuration ───────────────────────────────────────────
# Defines distinct, high-quality Microsoft Neural TTS voices for podcast personas:
# - Alex: Energetic, friendly American male host
# - Morgan: Warm, knowledgeable American female expert
# - Taylor: Expressive, thoughtful British male skeptic / 3rd guest
DEFAULT_SPEAKER_VOICES: dict[str, str] = {
    "alex": "en-US-GuyNeural",
    "morgan": "en-US-JennyNeural",
    "taylor": "en-GB-RyanNeural",
}

# Dynamic fallback pool used if user defines arbitrary/custom speaker names
FALLBACK_VOICE_POOL: list[str] = [
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-GB-RyanNeural",
    "en-US-AriaNeural",
    "en-US-ChristopherNeural",
    "en-AU-NatashaNeural",
]


# ── 2. Helper Functions ───────────────────────────────────────────────────────

def _resolve_voice(speaker_name: str, assigned_voices: dict[str, str]) -> str:
    """Resolves or assigns a consistent neural voice for a given speaker persona."""
    cleaned = speaker_name.strip().lower()
    if cleaned in assigned_voices:
        return assigned_voices[cleaned]
    if cleaned in DEFAULT_SPEAKER_VOICES:
        voice = DEFAULT_SPEAKER_VOICES[cleaned]
        assigned_voices[cleaned] = voice
        return voice
    
    # Assign from fallback pool and cache assignment for character continuity
    idx = len(assigned_voices) % len(FALLBACK_VOICE_POOL)
    voice = FALLBACK_VOICE_POOL[idx]
    assigned_voices[cleaned] = voice
    return voice


async def _synthesize_turn(text: str, voice: str, temp_path: str) -> None:
    """Synthesizes a single dialogue turn into a temporary MP3 snippet using edge-tts.
    
    Includes retry logic to ensure robust network communication over WebSockets.
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text=cleaned_text, voice=voice)
            await communicate.save(temp_path)
            return
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(0.8)


# ── 3. Main Audio Generation Tool ─────────────────────────────────────────────

async def generate_podcast_audio(
    script_data: Union[List[Dict[str, str]], str],
    output_filename: str = "podcast_episode.mp3",
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generates a multi-speaker MP3 podcast audio file from dialogue turns using neural TTS voices.
    
    Saves the MP3 locally and emits it as an ADK Session Artifact so it is visible and
    playable directly inside the Google ADK Web UI.

    Args:
        script_data: List of dialogue turns (e.g. [{"speaker": "Alex", "text": "..."}]), or a JSON string.
        output_filename: Name of the final MP3 file (e.g. 'podcast_episode.mp3').
        tool_context: ADK ToolContext injected by runtime for saving artifacts and confirmation.

    Returns:
        Summary message with path to generated .mp3 file and artifact details.
    """
    # ── Block A: Parse & Sanitize Input Script ────────────────────────────────
    # Supports JSON strings, dictionaries with 'turns' key, or raw turn lists.
    if isinstance(script_data, str):
        try:
            turns = json.loads(script_data)
        except Exception:
            # Fallback if raw text in 'Speaker: Text' format was provided
            turns = []
            for line in script_data.strip().split("\n"):
                if ":" in line:
                    spk, txt = line.split(":", 1)
                    turns.append({"speaker": spk.strip(), "text": txt.strip()})
    else:
        turns = script_data

    # Unwrap if nested inside a top-level dict {"turns": [...]}
    if isinstance(turns, dict) and "turns" in turns:
        turns = turns["turns"]

    if not turns:
        return "Error: Script is empty. Please provide dialogue turns with 'speaker' and 'text'."

    # Normalize and validate turn elements using Pydantic DialogueTurn schema
    sanitized_turns: list[dict[str, str]] = []
    for item in turns:
        try:
            if isinstance(item, DialogueTurn):
                sanitized_turns.append(item.model_dump())
            elif isinstance(item, dict):
                turn_obj = DialogueTurn.model_validate(item)
                sanitized_turns.append(turn_obj.model_dump())
            elif hasattr(item, "model_dump"):
                turn_obj = DialogueTurn.model_validate(item.model_dump())
                sanitized_turns.append(turn_obj.model_dump())
            elif hasattr(item, "dict"):
                turn_obj = DialogueTurn.model_validate(item.dict())
                sanitized_turns.append(turn_obj.model_dump())
        except Exception:
            # Fallback for loose dictionaries if strict validation fails
            if isinstance(item, dict) and "speaker" in item and "text" in item:
                sanitized_turns.append({"speaker": str(item["speaker"]), "text": str(item["text"])})
    turns = sanitized_turns

    # ── Block B: Output Directories & Path Setup ─────────────────────────────
    if not output_filename.endswith(".mp3"):
        output_filename += ".mp3"

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, output_filename)

    # ── Block C: Render Individual Turns via Neural TTS & Stitch Frames ───────
    # Generates a temporary MP3 file for each spoken line and sequentially concatenates
    # binary MP3 frames into the final continuous episode track.
    assigned_voices: dict[str, str] = {}
    temp_files: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, turn in enumerate(turns):
            speaker = turn.get("speaker", "Alex")
            text = turn.get("text", "")
            if not text.strip():
                continue

            voice = _resolve_voice(speaker, assigned_voices)
            clip_path = os.path.join(tmp_dir, f"clip_{i:04d}.mp3")
            await _synthesize_turn(text, voice, clip_path)
            temp_files.append(clip_path)

        # Binary frame stitching: MP3 frames are self-contained and concatenate seamlessly
        with open(output_path, "wb") as out_f:
            for clip in temp_files:
                if os.path.exists(clip):
                    with open(clip, "rb") as in_f:
                        out_f.write(in_f.read())

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return "Error: Failed to generate audio file."

    file_size_kb = os.path.getsize(output_path) / 1024
    voice_summary = ", ".join([f"{spk} -> {voice}" for spk, voice in assigned_voices.items()])

    # ── Block D: Save to ADK Session Artifacts (In-Browser UI Playback) ────────
    # Emits an artifact_delta action so ADK Web dev-ui renders the HTML5 audio player
    # inside the 'Artifacts' tab.
    artifact_status = ""
    if tool_context is not None and hasattr(tool_context, "save_artifact"):
        try:
            with open(output_path, "rb") as f:
                mp3_bytes = f.read()

            artifact_part = types.Part.from_bytes(
                data=mp3_bytes,
                mime_type="audio/mp3",
            )
            version = await tool_context.save_artifact(
                filename=output_filename,
                artifact=artifact_part,
            )
            artifact_status = (
                f"\n\n🎧 **Artifact Saved to ADK Web!**\n"
                f"• Artifact Name: `{output_filename}` (Version {version})\n"
                f"• You can now play or download the audio file directly from the **Artifacts** tab in the ADK Web interface!"
            )
        except Exception as e:
            artifact_status = f"\n\n(Note: Artifact saving notice: {str(e)})"

    return (
        f"✅ **Podcast MP3 Audio Generated Successfully!**\n"
        f"• Local File: `{output_path}`\n"
        f"• File Size: {file_size_kb:.1f} KB\n"
        f"• Dialogue Turns: {len(turns)}\n"
        f"• Cast & Voices: {voice_summary}"
        f"{artifact_status}"
    )
