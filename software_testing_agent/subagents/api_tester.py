"""API Tester Subagent Definition (api_tester_agent).

Responsible for HTTP/REST endpoint probing, assertion, and latency benchmarking.
"""

from google.adk import Agent
from google.genai import types

from software_testing_agent.prompt import (
    API_TESTER_INSTRUCTION,
    TESTING_STUDIO_STATIC_INSTRUCTION,
)
from software_testing_agent.tools.api_tester import (
    check_service_health,
    test_http_endpoint,
)

api_tester_agent = Agent(
    name="api_tester_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Tests REST APIs and microservice endpoints by sending HTTP requests, asserting status codes, "
        "validating response payloads, and benchmarking latency."
    ),
    static_instruction=TESTING_STUDIO_STATIC_INSTRUCTION,
    instruction=API_TESTER_INSTRUCTION,
    tools=[test_http_endpoint, check_service_health],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),
)
