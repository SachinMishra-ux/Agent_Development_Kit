"""Test Executor Subagent Definition (test_executor_agent).

Responsible for running automated test suites (pytest/unittest) and diagnosing failures.
"""

from google.adk import Agent
from google.genai import types

from software_testing_agent.prompt import (
    TEST_EXECUTOR_INSTRUCTION,
    TESTING_STUDIO_STATIC_INSTRUCTION,
)
from software_testing_agent.tools.filesystem_tools import read_source_file
from software_testing_agent.tools.test_runner import (
    run_local_tests,
    run_syntax_and_lint_check,
)

test_executor_agent = Agent(
    name="test_executor_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Executes local automated test suites (pytest/unittest), verifies Python syntax, "
        "analyzes failure traces, and diagnoses root causes of bugs."
    ),
    static_instruction=TESTING_STUDIO_STATIC_INSTRUCTION,
    instruction=TEST_EXECUTOR_INSTRUCTION,
    tools=[run_local_tests, run_syntax_and_lint_check, read_source_file],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),
)
