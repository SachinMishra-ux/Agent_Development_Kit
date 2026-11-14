"""Test Runner Tool for Software Testing Agent.

Executes test suites (pytest, unittest, etc.) and captures test outcomes, assertions,
stack traces, and duration metrics.
"""

import os
import re
import subprocess
import sys
import time
from typing import Optional


def run_local_tests(
    test_target: str = "",
    framework: str = "pytest",
    extra_args: str = "-v",
    timeout_seconds: int = 60,
) -> str:
    """Executes automated test suites across backend (pytest, unittest) and frontend (npm test, jest, vitest, playwright).

    Args:
        test_target: Path to test file, test directory, or specific test node (e.g. 'tests/test_api.py::test_login' or 'src/App.test.tsx').
                     If empty, runs tests across the default project test discovery root.
        framework: Test framework to invoke ('pytest', 'unittest', 'npm', 'jest', 'vitest', 'playwright'). Defaults to 'pytest'.
        extra_args: Additional command line flags (e.g. '-v', '-k test_name', '--runInBand').
        timeout_seconds: Maximum time in seconds before terminating the test process.

    Returns:
        A detailed summary containing execution status, pass/fail counts, duration, and failure stack traces.
    """
    cmd = []
    python_bin = sys.executable

    framework_clean = framework.lower().strip()
    if framework_clean == "pytest":
        cmd = [python_bin, "-m", "pytest"]
        if extra_args:
            cmd.extend(extra_args.split())
        if test_target:
            cmd.append(test_target)
    elif framework_clean == "unittest":
        cmd = [python_bin, "-m", "unittest"]
        if extra_args:
            cmd.extend(extra_args.split())
        if test_target:
            cmd.append(test_target)
    elif framework_clean in ["npm", "npm test"]:
        cmd = ["npm", "test", "--"]
        if extra_args:
            cmd.extend(extra_args.split())
        if test_target:
            cmd.append(test_target)
    elif framework_clean in ["jest", "vitest", "playwright"]:
        cmd = ["npx", framework_clean]
        if extra_args:
            cmd.extend(extra_args.split())
        if test_target:
            cmd.append(test_target)
    else:
        return f"Error: Unsupported test framework '{framework}'. Supported: 'pytest', 'unittest', 'npm', 'jest', 'vitest', 'playwright'."

    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration = round(time.time() - start_time, 2)
        stdout = proc.stdout
        stderr = proc.stderr
        return_code = proc.returncode

        # Parse output for pytest metrics
        passed = len(re.findall(r" PASSED ", stdout)) or len(re.findall(r"::.* PASSED", stdout))
        failed = len(re.findall(r" FAILED ", stdout)) or len(re.findall(r"::.* FAILED", stdout))
        errors = len(re.findall(r" ERROR ", stdout)) or len(re.findall(r"::.* ERROR", stdout))

        # Check unittest metrics if pytest didn't match
        if passed == 0 and failed == 0:
            match = re.search(r"Ran (\d+) tests? in ([\d\.]+)s", stderr)
            if match:
                total_ran = int(match.group(1))
                if "OK" in stderr:
                    passed = total_ran
                elif "FAILED" in stderr:
                    fail_match = re.search(r"failures=(\d+)", stderr)
                    err_match = re.search(r"errors=(\d+)", stderr)
                    failed = int(fail_match.group(1)) if fail_match else 0
                    errors = int(err_match.group(1)) if err_match else 0
                    passed = max(0, total_ran - failed - errors)

        status_label = "✅ PASSED" if return_code == 0 else "❌ FAILED"
        result_lines = [
            f"### Test Execution Result: {status_label}",
            f"- **Framework:** `{framework_clean}`",
            f"- **Target:** `{test_target or 'Default Discovery Root'}`",
            f"- **Command:** `{' '.join(cmd)}`",
            f"- **Exit Code:** `{return_code}`",
            f"- **Execution Time:** `{duration}s`",
            f"- **Detected Stats:** Passed: {passed}, Failed: {failed}, Errors: {errors}",
            "",
            "#### Output (Stdout / Stderr):",
            "```text",
            (stdout + ("\n" + stderr if stderr else "")).strip()[:4000],
            "```",
        ]

        if return_code != 0:
            result_lines.append("\n> [!WARNING] Test failures detected. Inspect failure tracebacks above to identify root causes and fixes.")

        return "\n".join(result_lines)

    except subprocess.TimeoutExpired:
        return f"❌ Error: Test execution timed out after {timeout_seconds} seconds. Command: {' '.join(cmd)}"
    except Exception as e:
        return f"❌ Error executing tests: {str(e)}"


def run_syntax_and_lint_check(file_or_dir_path: str) -> str:
    """Verifies Python syntax and checks for code compilation errors without running the code.

    Args:
        file_or_dir_path: Path to a Python file or directory of Python files to inspect.

    Returns:
        A report indicating syntax status, line numbers of any SyntaxErrors, or success confirmation.
    """
    import ast
    target = os.path.abspath(file_or_dir_path)
    if not os.path.exists(target):
        return f"Error: Path '{file_or_dir_path}' does not exist."

    py_files = []
    if os.path.isfile(target):
        if target.endswith(".py"):
            py_files.append(target)
        else:
            return f"Note: '{file_or_dir_path}' is not a Python (.py) file."
    else:
        for root, _, files in os.walk(target):
            if any(p in root for p in [".venv", "venv", "__pycache__", ".git"]):
                continue
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))

    if not py_files:
        return f"No Python files found under '{file_or_dir_path}'."

    errors = []
    clean_count = 0

    for py_file in py_files:
        try:
            with open(py_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            ast.parse(content, filename=py_file)
            clean_count += 1
        except SyntaxError as e:
            errors.append({
                "file": os.path.relpath(py_file),
                "line": e.lineno,
                "offset": e.offset,
                "msg": e.msg,
                "text": e.text.strip() if e.text else "",
            })
        except Exception as e:
            errors.append({
                "file": os.path.relpath(py_file),
                "line": "?",
                "offset": "?",
                "msg": str(e),
                "text": "",
            })

    report = [
        f"### Static Syntax Verification Summary",
        f"- **Files Checked:** {len(py_files)}",
        f"- **Syntax Valid:** {clean_count}",
        f"- **Syntax Errors:** {len(errors)}",
        "",
    ]
    if errors:
        report.append("#### Detected Syntax Errors:")
        for err in errors:
            report.append(f"- ❌ `{err['file']}` (Line {err['line']}): **{err['msg']}**")
            if err["text"]:
                report.append(f"  ```python\n  {err['text']}\n  ```")
    else:
        report.append("✅ All inspected Python files passed syntax validation.")

    return "\n".join(report)
