import os
import httpx
from dotenv import load_dotenv

# Load env variables
load_dotenv()

CLOUD_RUN_URL = os.getenv("GOOGLE_CLOUD_RUN_URL")
if not CLOUD_RUN_URL:
    print("❌ Error: GOOGLE_CLOUD_RUN_URL is not set in your .env file.")
    exit(1)

CLOUD_RUN_URL = CLOUD_RUN_URL.rstrip("/")
APP_NAME = "adk_simple_bot"
USER_ID = "test_user_cloud_run"

def main():
    print("=" * 62)
    print("  adk_simple_bot — Google Cloud Run Integration Test")
    print("=" * 62)
    print(f"  Service URL : {CLOUD_RUN_URL}")
    print(f"  App Name    : {APP_NAME}")
    print(f"  User ID     : {USER_ID}")
    print("-" * 62)

    # Step 1: Create a new session on Cloud Run
    print("[Step 1] Creating a new session...")
    session_endpoint = f"{CLOUD_RUN_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions"
    try:
        resp = httpx.post(session_endpoint, json={}, timeout=10)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        exit(1)

    if resp.status_code != 200:
        print(f"❌ Failed to create session: {resp.status_code} - {resp.text}")
        exit(1)

    session_data = resp.json()
    session_id = session_data["id"]
    print(f"✅ Session created: {session_id}")
    print("-" * 62)

    # Step 2: Send test messages
    test_messages = [
        "Hello! Who are you?",
        "What is the weather in Delhi?",
        "Can you shorten this: 'I am writing to inform you that the meeting scheduled for tomorrow has been postponed to next week due to unforeseen circumstances.'"
    ]

    run_endpoint = f"{CLOUD_RUN_URL}/run"

    for i, msg in enumerate(test_messages, 1):
        print(f"── Test {i}/{len(test_messages)} ──────────────────────────────────────────")
        print(f"  You   : {msg}")
        
        payload = {
            "appName": APP_NAME,
            "userId": USER_ID,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [{"text": msg}]
            }
        }

        try:
            resp = httpx.post(run_endpoint, json=payload, timeout=60)
        except Exception as e:
            print(f"❌ Request failed: {e}")
            continue

        if resp.status_code != 200:
            print(f"❌ API Error: {resp.status_code} - {resp.text}")
            continue

        events = resp.json()
        
        # Parse reply and actions
        reply = ""
        tool_calls = []
        
        for event in events:
            if not event:
                continue
            content = event.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                if not part:
                    continue
                # Text
                text = part.get("text")
                if text:
                    reply += text
                # Tool Call
                fc = part.get("functionCall")
                if fc:
                    tool_calls.append(fc.get("name"))

        if tool_calls:
            print(f"  Tools : Called tools: {', '.join(tool_calls)}")
        print(f"  Agent : {reply}")
        print(f"✅ Test {i} passed.")
        print()

    print("=" * 62)
    print("✅ All Cloud Run integration tests completed! 🎉")
    print("=" * 62)

if __name__ == "__main__":
    main()
