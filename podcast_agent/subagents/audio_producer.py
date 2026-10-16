"""Audio Producer Subagent (audio_producer_agent).

This subagent is solely responsible for technical audio production:
- Receives dialogue script turns and episode title from podcast_agent.
- Invokes the generate_podcast_audio tool to synthesize multi-speaker neural audio.
- Emits the resulting MP3 as an ADK Session Artifact for in-browser playback.
- Reports generation summary and transfers control back to podcast_agent.
- Employs static_instruction for Gemini Context Cache alignment.
"""

from google.adk import Agent
from google.genai import types

from podcast_agent.prompt import (
    AUDIO_PRODUCER_INSTRUCTION,
    PODCAST_STUDIO_STATIC_INSTRUCTION,
)
from podcast_agent.tools import generate_podcast_audio

# ── Audio Producer Agent Definition ───────────────────────────────────────────
# Equipped ONLY with generate_podcast_audio tool.
audio_producer_agent = Agent(
    name="audio_producer_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Synthesizes multi-speaker MP3 podcast audio from dialogue scripts using neural "
        "voices and saves the episode as an ADK Session Artifact."
    ),
    # Shared static instruction maintains context cache prefix alignment across handoffs
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=AUDIO_PRODUCER_INSTRUCTION,
    # Sole tool: Neural TTS synthesis and artifact saving
    tools=[generate_podcast_audio],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
    ),
)
