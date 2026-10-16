"""Investigative Researcher Subagent (research_agent).

This subagent is solely responsible for factual grounding:
- Accepts a podcast topic and optional document excerpts from the coordinator.
- Uses the built-in google_search tool to look up live statistics, recent news,
  and real-world case studies.
- Synthesizes findings into a structured briefing and transfers control back to podcast_agent.
- Employs static_instruction for Gemini Context Cache alignment.
"""

from google.adk import Agent
from google.adk.tools import google_search
from google.genai import types

from podcast_agent.prompt import (
    PODCAST_STUDIO_STATIC_INSTRUCTION,
    RESEARCHER_INSTRUCTION,
)

# ── Researcher Agent Definition ───────────────────────────────────────────────
# Equipped ONLY with google_search. It does not touch document reading or audio
# synthesis, ensuring clear separation of responsibilities.
research_agent = Agent(
    name="research_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Researches podcast topics using Google Search to provide factual briefing, "
        "live statistics, and debate angles."
    ),
    # Shared static instruction maintains context cache prefix alignment across handoffs
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=RESEARCHER_INSTRUCTION,
    # Sole tool: Google Search grounding
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        tool_config=types.ToolConfig(
            include_server_side_tool_invocations=True
        ),
    ),
)
