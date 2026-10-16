"""Root Coordinator Agent Definition (podcast_agent).

This module defines the primary entry point for the Podcast Studio system.
The coordinator acts as the Executive Producer:
- Inspects user requests and parses any attached documents (PDF/Word/Text).
- Delegates tasks strictly across three specialized subagents:
  1. research_agent (Web research & live facts via Google Search)
  2. scriptwriter_agent (Multi-speaker spoken dialogue scripting)
  3. audio_producer_agent (Neural multi-speaker MP3 audio synthesis)
- Employs static_instruction for Gemini Context Cache alignment.
"""

from google.adk import Agent
from google.adk.tools import load_artifacts
from google.genai import types

from podcast_agent.prompt import (
    COORDINATOR_INSTRUCTION,
    PODCAST_STUDIO_STATIC_INSTRUCTION,
)
from podcast_agent.subagents import (
    audio_producer_agent,
    research_agent,
    scriptwriter_agent,
)
from podcast_agent.tools import read_document


root_agent = Agent(
    name="podcast_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Executive Producer coordinator agent that reads documents and orchestrates "
        "research, scriptwriting, and audio production across specialized subagents."
    ),
    # ── Context Caching Optimization ──
    # static_instruction is identical across all agents in the tree, ensuring that the Gemini system prompt prefix remains 100% cached between turns.
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[research_agent, scriptwriter_agent, audio_producer_agent],
    tools=[read_document, load_artifacts],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.5,
        tool_config=types.ToolConfig(
            include_server_side_tool_invocations=True
        ),
    ),
)
