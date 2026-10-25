"""
Secure FastAPI proxy server for adk_simple_bot on Google Cloud Run (and Vertex AI Agent Engine).

Features:
  - API Key authentication on every endpoint (X-API-Key header)
  - CORS configured for frontend consumption
  - POST /sessions          → create a new session
  - GET  /sessions/{id}     → get session details
  - DELETE /sessions/{id}   → delete a session
  - POST /chat              → send a message, get full response (JSON)
  - POST /chat/stream       → send a message, get streamed response (SSE)

Run with:
    uv run uvicorn api_server:app --host 0.0.0.0 --port 8080 --reload

Environment variables (in .env):
    API_SECRET_KEY        → your chosen API key that clients must send
    GOOGLE_CLOUD_RUN_URL  → Cloud Run deployed service URL (preferred)
    GOOGLE_CLOUD_PROJECT  → GCP project ID (optional, falls back to hardcoded)
    GOOGLE_CLOUD_LOCATION → GCP region    (optional, falls back to hardcoded)
"""

import os
import json
import logging
from typing import AsyncGenerator, Optional

import httpx
import google.auth
import google.auth.transport.requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv(override=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("adk_api")

# ── Cloud Run / Vertex AI Config ──────────────────────────────────────────────
CLOUD_RUN_URL = os.getenv("GOOGLE_CLOUD_RUN_URL", "").rstrip("/")
APP_NAME      = "adk_simple_bot"

PROJECT_ID  = os.getenv("GOOGLE_CLOUD_PROJECT",  "email-copilotmy-project-20497")
LOCATION    = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
ENGINE_ID   = os.getenv("GOOGLE_CLOUD_ENGINE_ID", "7211680823664181248")

QUERY_URL = (
    f"https://{LOCATION}-aiplatform.googleapis.com/v1"
    f"/projects/{PROJECT_ID}/locations/{LOCATION}"
    f"/reasoningEngines/{ENGINE_ID}:query"
)

STREAM_QUERY_URL = (
    f"https://{LOCATION}-aiplatform.googleapis.com/v1"
    f"/projects/{PROJECT_ID}/locations/{LOCATION}"
    f"/reasoningEngines/{ENGINE_ID}:streamQuery?alt=sse"
)

# ── API Key security ──────────────────────────────────────────────────────────
API_SECRET_KEY   = os.getenv("API_SECRET_KEY", "adk-bot-secret-key-change-me")
API_KEY_HEADER   = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Dependency — rejects any request that does not carry the correct API key."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide it in the 'X-API-Key' header.",
        )
    if api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )
    return api_key


# ── Google auth helper ────────────────────────────────────────────────────────
_gcp_credentials = None
_gcp_auth_request = google.auth.transport.requests.Request()


def get_google_access_token() -> str:
    """Returns a fresh Bearer token from Application Default Credentials."""
    global _gcp_credentials
    if _gcp_credentials is None:
        _gcp_credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    if not _gcp_credentials.valid:
        _gcp_credentials.refresh(_gcp_auth_request)
    return _gcp_credentials.token


def gcp_headers() -> dict:
    """Build headers required by Vertex AI REST API."""
    return {
        "Authorization": f"Bearer {get_google_access_token()}",
        "Content-Type": "application/json",
    }


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., example="user_001", description="Unique user identifier")


class ChatRequest(BaseModel):
    user_id:    str  = Field(..., example="user_001")
    session_id: Optional[str] = Field(None, example="1234567890")
    message:    str  = Field(..., example="What is the weather in Delhi?")


class SessionResponse(BaseModel):
    session_id: str
    user_id:    str


class ChatResponse(BaseModel):
    session_id: Optional[str] = None
    user_id:    str
    message:    str
    reply:      str
    tool_calls: list = []


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="adk_simple_bot API",
    description=(
        "Secure proxy API for the adk_simple_bot deployed on "
        "Google Cloud Run / Vertex AI Agent Engine. "
        "All protected endpoints require an `X-API-Key` header."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow all origins for frontend consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health & Config ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    """Public health-check endpoint."""
    return {
        "status": "ok",
        "agent": APP_NAME,
        "backend": "cloud_run" if CLOUD_RUN_URL else "vertex_ai",
        "cloud_run_url": CLOUD_RUN_URL or None,
        "project": PROJECT_ID,
        "region": LOCATION,
    }


@app.get("/config", tags=["Config"])
async def get_config():
    """Public config endpoint to share API Key with local frontend automatically."""
    return {
        "api_key": API_SECRET_KEY,
        "mode": "cloud_run" if CLOUD_RUN_URL else "vertex_ai",
        "cloud_run_url": CLOUD_RUN_URL or None,
    }


# ── Helper for Cloud Run Session ──────────────────────────────────────────────
async def _create_cloud_run_session(user_id: str) -> str:
    session_endpoint = f"{CLOUD_RUN_URL}/apps/{APP_NAME}/users/{user_id}/sessions"
    log.info("Creating session on Cloud Run for user %s: %s", user_id, session_endpoint)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(session_endpoint, json={})
    if resp.status_code != 200:
        log.error("Cloud Run create session failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    session_id = data.get("id")
    if not session_id:
        raise HTTPException(status_code=500, detail="Cloud Run session returned no ID.")
    return session_id


# ══════════════════════════════════════════════════════════════════════════════
# SESSION ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/sessions",
    response_model=SessionResponse,
    tags=["Sessions"],
    summary="Create a new session",
    dependencies=[Depends(verify_api_key)],
)
async def create_session(body: CreateSessionRequest):
    """Creates a new stateful session."""
    if CLOUD_RUN_URL:
        session_id = await _create_cloud_run_session(body.user_id)
        log.info("Cloud Run session created: %s for user: %s", session_id, body.user_id)
        return SessionResponse(session_id=session_id, user_id=body.user_id)

    # Fallback to Vertex AI Agent Engine
    payload = {"class_method": "create_session", "input": {"user_id": body.user_id}}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(QUERY_URL, headers=gcp_headers(), json=payload)
    if resp.status_code != 200:
        log.error("create_session failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    output = data.get("output", {})
    session_id = output.get("id") or output.get("name", "").split("/")[-1]
    return SessionResponse(session_id=session_id, user_id=body.user_id)


@app.get(
    "/sessions/{session_id}",
    tags=["Sessions"],
    summary="Get session details",
    dependencies=[Depends(verify_api_key)],
)
async def get_session(session_id: str, user_id: str):
    """Fetch details of an existing session."""
    if CLOUD_RUN_URL:
        url = f"{CLOUD_RUN_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()

    payload = {
        "class_method": "get_session",
        "input": {"user_id": user_id, "session_id": session_id},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(QUERY_URL, headers=gcp_headers(), json=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json().get("output", {})


@app.delete(
    "/sessions/{session_id}",
    tags=["Sessions"],
    summary="Delete a session",
    dependencies=[Depends(verify_api_key)],
)
async def delete_session(session_id: str, user_id: str):
    """Delete an existing session."""
    if CLOUD_RUN_URL:
        url = f"{CLOUD_RUN_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return {"detail": f"Session {session_id} deleted successfully."}

    payload = {
        "class_method": "delete_session",
        "input": {"user_id": user_id, "session_id": session_id},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(QUERY_URL, headers=gcp_headers(), json=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"detail": f"Session {session_id} deleted successfully."}


# ══════════════════════════════════════════════════════════════════════════════
# CHAT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Send a message — full JSON response",
    dependencies=[Depends(verify_api_key)],
)
async def chat(body: ChatRequest):
    """Sends a message to the agent and waits for the complete reply."""
    session_id = body.session_id

    # ── Cloud Run flow ──
    if CLOUD_RUN_URL:
        if not session_id:
            session_id = await _create_cloud_run_session(body.user_id)

        run_url = f"{CLOUD_RUN_URL}/run"
        payload = {
            "appName": APP_NAME,
            "userId": body.user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [{"text": body.message}]
            }
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(run_url, json=payload)

        if resp.status_code != 200:
            log.error("Cloud Run /run error: %s %s", resp.status_code, resp.text)
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        events = resp.json()
        reply_texts = []
        tool_calls = []
        current_call = None

        for event in events:
            if not event:
                continue
            content = event.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                if not part:
                    continue
                # Plain text
                text = part.get("text")
                if text:
                    reply_texts.append(text)
                # Tool Function Call
                fc = part.get("functionCall") or part.get("function_call")
                if fc:
                    current_call = {
                        "name": fc.get("name"),
                        "args": fc.get("args"),
                        "id": fc.get("id"),
                        "response": None
                    }
                    tool_calls.append(current_call)
                # Tool Function Response
                fr = part.get("functionResponse") or part.get("function_response")
                if fr:
                    if current_call and current_call.get("id") == fr.get("id"):
                        current_call["response"] = fr.get("response")
                    else:
                        for tc in reversed(tool_calls):
                            if tc.get("name") == fr.get("name") and tc.get("response") is None:
                                tc["response"] = fr.get("response")
                                break

        reply = "".join(reply_texts).strip()
        return ChatResponse(
            session_id=session_id,
            user_id=body.user_id,
            message=body.message,
            reply=reply,
            tool_calls=tool_calls
        )

    # ── Vertex AI Agent Engine flow (legacy) ──
    payload = {
        "class_method": "stream_query",
        "input": {
            "message":    body.message,
            "user_id":    body.user_id,
            "session_id": body.session_id,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(QUERY_URL, headers=gcp_headers(), json=payload)

    if resp.status_code != 200:
        log.error("chat failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data   = resp.json()
    events = data.get("output", [])
    texts = []
    tool_calls = []
    current_call = None

    for event in events:
        if not event:
            continue
        err = event.get("error_message", "")
        if err:
            raise HTTPException(status_code=500, detail=f"Agent error: {err}")
        content = event.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            if not part:
                continue
            text = part.get("text", "")
            if text:
                texts.append(text)
            fc = part.get("function_call", {})
            if fc:
                current_call = {
                    "name": fc.get("name"),
                    "args": fc.get("args"),
                    "id": fc.get("id"),
                    "response": None
                }
                tool_calls.append(current_call)
            fr = part.get("function_response", {})
            if fr:
                if current_call and current_call.get("id") == fr.get("id"):
                    current_call["response"] = fr.get("response")
                else:
                    for tc in reversed(tool_calls):
                        if tc.get("name") == fr.get("name") and tc.get("response") is None:
                            tc["response"] = fr.get("response")
                            break

    reply = "".join(texts).strip()
    return ChatResponse(
        session_id=body.session_id,
        user_id=body.user_id,
        message=body.message,
        reply=reply,
        tool_calls=tool_calls
    )


@app.post(
    "/chat/stream",
    tags=["Chat"],
    summary="Send a message — Server-Sent Events (SSE) streaming response",
    dependencies=[Depends(verify_api_key)],
    response_class=StreamingResponse,
)
async def chat_stream(body: ChatRequest):
    """Sends a message to the agent and streams the response as Server-Sent Events (SSE)."""

    async def sse_generator() -> AsyncGenerator[str, None]:
        session_id = body.session_id

        # ── Cloud Run flow ──
        if CLOUD_RUN_URL:
            if not session_id:
                try:
                    session_id = await _create_cloud_run_session(body.user_id)
                    yield f"data: {json.dumps({'type': 'session_created', 'session_id': session_id})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Session creation failed: {str(e)}'})}\n\n"
                    return

            run_sse_url = f"{CLOUD_RUN_URL}/run_sse"
            payload = {
                "appName": APP_NAME,
                "userId": body.user_id,
                "sessionId": session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": body.message}]
                }
            }

            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    async with client.stream("POST", run_sse_url, json=payload) as response:
                        if response.status_code != 200:
                            yield f"data: {json.dumps({'type': 'error', 'content': f'Cloud Run stream error: {response.status_code}'})}\n\n"
                            return

                        async for raw_line in response.aiter_lines():
                            if not raw_line:
                                continue
                            raw = raw_line.strip()
                            if raw.startswith("data:"):
                                raw = raw[5:].strip()
                            if not raw:
                                continue
                            try:
                                event = json.loads(raw)
                            except json.JSONDecodeError:
                                continue

                            content = event.get("content") or {}
                            parts = content.get("parts") or []
                            for part in parts:
                                if not part:
                                    continue
                                text = part.get("text")
                                if text:
                                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"
                                fc = part.get("functionCall") or part.get("function_call")
                                if fc:
                                    yield f"data: {json.dumps({'type': 'tool_call', 'name': fc.get('name'), 'args': fc.get('args'), 'id': fc.get('id')})}\n\n"
                                fr = part.get("functionResponse") or part.get("function_response")
                                if fr:
                                    yield f"data: {json.dumps({'type': 'tool_response', 'name': fr.get('name'), 'response': fr.get('response'), 'id': fr.get('id')})}\n\n"

            except Exception as e:
                log.exception("Cloud Run SSE stream error")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            finally:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # ── Vertex AI Agent Engine flow (legacy) ──
        payload = {
            "class_method": "stream_query",
            "input": {
                "message":    body.message,
                "user_id":    body.user_id,
                "session_id": body.session_id,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", STREAM_QUERY_URL, headers=gcp_headers(), json=payload) as resp:
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        yield f"data: {json.dumps({'type': 'error', 'content': error_body.decode()})}\n\n"
                        return

                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        raw = line
                        if raw.startswith("data:"):
                            raw = raw[5:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        err = event.get("error_message", "")
                        if err:
                            yield f"data: {json.dumps({'type': 'error', 'content': err})}\n\n"
                            return

                        content = event.get("content") or {}
                        parts = content.get("parts") or []
                        for part in parts:
                            if not part:
                                continue
                            text = part.get("text", "")
                            if text:
                                yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"
                            fc = part.get("function_call", {})
                            if fc:
                                yield f"data: {json.dumps({'type': 'tool_call', 'name': fc.get('name'), 'args': fc.get('args'), 'id': fc.get('id')})}\n\n"
                            fr = part.get("function_response", {})
                            if fr:
                                yield f"data: {json.dumps({'type': 'tool_response', 'name': fr.get('name'), 'response': fr.get('response'), 'id': fr.get('id')})}\n\n"

        except Exception as e:
            log.exception("SSE stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8080, reload=True)
