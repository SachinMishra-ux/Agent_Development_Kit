# 🛡️ Universal Software Testing & QA Agent (Google ADK)

A comprehensive, production-ready, full-stack **Software Testing and Quality Assurance Agent** built using the **Google Agent Development Kit (ADK)** and powered by Gemini models (`gemini-3.1-flash-lite`).

This agent acts as an autonomous **Lead QA Architect** capable of testing **any kind of software**:
- 🌐 **UI & Frontend Code**: HTML5, CSS3, JavaScript, React, Vue, DOM elements, WCAG accessibility (a11y), responsive viewport, and frontend XSS security.
- ⚙️ **Backend Server Code**: Business logic, algorithms, Python/Node services, data models, and edge cases.
- 🧪 **Automated Test Suites**: Backend (`pytest`, `unittest`) and Frontend (`npm test`, `jest`, `vitest`, `playwright`).
- 🔌 **REST APIs & Microservices**: HTTP status code assertions, payload schemas, latency benchmarking, and endpoint health checks.
- 🔒 **Security & Vulnerability Scanning**: OWASP top 10 anti-patterns, SQL injection, unsafe `eval`/`exec`, exposed credentials, and unhandled errors.

---

## 🏗️ Architecture Overview

The system uses a collaborative multi-agent architecture with a Root Coordinator and four specialized subagents:

```
                                    ┌─────────────────────────────────────────┐
                                    │         software_testing_agent          │
                                    │         (Lead QA Architect)             │
                                    └────────────────────┬────────────────────┘
                                                         │
            ┌────────────────────────────┬───────────────┴───────────────┬────────────────────────────┐
            ▼                            ▼                               ▼                            ▼
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│     ui_tester_agent     │  │   test_executor_agent   │  │   code_auditor_agent    │  │    api_tester_agent     │
│ (UI, DOM, a11y, WCAG)   │  │(Pytest, Jest, Playwright│  │ (Static Security & AST) │  │  (REST API & Latency)   │
└───────────┬─────────────┘  └───────────┬─────────────┘  └───────────┬─────────────┘  └───────────┬─────────────┘
            │                            │                                │                            │
    • audit_ui_accessibility     • run_local_tests                • analyze_code_security      • test_http_endpoint
    • inspect_web_ui_elements    • run_syntax_and_lint            • generate_unit_tests        • check_service_health
    • analyze_frontend_js        • read_source_file               • read_source_file
```

---

## 📂 Folder Structure

```
software_testing_agent/
├── __init__.py                     # Package export (exports root_agent)
├── agent.py                        # Root coordinator Agent definition
├── prompt.py                       # Prompts & static instruction (Gemini context caching)
├── schemas.py                      # Pydantic data schemas (Test cases, suites, findings)
├── tools/
│   ├── __init__.py                 # Tool exports
│   ├── ui_tester.py                # UI DOM inspection, WCAG accessibility, frontend JS analysis
│   ├── test_runner.py              # Pytest, unittest, npm test, jest, vitest, playwright runner
│   ├── code_analyzer.py            # AST static security audit & test generator
│   ├── api_tester.py               # REST API HTTP tester & health check
│   ├── filesystem_tools.py         # Directory tree & source file inspector
│   └── report_generator.py         # Markdown QA audit report generator
├── subagents/
│   ├── __init__.py                 # Subagent exports
│   ├── ui_tester.py                # ui_tester_agent (Frontend & UI specialist)
│   ├── test_executor.py            # test_executor_agent (Backend & frontend test runner)
│   ├── code_auditor.py             # code_auditor_agent (Static analysis & security)
│   └── api_tester.py               # api_tester_agent (REST API specialist)
├── sample_software_to_test/        # Ready-to-test sample software
│   ├── __init__.py
│   ├── sample_ui_form.html         # UI HTML with intentional WCAG, viewport & button bugs
│   ├── sample_ui_script.js         # Frontend JS with innerHTML XSS & unhandled network errors
│   ├── order_calculator.py         # Backend logic with intentional edge-case bugs
│   ├── test_order_calculator.py    # Test suite with passing and failing assertions
│   └── vulnerable_auth_service.py  # Code with hardcoded keys, SQL injection & eval
├── reports/                        # Automatically generated QA reports (.md)
│   └── README.md
└── README.md                       # This guide
```

---

## 🚀 How to Run the Software Testing Agent

### Option 1: Automated Verification Script (Recommended)
Run the automated test runner script across UI, backend, and API testing:
```bash
uv run python test_software_testing_agent.py
```

### Option 2: ADK Interactive Web UI
Launch the built-in ADK Web Interface on `http://localhost:8000`:
```bash
uv run adk web .
```
Open your browser, select `software_testing_agent` from the dropdown, and chat with the agent!

### Option 3: ADK Command Line Interface (CLI)
Interact with the agent directly in your terminal:
```bash
uv run adk run software_testing_agent
```

---

## 💡 Example Prompt Scenarios

### 1. Test UI & Frontend Code (HTML, CSS, JS, a11y)
> *"Please audit `my_frontend/index.html` and `my_frontend/app.js`. Check for WCAG accessibility issues (missing alt tags, unlabeled form inputs), mobile viewport configuration, and XSS risks like `innerHTML`."*

### 2. Assert Specific Elements on a Web Page
> *"Inspect `http://localhost:3000` (or `index.html`) and check if `#submit-btn`, `.navbar`, and `input[name='email']` exist on the page."*

### 3. Run Backend / Frontend Test Suites
> *"Please run the pytest suite in `tests/test_api.py` (or npm test in `frontend/`). If any test fails, explain why and provide the code patch."*

### 4. Test Live REST APIs
> *"Please test `http://localhost:8080/api/users` with POST method and payload `{'name': 'test'}`. Verify status 201 and latency < 500ms."*

### 5. Static Security Audit & Full QA Report
> *"Please perform a full QA audit of my project repository and save a comprehensive QA audit report."*
