"""Root Coordinator Agent Definition (software_testing_agent).

This module defines the primary entry point for the Software Testing Agent system.
The coordinator acts as the Lead QA Architect:
- Capable of testing UI code, backend server code, REST APIs, and test suites.
- Coordinates testing across four specialized subagents:
  1. ui_tester_agent (Frontend, DOM, HTML/CSS/JS, WCAG accessibility, XSS)
  2. test_executor_agent (Backend & frontend automated test suites)
  3. code_auditor_agent (Static analysis, OWASP security audit, test case generation)
  4. api_tester_agent (REST API & microservice endpoint probing)
- Employs static_instruction for Gemini Context Cache alignment.
- Generates executive QA audit reports with actionable patch recommendations.
"""

from google.adk import Agent
from google.genai import types

from software_testing_agent.prompt import (
    COORDINATOR_INSTRUCTION,
    TESTING_STUDIO_STATIC_INSTRUCTION,
)
from software_testing_agent.subagents import (
    api_tester_agent,
    code_auditor_agent,
    test_executor_agent,
    ui_tester_agent,
)
from software_testing_agent.tools import (
    analyze_code_security_and_quality,
    analyze_frontend_javascript_code,
    audit_ui_accessibility_and_dom,
    generate_qa_report,
    inspect_code_directory,
    inspect_web_ui_elements,
    read_source_file,
    run_local_tests,
    run_syntax_and_lint_check,
    test_http_endpoint,
)

root_agent = Agent(
    name="software_testing_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Universal Lead QA Architect & Full-Stack Software Testing Coordinator that tests "
        "frontend UI code (HTML/CSS/JS, a11y, DOM, responsive layout), backend server code, "
        "automated test suites (pytest, npm test), REST APIs, and produces comprehensive QA audit reports."
    ),
    static_instruction=TESTING_STUDIO_STATIC_INSTRUCTION,
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[
        ui_tester_agent,
        test_executor_agent,
        code_auditor_agent,
        api_tester_agent,
    ],
    tools=[
        audit_ui_accessibility_and_dom,
        inspect_web_ui_elements,
        analyze_frontend_javascript_code,
        inspect_code_directory,
        read_source_file,
        run_local_tests,
        run_syntax_and_lint_check,
        analyze_code_security_and_quality,
        test_http_endpoint,
        generate_qa_report,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
    ),
)
