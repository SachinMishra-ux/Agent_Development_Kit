"""Pydantic Data Models and Schemas for Podcast Studio Agent.

This module defines the structured data contracts used across the podcast pipeline:
1. SpeakerProfile: Casting profile defining persona, role, and TTS voice ID.
2. PodcastPlan: High-level architectural plan of the episode.
3. DialogueTurn: A single spoken dialogue turn (speaker + spoken text).
4. PodcastScript: Complete episode script containing a sequence of DialogueTurns.
5. ResearchInput & ResearchBrief: Input/Output schemas for factual web research.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ── 1. Casting & Planning Schemas ─────────────────────────────────────────────

class SpeakerProfile(BaseModel):
    """Profile describing a podcast persona and their assigned neural voice."""
    name: str = Field(description="Name of the podcast speaker / host (e.g. Alex, Morgan, Taylor)")
    role: str = Field(description="Role in the conversation (e.g. Host, Expert, Skeptic)")
    tone: str = Field(description="Speaking style, tone, and personality characteristics")
    voice_id: str = Field(description="Voice identifier for TTS synthesis (e.g. en-US-GuyNeural)")


class PodcastPlan(BaseModel):
    """High-level outline and concept plan for a podcast episode."""
    episode_title: str = Field(description="Catchy title of the podcast episode")
    target_audience: str = Field(description="Target audience for the episode")
    core_topics: List[str] = Field(description="Main topics and questions to cover")
    speaker_count: int = Field(description="Number of speakers (2 or 3)")
    speaker_profiles: List[SpeakerProfile] = Field(description="Profiles for each speaker")


# ── 2. Dialogue & Script Schemas ──────────────────────────────────────────────

class DialogueTurn(BaseModel):
    """Represents a single conversational turn in the podcast dialogue."""
    speaker: str = Field(description="Name of the speaker talking in this turn (Alex, Morgan, or Taylor)")
    text: str = Field(description="Natural spoken dialogue text for this turn")


class PodcastScript(BaseModel):
    """Complete multi-speaker podcast script ready for audio synthesis."""
    episode_title: str = Field(description="Title of the podcast episode")
    speaker_count: int = Field(description="Number of speakers (2 or 3)")
    turns: List[DialogueTurn] = Field(description="Chronological dialogue turns of the podcast")


# ── 3. Research Schemas ───────────────────────────────────────────────────────

class ResearchInput(BaseModel):
    """Input payload sent to the researcher subagent."""
    topic: str = Field(description="Topic or query to research")
    raw_document_context: Optional[str] = Field(
        default=None,
        description="Optional text extracted from an attached PDF or Word document"
    )


class ResearchBrief(BaseModel):
    """Synthesized research briefing returned by the researcher subagent."""
    topic: str = Field(description="Researched topic")
    summary: str = Field(description="Executive summary of key findings")
    key_facts: List[str] = Field(description="Important facts, data points, and statistics")
    talking_points: List[str] = Field(description="Debate angles and questions for discussion")
