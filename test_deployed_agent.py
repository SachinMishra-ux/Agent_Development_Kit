"""
Test script for adk_simple_bot deployed on Vertex AI Agent Engine.

Run with:
    uv run python test_deployed_agent.py
"""

import os
import vertexai
from google.protobuf.json_format import MessageToDict
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

# ── Load Environment Variables ────────────────────────────────────────────────
load_dotenv(override=True)

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ID    = os.getenv("GOOGLE_CLOUD_PROJECT")
PROJECT_NUM   = os.getenv("GOOGLE_CLOUD_PROJECT_NUM")
LOCATION      = os.getenv("GOOGLE_CLOUD_LOCATION")
ENGINE_ID     = os.getenv("GOOGLE_CLOUD_ENGINE_ID")
RESOURCE_NAME = f"projects/{PROJECT_NUM}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"

# ── Test messages ─────────────────────────────────────────────────────────────
TEST_MESSAGES = [
    "Hello! What can you help me with?",
    "What is the weather in Mumbai?",
    "What is the weather in Delhi?",
    (
        "Can you shorten this: 'I am writing to inform you that the meeting "
        "scheduled for tomorrow has been postponed to next week due to "
        "unforeseen circumstances.'"
    ),
]

# ── Terminal colours ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def banner(text):
    print(f"\n{BOLD}{BLUE}{'─' * 62}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'─' * 62}{RESET}")

def step(n, text): print(f"\n{YELLOW}[Step {n}]{RESET} {text}")
def ok(text):      print(f"{GREEN}✅  {text}{RESET}")
def warn(text):    print(f"{YELLOW}⚠️   {text}{RESET}")
def fail(text):    print(f"{RED}❌  {text}{RESET}")


def extract_text_from_response(response) -> str:
    """
    Convert the QueryReasoningEngineResponse protobuf into plain text.
    output is a list of event dicts, each with:
      - content.parts[].text  → the agent's reply text
      - error_message         → any error string
    """
    try:
        data   = MessageToDict(response._pb)
        events = data.get("output", [])          # list of event dicts
        texts  = []
        for event in events:
            # Surface errors immediately
            err = event.get("error_message", "")
            if err:
                return f"[ERROR] {err}"
            # Extract text parts
            parts = event.get("content", {}).get("parts", [])
            for part in parts:
                text = part.get("text", "")
                if text:
                    texts.append(text)
        return "".join(texts)
    except Exception as e:
        return f"[parse error: {e}]"


def main():
    banner("adk_simple_bot — Vertex AI Agent Engine Test")
    print(f"  Project  : {PROJECT_ID}")
    print(f"  Location : {LOCATION}")
    print(f"  Engine ID: {ENGINE_ID}")
    print(f"  Resource : {RESOURCE_NAME}")

    # ── Step 1: Initialise Vertex AI ──────────────────────────────────────────
    step(1, "Initialising Vertex AI client...")
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        ok("Vertex AI initialised.")
    except Exception as e:
        fail(f"Could not initialise Vertex AI: {e}")
        return

    # ── Step 2: Connect to the deployed agent ─────────────────────────────────
    step(2, "Connecting to deployed Agent Engine...")
    try:
        agent = reasoning_engines.ReasoningEngine(RESOURCE_NAME)
        ok(f"Connected to Agent Engine: {ENGINE_ID}")
    except Exception as e:
        fail(f"Could not connect: {e}")
        return

    # ── Step 3: Create a session ──────────────────────────────────────────────
    step(3, "Creating a new session...")
    try:
        session    = agent.create_session(user_id="test_user_001")
        session_id = session["id"]
        ok(f"Session created: {session_id}")
    except Exception as e:
        fail(f"Could not create session: {e}")
        return

    # ── Step 4: Send test messages ────────────────────────────────────────────
    step(4, f"Sending {len(TEST_MESSAGES)} test messages...\n")

    passed = 0
    for i, message in enumerate(TEST_MESSAGES, 1):
        print(f"{BOLD}── Test {i}/{len(TEST_MESSAGES)} {'─' * 42}{RESET}")
        print(f"\n{BOLD}  You   :{RESET} {message}")

        try:
            response = agent.execution_api_client.query_reasoning_engine(
                request={
                    "name": RESOURCE_NAME,
                    "class_method": "stream_query",
                    "input": {
                        "message":    message,
                        "user_id":    "test_user_001",
                        "session_id": session_id,
                    },
                }
            )

            text = extract_text_from_response(response)

            if text.startswith("[ERROR]"):
                fail(f"Agent returned an error:")
                print(f"  {RED}{text}{RESET}")
            elif text.strip():
                print(f"{GREEN}{BOLD}  Agent :{RESET} {text.strip()}")
                ok(f"Test {i} passed.")
                passed += 1
            else:
                warn(f"Test {i} — agent returned an empty response.")

        except Exception as e:
            fail(f"Test {i} failed with exception: {e}")

    # ── Step 5: Summary ───────────────────────────────────────────────────────
    banner("Test Summary")
    if passed == len(TEST_MESSAGES):
        ok(f"All {passed}/{len(TEST_MESSAGES)} tests passed! 🎉")
    else:
        warn(f"{passed}/{len(TEST_MESSAGES)} tests passed.")

    print(f"\n  Session ID  : {session_id}")
    print(f"  Playground  : https://console.cloud.google.com/vertex-ai/agents/"
          f"agent-engines/locations/{LOCATION}/agent-engines/{ENGINE_ID}/"
          f"playground?project={PROJECT_NUM}")
    print()


if __name__ == "__main__":
    main()
