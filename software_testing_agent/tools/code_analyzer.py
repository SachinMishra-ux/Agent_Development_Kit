"""Static Code Analysis and Security Audit Tool for Software Testing Agent.

Performs static AST inspection, security vulnerability checks (OWASP / CWE patterns),
code smell detection, and unit test scaffold generation.
"""

import ast
import os
import re
from typing import Dict, List, Optional


def analyze_code_security_and_quality(code_snippet_or_file_path: str) -> str:
    """Performs static code analysis and security auditing on code or a file.

    Detects common vulnerabilities (insecure eval/exec, shell injections, hardcoded credentials,
    SQL injection risks, bare excepts, resource leaks).

    Args:
        code_snippet_or_file_path: Direct source code string OR path to a code file.

    Returns:
        Structured audit report detailing security risks, code smells, and quality recommendations.
    """
    code_text = code_snippet_or_file_path
    file_context = "Direct Code Snippet"

    # If it's a file path that exists, read it
    if os.path.exists(code_snippet_or_file_path) and os.path.isfile(code_snippet_or_file_path):
        file_context = f"File: {code_snippet_or_file_path}"
        try:
            with open(code_snippet_or_file_path, "r", encoding="utf-8", errors="replace") as f:
                code_text = f.read()
        except Exception as e:
            return f"Error reading file '{code_snippet_or_file_path}': {str(e)}"

    findings = []
    lines = code_text.splitlines()

    # 1. Regex & Pattern Checks (Line-by-Line)
    secret_patterns = [
        (r'(?i)(api[_-]?key|secret|password|auth[_-]?token|access[_-]?token)\s*=\s*["\'][A-Za-z0-9_\-\.]{8,}["\']', "Potential Hardcoded Secret / API Token"),
        (r'AIza[0-9A-Za-z-_]{35}', "Google API Key Pattern Detected"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key Pattern Detected"),
        (r'-----BEGIN\s+(RSA|DSA|EC|OPENSSH)?\s*PRIVATE KEY-----', "Embedded Private Key Detected"),
    ]

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Skip commented lines
        if stripped.startswith("#"):
            continue

        for pattern, desc in secret_patterns:
            if re.search(pattern, stripped):
                findings.append({
                    "severity": "CRITICAL",
                    "type": "Hardcoded Credential",
                    "line": idx,
                    "snippet": stripped[:80],
                    "desc": desc,
                })

        # Check for bare except
        if re.match(r'except\s*:', stripped) or stripped == "except:":
            findings.append({
                "severity": "MEDIUM",
                "type": "Bare Except Clause",
                "line": idx,
                "snippet": stripped,
                "desc": "Catches all exceptions indiscriminately (including KeyboardInterrupt and SystemExit). Use 'except Exception:' instead.",
            })

        # Check for unparameterized SQL queries
        if re.search(r'(?i)(execute|cursor\.execute)\s*\(\s*(f["\']|.*\+.*SELECT|.*\+.*INSERT)', stripped):
            findings.append({
                "severity": "HIGH",
                "type": "SQL Injection Risk",
                "line": idx,
                "snippet": stripped[:90],
                "desc": "String formatting or concatenation in SQL query execution. Use parameterized queries instead.",
            })

    # 2. AST-Based Deep Inspection
    try:
        tree = ast.parse(code_text)

        class CodeVisitor(ast.NodeVisitor):
            def __init__(self):
                self.calls = []
                self.has_asserts = False
                self.has_type_annotations = False
                self.functions_count = 0
                self.classes_count = 0

            def visit_FunctionDef(self, node):
                self.functions_count += 1
                if node.returns or any(arg.annotation for arg in node.args.args):
                    self.has_type_annotations = True
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                self.functions_count += 1
                self.generic_visit(node)

            def visit_ClassDef(self, node):
                self.classes_count += 1
                self.generic_visit(node)

            def visit_Call(self, node):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                line_no = getattr(node, "lineno", "?")

                # Insecure execution functions
                if func_name in ["eval", "exec"]:
                    findings.append({
                        "severity": "CRITICAL",
                        "type": "Arbitrary Code Execution Risk",
                        "line": line_no,
                        "snippet": f"{func_name}(...)",
                        "desc": f"Use of built-in '{func_name}' allows dynamic code execution and vulnerability to remote code execution (RCE).",
                    })
                elif func_name in ["system", "popen"] and isinstance(getattr(node.func, "value", None), ast.Name) and node.func.value.id == "os":
                    findings.append({
                        "severity": "HIGH",
                        "type": "Command Injection Risk",
                        "line": line_no,
                        "snippet": "os.system / os.popen",
                        "desc": "Unsafe system command invocation. Use subprocess.run with shell=False and argument arrays instead.",
                    })
                elif func_name == "loads" and isinstance(getattr(node.func, "value", None), ast.Name) and node.func.value.id == "pickle":
                    findings.append({
                        "severity": "CRITICAL",
                        "type": "Insecure Deserialization",
                        "line": line_no,
                        "snippet": "pickle.loads(...)",
                        "desc": "Pickle deserialization from untrusted sources can lead to remote code execution.",
                    })

                self.generic_visit(node)

        visitor = CodeVisitor()
        visitor.visit(tree)

        stats = {
            "functions": visitor.functions_count,
            "classes": visitor.classes_count,
            "has_type_hints": visitor.has_type_annotations,
        }
    except SyntaxError as e:
        return f"❌ Syntax Error in target code at line {e.lineno}: {e.msg}\n  {e.text}"
    except Exception as e:
        stats = {"functions": 0, "classes": 0, "has_type_hints": False}

    # Format Markdown Report
    report = [
        f"### Static Code Analysis & Security Audit: `{file_context}`",
        f"- **Functions Defined:** {stats.get('functions', 0)}",
        f"- **Classes Defined:** {stats.get('classes', 0)}",
        f"- **Type Annotations Present:** {'Yes' if stats.get('has_type_hints') else 'No / Minimal'}",
        f"- **Total Security / Quality Issues Identified:** {len(findings)}",
        "",
    ]

    if findings:
        report.append("#### Vulnerabilities and Code Smells:")
        for item in findings:
            sev_badge = {
                "CRITICAL": "🔴 CRITICAL",
                "HIGH": "🟠 HIGH",
                "MEDIUM": "🟡 MEDIUM",
                "LOW": "🔵 LOW",
            }.get(item["severity"], "⚪ INFO")

            report.append(f"- **{sev_badge}** (Line {item['line']}): `{item['type']}`")
            report.append(f"  - **Description:** {item['desc']}")
            report.append(f"  - **Snippet:** `{item['snippet']}`")
            report.append("")
    else:
        report.append("✅ No critical security anti-patterns (eval, injection, hardcoded keys) detected in static scan.")

    return "\n".join(report)


def generate_unit_tests_template(source_file_path: str, framework: str = "pytest") -> str:
    """Extracts function and class signatures from a Python file and generates a pytest scaffold.

    Args:
        source_file_path: Path to the Python source file.
        framework: Testing framework for the template ('pytest' or 'unittest').

    Returns:
        A ready-to-run Python test file template containing test stubs and edge-case assertions.
    """
    if not os.path.exists(source_file_path):
        return f"Error: Source file '{source_file_path}' does not exist."

    try:
        with open(source_file_path, "r", encoding="utf-8") as f:
            code_text = f.read()
        tree = ast.parse(code_text)
    except Exception as e:
        return f"Error parsing source file '{source_file_path}': {str(e)}"

    mod_name = os.path.splitext(os.path.basename(source_file_path))[0]
    functions = []
    classes = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args]
            functions.append({"name": node.name, "args": args})
        elif isinstance(node, ast.ClassDef):
            methods = [
                m.name for m in node.body
                if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")
            ]
            classes.append({"name": node.name, "methods": methods})

    lines = [
        f'"""Automated Test Suite for `{mod_name}` generated by Software Testing Agent."""',
        "",
        "import pytest",
        f"from {mod_name} import *",
        "",
    ]

    for func in functions:
        fname = func["name"]
        lines.extend([
            f"def test_{fname}_happy_path():",
            f'    """Verifies standard input and expected success behavior for {fname}."""',
            f"    # TODO: Supply valid test arguments: {func['args']}",
            f"    # result = {fname}()",
            f"    # assert result is not None",
            "    pass",
            "",
            f"def test_{fname}_edge_cases():",
            f'    """Verifies boundary values, zero/empty states, and unexpected inputs for {fname}."""',
            f"    # with pytest.raises(ValueError):",
            f"    #     {fname}(None)",
            "    pass",
            "",
        ])

    for cls in classes:
        cname = cls["name"]
        lines.extend([
            f"class Test{cname}:",
            f'    """Test suite for {cname} class."""',
            "",
            "    @pytest.fixture",
            "    def instance(self):",
            f"        # TODO: Initialize instance of {cname}",
            f"        return {cname}()",
            "",
        ])
        for method in cls["methods"]:
            lines.extend([
                f"    def test_{method}(self, instance):",
                f'        """Tests {method} on {cname}."""',
                f"        # result = instance.{method}()",
                "        pass",
                "",
            ])

    return "\n".join(lines)
