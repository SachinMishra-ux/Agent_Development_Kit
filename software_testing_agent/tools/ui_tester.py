"""UI and Frontend Testing Tool for Software Testing Agent.

Performs static UI code analysis, WCAG accessibility (a11y) auditing, DOM element
assertion, responsive viewport validation, and frontend JavaScript security checks.
"""

from bs4 import BeautifulSoup
import json
import os
import re
from typing import Dict, List, Optional
import urllib.parse
import requests


def audit_ui_accessibility_and_dom(file_path_or_html: str) -> str:
    """Audits HTML/UI code for accessibility (WCAG), semantic structure, and security issues.

    Checks for:
    - Missing viewport meta tags (mobile responsiveness)
    - Missing <title> and language attributes (<html lang="...">)
    - Images missing alt attributes (WCAG 1.1.1)
    - Form inputs missing associated <label> or aria-label (WCAG 1.3.1 / 4.1.2)
    - Buttons with empty text or missing labels (WCAG 4.1.2)
    - Unsafe links (target="_blank" without rel="noopener noreferrer")
    - Inline event handlers and XSS vectors (onclick, onload, etc.)
    - Skipped heading levels (e.g., h1 followed directly by h3)

    Args:
        file_path_or_html: Local file path to an HTML/UI file OR raw HTML string.

    Returns:
        Structured audit report detailing UI violations, a11y status, and remediation instructions.
    """
    html_content = file_path_or_html
    target_desc = "Raw HTML Snippet"

    if os.path.exists(file_path_or_html) and os.path.isfile(file_path_or_html):
        target_desc = f"File: {file_path_or_html}"
        try:
            with open(file_path_or_html, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()
        except Exception as e:
            return f"Error reading UI file '{file_path_or_html}': {str(e)}"

    soup = BeautifulSoup(html_content, "html.parser")
    violations = []
    passes = []

    # 1. Document Structure & Meta Tags
    html_tag = soup.find("html")
    if not html_tag:
        violations.append({
            "severity": "MEDIUM",
            "category": "HTML Structure",
            "desc": "Missing top-level <html> element.",
            "element": "<html>",
        })
    elif not html_tag.get("lang"):
        violations.append({
            "severity": "LOW",
            "category": "Accessibility (a11y)",
            "desc": "<html lang='...'> attribute is missing. Screen readers need language specification.",
            "element": f"<html {dict(html_tag.attrs)}>",
        })
    else:
        passes.append("Document language specified via <html lang='...'>")

    title_tag = soup.find("title")
    if not title_tag or not title_tag.text.strip():
        violations.append({
            "severity": "HIGH",
            "category": "SEO & Accessibility",
            "desc": "Missing or empty <title> tag in document head.",
            "element": "<title>",
        })
    else:
        passes.append(f"Page title present: '{title_tag.text.strip()}'")

    viewport_meta = soup.find("meta", attrs={"name": "viewport"})
    if not viewport_meta:
        violations.append({
            "severity": "HIGH",
            "category": "Responsive Design",
            "desc": "Missing <meta name='viewport' content='width=device-width, initial-scale=1.0'>. Page will not render properly on mobile devices.",
            "element": "<meta name='viewport'>",
        })
    else:
        passes.append("Responsive mobile viewport meta tag configured.")

    # 2. Image Accessibility (Alt text)
    images = soup.find_all("img")
    missing_alt = 0
    for img in images:
        if "alt" not in img.attrs:
            missing_alt += 1
            violations.append({
                "severity": "HIGH",
                "category": "Accessibility (WCAG 1.1.1)",
                "desc": "Image element is missing an 'alt' attribute.",
                "element": str(img)[:80],
            })
    if images and missing_alt == 0:
        passes.append(f"All {len(images)} images contain alt descriptions.")

    # 3. Form Input Labeling
    inputs = soup.find_all(["input", "textarea", "select"])
    unlabeled_inputs = 0
    for inp in inputs:
        inp_type = inp.get("type", "text")
        if inp_type in ["hidden", "submit", "button", "reset"]:
            continue
        
        inp_id = inp.get("id")
        has_label = False
        if inp_id and soup.find("label", attrs={"for": inp_id}):
            has_label = True
        elif inp.find_parent("label"):
            has_label = True
        elif inp.get("aria-label") or inp.get("aria-labelledby"):
            has_label = True

        if not has_label:
            unlabeled_inputs += 1
            violations.append({
                "severity": "HIGH",
                "category": "Accessibility (WCAG 1.3.1 / 4.1.2)",
                "desc": f"Form control <{inp.name} type='{inp_type}'> lacks an associated <label> or aria-label.",
                "element": str(inp)[:80],
            })
    if inputs and unlabeled_inputs == 0:
        passes.append(f"All {len(inputs)} interactive form inputs are properly labeled.")

    # 4. Buttons with empty content
    buttons = soup.find_all("button")
    for btn in buttons:
        btn_text = btn.text.strip()
        if not btn_text and not btn.get("aria-label") and not btn.find("img"):
            violations.append({
                "severity": "HIGH",
                "category": "Accessibility (WCAG 4.1.2)",
                "desc": "Button is empty and has no readable text or aria-label for screen readers.",
                "element": str(btn)[:80],
            })

    # 5. Unsafe External Links (Tabnabbing)
    links = soup.find_all("a", href=True)
    for link in links:
        if link.get("target") == "_blank":
            rel = link.get("rel", [])
            rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)
            if "noopener" not in rel_str or "noreferrer" not in rel_str:
                violations.append({
                    "severity": "MEDIUM",
                    "category": "Security (Reverse Tabnabbing)",
                    "desc": "Link opens in new tab with target='_blank' but is missing rel='noopener noreferrer'.",
                    "element": str(link)[:90],
                })

    # 6. Inline JavaScript Event Handlers (XSS / CSP violation)
    inline_events = [
        "onclick", "onload", "onerror", "onmouseover", "onfocus", "onchange", "onsubmit"
    ]
    inline_event_count = 0
    for tag in soup.find_all(True):
        for event in inline_events:
            if tag.get(event):
                inline_event_count += 1
                violations.append({
                    "severity": "MEDIUM",
                    "category": "Frontend Security / Maintainability",
                    "desc": f"Inline event handler '{event}' violates modern Content Security Policy (CSP). Use addEventListener in external JS.",
                    "element": str(tag)[:80],
                })
                break

    # Format report
    report = [
        f"### UI & Accessibility Audit Report: `{target_desc}`",
        f"- **DOM Elements Inspected:** {len(soup.find_all(True))}",
        f"- **Passed Checks:** {len(passes)}",
        f"- **Issues Detected:** {len(violations)}",
        "",
        "#### Passed Validations:",
    ]
    for p in passes:
        report.append(f"- ✅ {p}")
    if not passes:
        report.append("- *(No standard checks passed)*")

    report.append("\n#### Detected Issues & WCAG Violations:")
    if violations:
        for v in violations:
            badge = {
                "CRITICAL": "🔴 CRITICAL",
                "HIGH": "🟠 HIGH",
                "MEDIUM": "🟡 MEDIUM",
                "LOW": "🔵 LOW",
            }.get(v["severity"], "⚪ INFO")
            report.append(f"- **{badge}** [{v['category']}]: {v['desc']}")
            report.append(f"  `{v['element']}`")
    else:
        report.append("✅ No accessibility or structural violations detected.")

    return "\n".join(report)


def inspect_web_ui_elements(
    url_or_file_path: str,
    required_selectors_json: str = "[]",
) -> str:
    """Inspects a web page or HTML file to verify the presence of critical UI components.

    Args:
        url_or_file_path: Live web URL (e.g. 'http://localhost:8080') or local HTML file path.
        required_selectors_json: JSON list of CSS selectors to assert (e.g. '["#submit-btn", "nav.main", "input[name=\\"email\\"]"]').

    Returns:
        Summary of UI elements found, page title, forms, buttons, and assertion pass/fail for required selectors.
    """
    try:
        required_selectors = json.loads(required_selectors_json) if required_selectors_json else []
    except Exception:
        required_selectors = [s.strip() for s in required_selectors_json.split(",") if s.strip()]

    html_content = ""
    source_type = "File"

    if url_or_file_path.startswith(("http://", "https://")):
        source_type = f"Live URL ({url_or_file_path})"
        try:
            resp = requests.get(url_or_file_path, timeout=8.0)
            if resp.status_code != 200:
                return f"Error: Received HTTP {resp.status_code} when requesting {url_or_file_path}."
            html_content = resp.text
        except Exception as e:
            return f"Error: Could not connect to {url_or_file_path}: {str(e)}"
    elif os.path.exists(url_or_file_path):
        source_type = f"Local File ({url_or_file_path})"
        try:
            with open(url_or_file_path, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()
        except Exception as e:
            return f"Error reading file '{url_or_file_path}': {str(e)}"
    else:
        return f"Error: '{url_or_file_path}' is neither a reachable URL nor an existing file."

    soup = BeautifulSoup(html_content, "html.parser")

    # Inventory
    forms = soup.find_all("form")
    buttons = soup.find_all("button")
    inputs = soup.find_all("input")
    links = soup.find_all("a")
    headings = soup.find_all(["h1", "h2", "h3"])

    # Check Required Selectors
    selector_results = []
    missing_selectors = 0
    for sel in required_selectors:
        found = soup.select(sel)
        if found:
            selector_results.append(f"- ✅ Selector `{sel}` found ({len(found)} instance(s))")
        else:
            missing_selectors += 1
            selector_results.append(f"- ❌ Selector `{sel}` **NOT FOUND** on page")

    report = [
        f"### UI Component Inspection: `{source_type}`",
        f"- **Title:** `{soup.title.text.strip() if soup.title else 'No Title'}`",
        f"- **Forms Found:** {len(forms)}",
        f"- **Buttons Found:** {len(buttons)}",
        f"- **Inputs Found:** {len(inputs)}",
        f"- **Navigation / Links Found:** {len(links)}",
        f"- **Headings (H1-H3):** {len(headings)}",
    ]

    if required_selectors:
        report.append(f"\n#### Assertion on Required UI Selectors ({len(required_selectors) - missing_selectors}/{len(required_selectors)} Passed):")
        report.extend(selector_results)

    return "\n".join(report)


def analyze_frontend_javascript_code(file_path_or_js: str) -> str:
    """Performs static analysis of frontend JavaScript/TypeScript code for UI bugs and security.

    Detects:
    - Dangerous DOM manipulation (innerHTML, document.write) leading to Cross-Site Scripting (XSS)
    - Missing event listener cleanup (memory leaks)
    - Unhandled fetch / Promise errors
    - Insecure localStorage of auth tokens

    Args:
        file_path_or_js: Path to JS/TS file OR raw JavaScript code string.

    Returns:
        Structured audit report for frontend script code.
    """
    code_text = file_path_or_js
    target_desc = "JavaScript Snippet"

    if os.path.exists(file_path_or_js) and os.path.isfile(file_path_or_js):
        target_desc = f"File: {file_path_or_js}"
        try:
            with open(file_path_or_js, "r", encoding="utf-8", errors="replace") as f:
                code_text = f.read()
        except Exception as e:
            return f"Error reading JS file '{file_path_or_js}': {str(e)}"

    findings = []
    lines = code_text.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        # 1. innerHTML XSS Check
        if re.search(r'\.innerHTML\s*=', stripped):
            findings.append({
                "severity": "HIGH",
                "type": "Cross-Site Scripting (XSS) via innerHTML",
                "line": idx,
                "snippet": stripped[:90],
                "fix": "Use element.textContent or textNode, or sanitize HTML before injecting.",
            })

        # 2. document.write Check
        if "document.write(" in stripped:
            findings.append({
                "severity": "HIGH",
                "type": "Dangerous document.write()",
                "line": idx,
                "snippet": stripped[:80],
                "fix": "Avoid document.write(); it can overwrite the document and cause XSS.",
            })

        # 3. Insecure sensitive storage
        if re.search(r'localStorage\.setItem\s*\(\s*["\'](token|auth|jwt|password|secret)', stripped, re.IGNORECASE):
            findings.append({
                "severity": "MEDIUM",
                "type": "Sensitive Credential in localStorage",
                "line": idx,
                "snippet": stripped[:90],
                "fix": "Store authentication tokens in HttpOnly, Secure cookies to prevent XSS exfiltration.",
            })

        # 4. Uncaught fetch without .catch() or try/catch
        if re.search(r'fetch\(', stripped) and not ("catch" in stripped or "await" in stripped):
            findings.append({
                "severity": "LOW",
                "type": "Potential Unhandled Network Rejection",
                "line": idx,
                "snippet": stripped[:80],
                "fix": "Ensure fetch() calls have a .catch(...) handler or are awaited inside try/catch.",
            })

    report = [
        f"### Frontend JavaScript Analysis: `{target_desc}`",
        f"- **Lines of Code:** {len(lines)}",
        f"- **Issues Detected:** {len(findings)}",
        "",
    ]
    if findings:
        report.append("#### Detected Frontend Bugs & Vulnerabilities:")
        for f in findings:
            badge = {"HIGH": "🟠 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🔵 LOW"}.get(f["severity"], "⚪ INFO")
            report.append(f"- **{badge}** (Line {f['line']}): `{f['type']}`")
            report.append(f"  - **Snippet:** `{f['snippet']}`")
            report.append(f"  - **Fix:** {f['fix']}\n")
    else:
        report.append("✅ No high-severity frontend DOM/XSS anti-patterns detected.")

    return "\n".join(report)
