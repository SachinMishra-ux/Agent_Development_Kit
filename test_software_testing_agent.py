"""Test script to verify the Universal Software Testing Agent (UI, Backend, APIs, Test Suites)."""

import asyncio
from dotenv import load_dotenv

# Load environment variables (.env)
load_dotenv(override=True)

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from software_testing_agent.agent import root_agent


async def run_query(runner: Runner, session_id: str, prompt_text: str):
    print("\n" + "=" * 70)
    print(f"🧪 USER QUERY: {prompt_text}")
    print("=" * 70)

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt_text)],
    )

    print("\n🤖 AGENT EXECUTION & OUTPUT:\n")
    async for event in runner.run_async(
        user_id="qa_tester",
        session_id=session_id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text, end="", flush=True)
    print("\n")


async def main():
    print("*" * 70)
    print("🛡️  Testing Universal Software Testing Agent (UI + Backend + API)")
    print("*" * 70)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="software_testing_agent",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="software_testing_agent",
        user_id="qa_tester",
    )

    # -------------------------------------------------------------
    # Scenario 1: UI & Frontend Testing (HTML, CSS/JS, WCAG, DOM)
    # -------------------------------------------------------------
    prompt_ui_test = (
        "Please perform a complete UI and frontend test on the web files: "
        "'software_testing_agent/sample_software_to_test/sample_ui_form.html' and "
        "'software_testing_agent/sample_software_to_test/sample_ui_script.js'. "
        "Audit for WCAG accessibility (missing alt, form labels, empty buttons), "
        "mobile responsiveness viewport tags, and frontend JavaScript security (XSS innerHTML)."
    )
    await run_query(runner, session.id, prompt_ui_test)

    # -------------------------------------------------------------
    # Scenario 2: Backend Test Suite Execution & Bug Diagnosis
    # -------------------------------------------------------------
    prompt_test_suite = (
        "Please run the test suite in "
        "'software_testing_agent/sample_software_to_test/test_order_calculator.py'. "
        "Report pass/fail counts. If any test fails, inspect the source code, "
        "explain the root cause, and provide the code patch to fix it."
    )
    await run_query(runner, session.id, prompt_test_suite)

    # -------------------------------------------------------------
    # Scenario 3: REST API & Backend Server Probing
    # -------------------------------------------------------------
    prompt_api = (
        "Please test the HTTP endpoint 'https://httpbin.org/get'. "
        "Confirm if it returns HTTP status 200, check the round-trip latency, "
        "and verify that the response body is valid JSON."
    )
    await run_query(runner, session.id, prompt_api)

    print("=" * 70)
    print("🎉 All Full-Stack (UI, Backend, API) verification scenarios completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
