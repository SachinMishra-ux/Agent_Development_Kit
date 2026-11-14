"""API and Microservice Testing Tool for Software Testing Agent.

Performs HTTP/REST endpoint probing, response assertion, latency benchmarking,
and payload validation.
"""

import json
import time
from typing import Dict, Optional
import requests


def test_http_endpoint(
    url: str,
    method: str = "GET",
    headers_json: str = "{}",
    payload_json: str = "{}",
    expected_status: int = 200,
    timeout_seconds: float = 10.0,
) -> str:
    """Tests an HTTP/REST endpoint by sending a request and asserting the response and latency.

    Args:
        url: Full URL to target (e.g. 'http://localhost:8000/api/users' or 'https://httpbin.org/get').
        method: HTTP method: 'GET', 'POST', 'PUT', 'DELETE', 'PATCH', or 'HEAD'.
        headers_json: JSON string of HTTP headers to send (e.g. '{"Authorization": "Bearer token"}').
        payload_json: JSON string of request body payload for POST/PUT/PATCH requests.
        expected_status: Expected HTTP status code (e.g. 200, 201, 204, 400, 404).
        timeout_seconds: Maximum request timeout in seconds.

    Returns:
        Structured test result containing status code, latency (ms), response body preview, and pass/fail verdict.
    """
    method = method.upper().strip()
    try:
        headers = json.loads(headers_json) if headers_json else {}
    except Exception as e:
        return f"Error: Invalid headers_json parameter: {str(e)}"

    payload = None
    if payload_json and payload_json.strip() and payload_json != "{}":
        try:
            payload = json.loads(payload_json)
        except Exception:
            payload = payload_json  # Fallback to raw string

    start_time = time.time()
    try:
        req_kwargs = {
            "headers": headers,
            "timeout": timeout_seconds,
        }
        if method in ["POST", "PUT", "PATCH"]:
            if isinstance(payload, dict):
                req_kwargs["json"] = payload
            else:
                req_kwargs["data"] = payload

        resp = requests.request(method, url, **req_kwargs)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        status_code = resp.status_code

        # Evaluate assertion
        is_passed = (status_code == expected_status)
        verdict_str = "✅ PASSED" if is_passed else "❌ FAILED (Status Mismatch)"

        # Parse body preview
        try:
            body_json = resp.json()
            body_formatted = json.dumps(body_json, indent=2)
            is_json = True
        except Exception:
            body_formatted = resp.text[:1500]
            is_json = False

        res_lines = [
            f"### API Test Result: {verdict_str}",
            f"- **Target URL:** `{method} {url}`",
            f"- **Expected Status:** `{expected_status}`",
            f"- **Actual Status:** `{status_code} ({resp.reason})`",
            f"- **Latency (RTT):** `{latency_ms} ms`",
            f"- **Content-Type:** `{resp.headers.get('content-type', 'N/A')}`",
            f"- **Response Size:** `{len(resp.content)} bytes`",
            "",
            "#### Response Body Preview:",
            f"```{ 'json' if is_json else 'text' }",
            body_formatted[:2500],
            "```",
        ]

        if not is_passed:
            res_lines.append(
                f"\n> [!WARNING] Expected status `{expected_status}`, but server returned `{status_code}`."
            )

        # Performance advisory
        if latency_ms > 1500:
            res_lines.append(f"\n> [!NOTE] High latency warning: response time was {latency_ms} ms (> 1500 ms threshold).")

        return "\n".join(res_lines)

    except requests.exceptions.Timeout:
        return f"❌ Error: Request to {url} timed out after {timeout_seconds}s."
    except requests.exceptions.ConnectionError as e:
        return f"❌ Error: Failed to connect to {url}. Connection refused or host unreachable. Details: {str(e)}"
    except Exception as e:
        return f"❌ Error while testing API {url}: {str(e)}"


def check_service_health(base_url: str) -> str:
    """Performs an automated health check against common service endpoints.

    Args:
        base_url: Base URL of the service (e.g. 'http://localhost:8080' or 'https://api.github.com').

    Returns:
        Summary of probed health endpoints (/health, /healthz, /status, /ping, /).
    """
    base = base_url.rstrip("/")
    probe_paths = ["/health", "/healthz", "/status", "/ping", "/"]
    results = []

    for path in probe_paths:
        target = f"{base}{path}"
        try:
            t0 = time.time()
            resp = requests.get(target, timeout=3.0)
            latency = round((time.time() - t0) * 1000, 1)
            results.append(f"- `{path}`: Status **{resp.status_code}** ({resp.reason}) - {latency}ms")
        except Exception:
            results.append(f"- `{path}`: ❌ Unreachable / Connection error")

    return f"### Health Check Summary for `{base}`\n" + "\n".join(results)
