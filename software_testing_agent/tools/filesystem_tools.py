"""Filesystem and Code Inspection Tools for Software Testing Agent.

Provides utilities for inspecting software project structures and reading source code files.
"""

import os
from typing import List, Optional


def inspect_code_directory(directory_path: str = ".", max_depth: int = 3) -> str:
    """Inspects a software directory structure to detect project type, source files, and test files.

    Args:
        directory_path: Relative or absolute path to the software directory. Defaults to current directory.
        max_depth: Maximum recursion depth for directory exploration.

    Returns:
        A structured summary listing detected project configuration, source files, test suites, and hierarchy.
    """
    target = os.path.abspath(directory_path)
    if not os.path.exists(target):
        return f"Error: Target path '{directory_path}' does not exist."
    if not os.path.isdir(target):
        return f"Error: Target path '{directory_path}' is a file, not a directory."

    detected_configs = []
    test_files = []
    source_files = []
    tree_lines = []

    # Identify project configuration markers
    config_markers = [
        "pyproject.toml", "requirements.txt", "package.json", "go.mod", 
        "Cargo.toml", "pom.xml", "build.gradle", "Dockerfile", "docker-compose.yml"
    ]
    for marker in config_markers:
        if os.path.exists(os.path.join(target, marker)):
            detected_configs.append(marker)

    start_depth = target.rstrip(os.path.sep).count(os.path.sep)
    for root, dirs, files in os.walk(target):
        # Exclude common build and virtual environment directories
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".adk"}]
        current_depth = root.rstrip(os.path.sep).count(os.path.sep) - start_depth
        if current_depth > max_depth:
            continue

        indent = "  " * current_depth
        rel_root = os.path.relpath(root, target)
        if rel_root != ".":
            tree_lines.append(f"{indent}📂 {os.path.basename(root)}/")

        for f in sorted(files):
            rel_path = os.path.normpath(os.path.join(rel_root, f))
            tree_lines.append(f"{indent}  📄 {f}")
            if "test" in f.lower() or f.startswith("test_") or f.endswith(("_test.py", ".spec.ts", ".test.js")):
                test_files.append(rel_path)
            elif f.endswith((".py", ".js", ".ts", ".go", ".java", ".rs", ".cpp", ".c", ".cs")):
                source_files.append(rel_path)

    summary = [
        f"### Project Structure Inspection: `{os.path.basename(target)}`",
        f"- **Absolute Path:** `{target}`",
        f"- **Detected Configs / Manifests:** {', '.join(detected_configs) if detected_configs else 'None'}",
        f"- **Total Source Files Found:** {len(source_files)}",
        f"- **Total Test Files Found:** {len(test_files)}",
        "",
        "#### Discovered Test Files:",
    ]
    if test_files:
        summary.extend([f"  - `{tf}`" for tf in test_files[:20]])
    else:
        summary.append("  *(No explicit test files detected)*")

    summary.append("\n#### Directory Hierarchy (Up to depth " + str(max_depth) + "):")
    summary.extend(tree_lines[:60])
    if len(tree_lines) > 60:
        summary.append(f"  ... ({len(tree_lines) - 60} more files omitted)")

    return "\n".join(summary)


def read_source_file(file_path: str, line_start: int = 1, line_end: int = 250) -> str:
    """Reads lines from a source code or test file with line numbering for debugging and analysis.

    Args:
        file_path: Path to the code or test file.
        line_start: Starting line number (1-based index).
        line_end: Ending line number (inclusive).

    Returns:
        Line-numbered file contents or an error message if the file cannot be read.
    """
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' not found."
    if not os.path.isfile(file_path):
        return f"Error: Path '{file_path}' is not a regular file."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        start_idx = max(0, line_start - 1)
        end_idx = min(total_lines, line_end)

        selected = lines[start_idx:end_idx]
        output = [f"--- File: {file_path} (Lines {start_idx + 1} to {end_idx} of {total_lines}) ---"]
        for idx, line in enumerate(selected, start=start_idx + 1):
            output.append(f"{idx:4d} | {line.rstrip()}")

        return "\n".join(output)
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"
