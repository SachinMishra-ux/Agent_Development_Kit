"""Code Auditor Subagent Definition (code_auditor_agent).

Responsible for static code analysis, vulnerability scanning, and test case generation.
"""

from google.adk import Agent
from google.genai import types

from software_testing_agent.prompt import (
    CODE_AUDITOR_INSTRUCTION,
    TESTING_STUDIO_STATIC_INSTRUCTION,
)
from software_testing_agent.tools.code_analyzer import (
    analyze_code_security_and_quality,
    generate_unit_tests_template,
)
from software_testing_agent.tools.filesystem_tools import read_source_file

code_auditor_agent = Agent(
    name="code_auditor_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Performs static code auditing, detects security vulnerabilities (OWASP/CWE), "
        "identifies code quality smells, and generates unit test scaffolds."
    ),
    static_instruction=TESTING_STUDIO_STATIC_INSTRUCTION,
    instruction=CODE_AUDITOR_INSTRUCTION,
    tools=[analyze_code_security_and_quality, generate_unit_tests_template, read_source_file],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),
)
