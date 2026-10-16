"""Test script to verify the Podcast Agent multi-agent collaboration and audio generation."""

import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from podcast_agent.agent import root_agent
from podcast_agent.tools.audio_generator import generate_podcast_audio


async def main():
    print("=" * 65)
    print("🎙️  Testing Podcast Agent (Google ADK Collaborative System)")
    print("=" * 65)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="podcast_agent",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="podcast_agent",
        user_id="podcast_user",
    )

    user_prompt = (
        "I want to create a 3-person podcast about: "
        "'How Autonomous AI Agents are Changing Software Engineering'. "
        "Please plan the episode and write a short engaging 4-turn script "
        "between Alex (Host), Morgan (Expert), and Taylor (Skeptic)."
    )

    print(f"\n[User Request]: {user_prompt}\n")
    print("-" * 65)

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_prompt)],
    )

    async for event in runner.run_async(
        user_id="podcast_user",
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text, end="", flush=True)

    print("\n\n" + "=" * 65)
    print("🎧 Synthesizing Demo Multi-Speaker Audio Track (.mp3)...")
    print("=" * 65)

    sample_dialogue = [
        {
            "speaker": "Alex",
            "text": "Welcome to The Build Loop! Today we're tackling a massive question: Are AI agents about to replace software engineers, or are they just the ultimate copilot?",
        },
        {
            "speaker": "Morgan",
            "text": "Hey Alex! In my view, agents aren't replacing developers; they're elevating them. Instead of typing boilerplate, engineers are becoming architects who orchestrate swarms of specialized agents.",
        },
        {
            "speaker": "Taylor",
            "text": "Hold on Morgan, that sounds great in theory, but what about debugging? If an agent writes 5,000 lines of code across ten files, who is actually on the hook when production goes down at 2 AM?",
        },
        {
            "speaker": "Alex",
            "text": "Taylor cuts right to the heart of it! That's exactly why human-in-the-loop validation is the most critical design pattern in modern agent systems. Let's dig into that.",
        },
    ]

    result = await generate_podcast_audio(sample_dialogue, "software_agents_3_hosts.mp3")
    print("\n" + str(result))


if __name__ == "__main__":
    asyncio.run(main())
