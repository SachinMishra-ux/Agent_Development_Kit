"""Podcast Scriptwriter Subagent (scriptwriter_agent).

This subagent is solely responsible for writing organic spoken dialogue:
- Takes the research brief, document notes, and speaker count (2 or 3 speakers) from coordinator.
- Writes authentic conversational dialogue with contractions, interruptions, and natural pacing.
- Supports 2 or 3 distinct personas:
  * 2 Speakers: Alex (Host) & Morgan (Expert)
  * 3 Speakers: Alex (Host), Morgan (Expert) & Taylor (Skeptic)
- Has NO external tools (pure LLM creative generation) to eliminate tool distraction.
- Delivers the dialogue turns and transfers control back to podcast_agent.
- Employs static_instruction for Gemini Context Cache alignment.
"""

from google.adk import Agent
from google.genai import types

from podcast_agent.prompt import (
    PODCAST_STUDIO_STATIC_INSTRUCTION,
    SCRIPTWRITER_INSTRUCTION,
)

# ── Scriptwriter Agent Definition ─────────────────────────────────────────────
# Pure dialogue creation agent. Once finished, calls transfer_to_agent("podcast_agent")
# to return the script turns to the producer.
scriptwriter_agent = Agent(
    name="scriptwriter_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Writes natural, engaging multi-speaker podcast dialogue scripts for 2 or 3 "
        "distinct personas based on research briefs."
    ),
    # Shared static instruction maintains context cache prefix alignment across handoffs
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=SCRIPTWRITER_INSTRUCTION,
    # No tools needed: dedicated purely to creative dialogue scripting
    tools=[],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
    ),
)
