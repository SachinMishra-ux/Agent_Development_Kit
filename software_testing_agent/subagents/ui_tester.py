"""UI and Frontend Tester Subagent Definition (ui_tester_agent).

Responsible for testing frontend UI code (HTML/CSS/JS, React, Vue), accessibility (WCAG),
DOM elements, responsive layouts, and frontend security (XSS, CSP).
"""

from google.adk import Agent
from google.genai import types

from software_testing_agent.prompt import (
    TESTING_STUDIO_STATIC_INSTRUCTION,
    UI_TESTER_INSTRUCTION,
)
from software_testing_agent.tools.filesystem_tools import read_source_file
from software_testing_agent.tools.ui_tester import (
    analyze_frontend_javascript_code,
    audit_ui_accessibility_and_dom,
    inspect_web_ui_elements,
)

ui_tester_agent = Agent(
    name="ui_tester_agent",
    model="gemini-3.1-flash-lite",
    description=(
        "Specialized UI & Frontend Testing agent that inspects HTML/CSS/JavaScript, "
        "audits WCAG accessibility, asserts DOM elements/selectors, validates mobile responsiveness, "
        "and checks for frontend security vulnerabilities like XSS and unsafe DOM manipulation."
    ),
    static_instruction=TESTING_STUDIO_STATIC_INSTRUCTION,
    instruction=UI_TESTER_INSTRUCTION,
    tools=[
        audit_ui_accessibility_and_dom,
        inspect_web_ui_elements,
        analyze_frontend_javascript_code,
        read_source_file,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),
)
