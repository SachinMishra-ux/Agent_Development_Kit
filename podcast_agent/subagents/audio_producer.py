"""Audio Producer Subagent (audio_producer_agent).

This subagent is solely responsible for technical audio production:
- Receives dialogue script turns and episode title from podcast_agent.
- Invokes the generate_podcast_audio tool to synthesize multi-speaker neural audio.
- Emits the resulting MP3 as an ADK Session Artifact for in-browser playback.
- Reports generation summary and transfers control back to podcast_agent.
- Employs static_instruction for Gemini Context Cache alignment.
"""

from google.adk import Agent
from google.adk.tools import FunctionTool
from google.genai import types

from podcast_agent.prompt import (
    AUDIO_PRODUCER_INSTRUCTION,
    PODCAST_STUDIO_STATIC_INSTRUCTION,
)
from podcast_agent.tools import generate_podcast_audio

# ── Pattern 2: Native Tool Confirmation Gate ──────────────────────────────────
# By wrapping generate_podcast_audio with FunctionTool(..., require_confirmation=True),
# Google ADK intercepts the function call before running. In the ADK Web UI, this
# displays an interactive Confirmation Card with a checkbox and "Submit" button,
# allowing the user to explicitly approve or reject tool execution directly in the UI.
generate_podcast_audio_tool = FunctionTool(
    func=generate_podcast_audio,
    require_confirmation=True,
)

# ── Audio Producer Agent Definition ───────────────────────────────────────────
# Equipped ONLY with generate_podcast_audio_tool.
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
    # Sole tool: Neural TTS synthesis with native HITL tool confirmation gate
    tools=[generate_podcast_audio_tool],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
    ),
)
