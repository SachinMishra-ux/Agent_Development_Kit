import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

# ── Load environment variables (from parent directory or workspace root) ──────
load_dotenv(dotenv_path="../.env")
load_dotenv() # Fallback

# Logger setup
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("adk_cloud_run_api")

# Read configurations
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "adk-bot-secret-key-change-me")
CLOUD_RUN_URL = os.getenv("GOOGLE_CLOUD_RUN_URL")

if not CLOUD_RUN_URL:
    raise ValueError("Missing GOOGLE_CLOUD_RUN_URL in .env file.")

# Normalize Cloud Run URL
CLOUD_RUN_URL = CLOUD_RUN_URL.rstrip("/")

APP_NAME = "adk_simple_bot"

# ── FastAPI Application Setup ─────────────────────────────────────────────────
app = FastAPI(
    title="ADK Cloud Run Secure Proxy Server",
    description="A secure gateway wrapper for ADK Agent deployed on Google Cloud Run.",
    version="1.0.0"
)

# Enable CORS for local web interface testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Authentication Setup
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != API_SECRET_KEY:
        log.warning("Unauthorized access attempt detected.")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Please provide a valid X-API-Key header."
        )
    return api_key


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., example="user_001")


class ChatRequest(BaseModel):
    user_id:    str  = Field(..., example="user_001")
    session_id: Optional[str] = Field(None, example="1234567890")
    message:    str  = Field(..., example="What is the weather in Delhi?")


class SessionResponse(BaseModel):
    session_id: str
    user_id:    str


class ChatResponse(BaseModel):
    session_id: str
    user_id:    str
    message:    str
    reply:      str
    tool_calls: list = []


# ── Helper Methods ────────────────────────────────────────────────────────────
async def create_cloud_run_session(user_id: str) -> str:
    """Helper method to explicitly create a session in the Cloud Run database."""
    session_endpoint = f"{CLOUD_RUN_URL}/apps/{APP_NAME}/users/{user_id}/sessions"
    log.info(f"Creating session on Cloud Run for user {user_id}...")
    
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(session_endpoint, json={})
        
    if resp.status_code != 200:
        log.error(f"Failed to create session in Cloud Run: {resp.status_code} {resp.text}")
        raise HTTPException(status_code=resp.status_code, detail=f"Cloud Run session error: {resp.text}")
        
    session_data = resp.json()
    session_id = session_data.get("id")
    if not session_id:
        raise HTTPException(status_code=500, detail="Cloud Run session creation returned no ID.")
    
    log.info(f"Successfully created Cloud Run session: {session_id}")
    return session_id


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Public health status check."""
    return {
        "status": "ok",
        "agent": APP_NAME,
        "cloud_run_url": CLOUD_RUN_URL
    }


@app.get("/config")
def get_config():
    """Public endpoint to fetch frontend dev config (e.g. discovery of API Key)."""
    return {
        "api_key": API_SECRET_KEY,
        "mode": "cloud_run"
    }


@app.post("/sessions", response_model=SessionResponse, dependencies=[Depends(verify_api_key)])
async def create_session(body: CreateSessionRequest):
    """Creates a new stateful session on Cloud Run and returns the session ID."""
    session_id = await create_cloud_run_session(body.user_id)
    return SessionResponse(session_id=session_id, user_id=body.user_id)


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(body: ChatRequest):
    """Synchronous chat endpoint routing queries to Cloud Run /run."""
    session_id = body.session_id
    
    # Auto-create session if not provided by client
    if not session_id:
        session_id = await create_cloud_run_session(body.user_id)
        
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
    
    log.info(f"Sending sync query to Cloud Run for session {session_id}...")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(run_url, json=payload)
        
    if resp.status_code != 200:
        log.error(f"Cloud Run run failed: {resp.status_code} {resp.text}")
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
                
            # 1. Text chunk
            text = part.get("text")
            if text:
                reply_texts.append(text)
                
            # 2. Tool Function Call
            fc = part.get("functionCall")
            if fc:
                current_call = {
                    "name": fc.get("name"),
                    "args": fc.get("args"),
                    "id": fc.get("id"),
                    "response": None
                }
                tool_calls.append(current_call)
                
            # 3. Tool Function Response
            fr = part.get("functionResponse")
            if fr:
                if current_call and current_call.get("id") == fr.get("id"):
                    current_call["response"] = fr.get("response")
                else:
                    for tc in reversed(tool_calls):
                        if tc.get("name") == fr.get("name") and tc.get("response") is None:
                            tc["response"] = fr.get("response")
                            break
                            
    reply = "".join(reply_texts)
    return ChatResponse(
        session_id=session_id,
        user_id=body.user_id,
        message=body.message,
        reply=reply,
        tool_calls=tool_calls
    )


@app.post("/chat/stream", dependencies=[Depends(verify_api_key)])
async def chat_stream(body: ChatRequest):
    """Server-Sent Events (SSE) streaming chat endpoint routing queries to Cloud Run /run_sse."""
    
    async def sse_generator():
        session_id = body.session_id
        
        # Auto-create session if not provided by client
        if not session_id:
            try:
                session_id = await create_cloud_run_session(body.user_id)
                # Notify frontend of dynamic session ID
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
        
        log.info(f"Opening SSE connection to Cloud Run for session {session_id}...")
        
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", run_sse_url, json=payload) as response:
                if response.status_code != 200:
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Cloud Run stream error: {response.status_code}'})}\n\n"
                    return
                    
                async for raw_line in response.aiter_lines():
                    if not raw_line:
                        continue
                        
                    # Remove 'data: ' prefix if present
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
                            
                        # 1. Plain text chunk
                        text = part.get("text")
                        if text:
                            yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"
                            
                        # 2. Tool Function Call
                        fc = part.get("functionCall")
                        if fc:
                            yield f"data: {json.dumps({
                                'type': 'tool_call',
                                'name': fc.get('name'),
                                'args': fc.get('args'),
                                'id': fc.get('id')
                            })}\n\n"
                            
                        # 3. Tool Function Response
                        fr = part.get("functionResponse")
                        if fr:
                            yield f"data: {json.dumps({
                                'type': 'tool_response',
                                'name': fr.get('name'),
                                'response': fr.get('response'),
                                'id': fr.get('id')
                            })}\n\n"
                            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    # Defaulting local port to 8081 for Cloud Run secure gateway proxy
    uvicorn.run(app, host="0.0.0.0", port=8081)
