# Google ADK: Memory Architecture Guide (Short-Term vs. Long-Term Memory)

This document provides a comprehensive overview of how memory works in Google's **Agent Development Kit (ADK)**, covering multi-turn conversation handling, short-term sessions, and cross-session long-term memory.

---

## 1. The Two-Tier Memory Architecture

In Google ADK, memory and conversational state management are split into a clean, two-tier architecture:

| Dimension | Short-Term Memory (`SessionService`) | Long-Term Memory (`MemoryService`) |
| :--- | :--- | :--- |
| **Primary Purpose** | Maintains context within an active conversation thread. | Recalls user facts, preferences, and knowledge across different sessions. |
| **Scope** | Single conversation thread bound to a `session_id`. | Cross-session / persistent user profile. |
| **Default Status** | **Enabled by default** (handled via `Session`). | **Disabled by default** (requires explicit service & tool setup). |
| **Storage Units** | Chronological **Events** (prompts, tool calls, replies) & temporary `session.state`. | Vectorized **MemoryEntry** items (distilled facts, summaries, knowledge). |
| **Lifecycle** | Transient (session duration). | Permanent (persists indefinitely until deleted). |
| **Example Backends** | `InMemorySessionService`, `VertexAiSessionService`, `DatabaseSessionService` (Firestore/SQLite). | `VertexAiMemoryBankService`, `InMemoryMemoryService`. |

---

## 2. Short-Term Memory: Multi-Turn Conversations

### How It Works
When you ask an agent a follow-up question (e.g., *"What is the weather in Mumbai?"* followed by *"What about Delhi?"*), the agent remembers the context because of **ADK Sessions**:
1. Every interaction turn is recorded as a structured **`Event`** within the session.
2. When the user sends a subsequent query with the **same `session_id`**, ADK automatically retrieves earlier events from the session.
3. The previous turns are injected into the model's conversation history before generating a response.

### The Role of `session_id`
* **Preserving Context:** For follow-ups to work, the client application (FastAPI server, CLI runner, or frontend) **must pass the same `session_id`** on each subsequent call.
* **Stateless Traps:** If a request is sent without a `session_id` (or if the client generates a new ID on every message), each turn is treated as a brand new conversation with zero context.

### Behavior Across Deployment Environments
* **Vertex AI Agent Engine (Managed Platform):**
  * Fully managed, built-in session persistence.
  * Sessions and event histories are automatically stored in Google Cloud and survive container restarts.
* **Local Development (`InMemorySessionService`):**
  * Stored in process memory.
  * Multi-turn works during the active run, but restarting the Python process clears all sessions.
* **Google Cloud Run:**
  * Cloud Run instances are stateless and scale to zero when idle.
  * In-memory sessions reset upon instance restart or when routed to different container replicas.
  * **Production Recommendation:** Connect Cloud Run to **Google Cloud Firestore** using `DatabaseSessionService` to persist session events across restarts.

---

## 3. Long-Term Memory: Cross-Session Recall

### Why Isn't Long-Term Memory On by Default?
Unlike short-term conversation context, long-term memory involves:
* Distilling raw chat history into structured knowledge or embeddings.
* Storing embeddings in a vector database or managed memory bank.
* Extra inference and storage costs for background fact extraction.

Consequently, Google ADK requires developers to explicitly opt in to long-term memory.

### Key ADK Components for Long-Term Memory

1. **`MemoryService`:**
   * Manages extraction, vectorization, and searching of historical facts.
   * **`VertexAiMemoryBankService`**: Connects directly to Google Cloud Vertex AI Memory Bank for managed memory extraction and semantic retrieval.
   * **`InMemoryMemoryService`**: Used for testing/prototyping memory workflows in memory.

2. **Ingestion Operations:**
   * `add_session_to_memory`: Takes a completed session, extracts key facts, and saves them to the long-term knowledge base.
   * `add_events_to_memory`: Appends a delta of recent events directly into long-term memory.

3. **Retrieval Tools:**
   * **`preload_memory` (`PreloadMemoryTool`)**: Automatically searches past memories matching the user's current query and injects relevant historical facts into the model's dynamic system instructions before every call.
   * **`load_memory` (`LoadMemoryTool`)**: An explicit function tool that the LLM can call on-demand when it realizes it needs to search past information about the user.

---

## 4. Code Examples

### A. How Multi-Turn (Short-Term) Memory is Queried in Code
```python
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from adk_simple_bot.agent import root_agent

session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name="adk_simple_bot", session_service=session_service)

# 1. Create a session for the user
session = await session_service.create_session(app_name="adk_simple_bot", user_id="user_123")

# Turn 1
msg1 = types.Content(role="user", parts=[types.Part.from_text(text="What is the weather in Mumbai?")])
async for event in runner.run_async(user_id="user_123", session_id=session.id, new_message=msg1):
    pass

# Turn 2: Follow-up question using the SAME session_id (agent remembers Turn 1)
msg2 = types.Content(role="user", parts=[types.Part.from_text(text="What about Delhi?")])
async for event in runner.run_async(user_id="user_123", session_id=session.id, new_message=msg2):
    pass
```

### B. Configuring Long-Term Memory Tools (Conceptual)
```python
from google.adk import Agent
from google.adk.tools import google_search, preload_memory
from google.genai import types
from adk_simple_bot.tools import get_weather

root_agent = Agent(
    name="adk_simple_bot",
    model="gemini-3.1-flash-lite",
    instruction="You are a helpful assistant.",
    # Adding preload_memory automatically injects relevant past session facts:
    tools=[get_weather, google_search, preload_memory],
    generate_content_config=types.GenerateContentConfig(
        tool_config=types.ToolConfig(include_server_side_tool_invocations=True)
    ),
)
```

---

## 5. Summary Checklist

* **Multi-Turn Follow-Ups:** Work out of the box using Google ADK's built-in `Session` handling.
* **Client Implementation:** Ensure your frontend or API proxy stores and forwards the `session_id` on all subsequent user turns.
* **Long-Term Memory:** Add an ADK `MemoryService` and the `preload_memory` or `load_memory` tool if you need cross-session user recall.
