# 🎙️ Podcast Agent (Google ADK)

A multi-speaker podcast generation agent built on the **Google Agent Development Kit (ADK)** using a collaborative subagent architecture, Human-in-the-Loop (HITL) approval, and neural multi-speaker MP3 audio synthesis.

---

## 1. Architecture & Subagent Workflow

The agent operates on Google ADK's **Collaborative Workflows** pattern with clear separation of responsibilities:

```
                                    ┌───────────────────────────┐
                                    │        User Input         │
                                    │  - Topic / File (PDF/Doc) │
                                    │  - 2 or 3 Speakers Choice │
                                    └─────────────┬─────────────┘
                                                  │
                                                  ▼
                                    ┌───────────────────────────┐
                                    │   Root Coordinator Agent  │
                                    │      (podcast_agent)      │
                                    │                           │
                                    │ • read_document           │
                                    │ • load_artifacts          │
                                    └─────────────┬─────────────┘
                                                  │
                      ┌───────────────────────────┼───────────────────────────┐
                      │ 1. Mandatory Research     │ 2. Scriptwriting          │ 3. Audio Synthesis
                      ▼                           ▼                           ▼
           ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
           │   research_agent    │     │  scriptwriter_agent │     │audio_producer_agent │
           │                     │     │                     │     │                     │
           │ • Tools:            │     │ • Tools: None       │     │ • Tools:            │
           │   google_search     │     │ • 2 or 3 Personas   │     │   generate_podcast_ │
           │ • Live web facts,   │     │ • Spoken dialogue   │     │   audio             │
           │   stats & debate    │     │ • Transfers back to │     │ • Neural Edge-TTS   │
           │   angles            │     │   coordinator       │     │ • Emits MP3 Session │
           │ • Transfers back to │     │                     │     │   Artifact          │
           │   coordinator       │     │                     │     │                     │
           └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### Components & Roles

1. **Root Coordinator Agent (`podcast_agent`)**:
   - Manages episode planning and user inputs.
   - Uses `read_document` to inspect uploaded files (PDFs, Word docs, text).
   - **Enforces the production pipeline**: delegates to `research_agent`, then to `scriptwriter_agent`, and finally to `audio_producer_agent`.
   - Surfaces final transcripts and points users to the generated audio in the **Artifacts tab**.
   - Handles Human-in-the-Loop (HITL) feedback and revision requests.

2. **Research Subagent (`research_agent`)**:
   - Equipped solely with `google_search` for real-time web grounding and factual verification.
   - Synthesizes findings into a structured briefing (key takeaways, debate angles, surprising data).
   - Transfers the completed research brief back to `podcast_agent`.

3. **Scriptwriter Subagent (`scriptwriter_agent`)**:
   - Focuses 100% on dialogue writing without any tool distraction.
   - Dynamically crafts spoken conversations tailored to the requested speaker count:
     - **2 Speakers**:
       * **Alex (Host)**: Inquisitive, charismatic narrator who frames questions.
       * **Morgan (Expert)**: Domain specialist who explains concepts with relatable analogies.
     - **3 Speakers**:
       * **Alex (Host)**: Moderator keeping time and guiding transitions.
       * **Morgan (Expert)**: Deep technical and factual authority.
       * **Taylor (Skeptic)**: Critical thinker who questions assumptions and plays devil's advocate.
   - Transfers the completed script turns back to `podcast_agent`.

4. **Audio Producer Subagent (`audio_producer_agent`)**:
   - Equipped with `generate_podcast_audio`.
   - Receives the approved dialogue turns and synthesizes the neural multi-speaker MP3 audio track.
   - Saves the final audio file directly into the **ADK Session Artifacts**, triggering the `artifact_delta` event so the audio appears in ADK Web.
   - Transfers confirmation back to `podcast_agent`.

---

## 2. Audio Generation Tool & Models

### Models & Tools Overview

| Component | Technology / Tool Used | Why It Was Chosen |
| :--- | :--- | :--- |
| **Reasoning & Planning** | Gemini 3.1 Flash Lite (`gemini-3.1-flash-lite`) | High-speed, cost-effective reasoning for outline planning and workflow orchestration. |
| **Web Research** | ADK Inbuilt `google_search` | Real-time factual grounding directly from Google Search. |
| **Document Ingestion** | Custom `read_document` tool (`pypdf`, `python-docx`) | Extracts text from uploaded session artifacts (PDFs, Word documents, text). |
| **Audio Production** | Custom `audio_producer_agent` via `generate_podcast_audio` (`edge-tts`) | High-fidelity Microsoft Neural TTS voices at **$0 extra cost** with zero external API key requirements. |

### Voice Personas (Neural Voices)

| Speaker | Persona | Assigned Neural Voice | Character Profile |
| :--- | :--- | :--- | :--- |
| **Alex** | Primary Host | `en-US-GuyNeural` | Warm, energetic, clear American male voice. |
| **Morgan** | Expert Guest | `en-US-JennyNeural` | Articulate, insightful, friendly American female voice. |
| **Taylor** | Skeptic / 3rd Host | `en-GB-RyanNeural` | Sharp, expressive, engaging British male voice. |

---

## 3. Human-in-the-Loop (HITL) Workflow

The system provides conversational script review and feedback:
1. Once the audio producer finishes generating the MP3, the coordinator prints the full dialogue in the chat and alerts the user to the **Artifacts tab**.
2. The user can request revisions:
   > *"Make Morgan sound more casual, and let Taylor challenge the timeline in turn 4."*
3. The coordinator passes the feedback back to `scriptwriter_agent` to update the script, and then to `audio_producer_agent` to re-synthesize the updated audio track.

---

## 4. Directory Structure

```text
podcast_agent/
├── __init__.py               # Exports root_agent for ADK CLI & runner
├── agent.py                  # Coordinator agent definition (podcast_agent)
├── prompt.py                 # System instructions for coordinator and subagents
├── schemas.py                # Pydantic schemas (DialogueTurn, PodcastScript, etc.)
├── README.md                 # System documentation & usage guide
├── subagents/
│   ├── __init__.py           # Exports research_agent, scriptwriter_agent, audio_producer_agent
│   ├── researcher.py         # Subagent with google_search tool
│   ├── scriptwriter.py       # Subagent dedicated to multi-speaker dialogue
│   └── audio_producer.py     # Subagent with generate_podcast_audio tool
├── tools/
│   ├── __init__.py           # Exports generate_podcast_audio and read_document
│   ├── audio_generator.py    # Multi-speaker TTS synthesizer & MP3 stitcher
│   └── document_reader.py    # Parser for PDF, Word (.docx), and text files
└── output/                   # Directory where generated .mp3 files are saved
```

---

## 5. ADK Web UI: File Uploads & In-Browser Audio Playback

The agent is designed for **Google ADK Web UI** (`adk web` / dev-ui):

### 📎 File Uploads via ADK Web
When you attach a file using the **Paperclip icon** in ADK Web (e.g., `job_satisfaction.pdf` or a `.docx` document):
1. ADK uploads the file into the session's **Artifact Service** as a session artifact (not a raw filesystem path).
2. The agent's `read_document` tool automatically calls `await tool_context.list_artifacts()` and loads the file in-memory using `await tool_context.load_artifact(filename)`.
3. It parses the document bytes using `pypdf` (for PDF) or `python-docx` (for Word documents) without requiring any manual disk path configuration.

### 🎧 In-Browser Audio Playback & Download
Once the podcast audio is assembled:
1. `generate_podcast_audio` saves the resulting MP3 bytes as a session artifact:
   ```python
   await tool_context.save_artifact(
       output_filename,
       types.Part.from_bytes(data=mp3_bytes, mime_type="audio/mp3")
   )
   ```
2. ADK Web receives an `artifact_delta` action event and renders the audio directly in the **Artifacts tab** (top right corner of ADK Web).
3. You can click to listen to the generated audio in the integrated audio player or download the `.mp3` file. A copy is also saved locally to `podcast_agent/output/`.

---

## 6. How to Run & Test

### Option A: Launch Interactive ADK Web UI (Recommended)
```bash
uv run adk web
```
Then navigate to:
```text
http://localhost:8000/dev-ui/?app=podcast_agent
```
1. Click the 📎 paperclip icon to upload any PDF or Word document (e.g., `job_satisfaction.pdf`).
2. Type your prompt:
   > *"I have attached job_satisfaction.pdf. Please create a 2-person podcast with Alex and Morgan and generate the audio."*
3. The coordinator will read the document, delegate research to `research_agent`, scriptwriting to `scriptwriter_agent`, and audio synthesis to `audio_producer_agent`.
4. Switch to the **Artifacts tab** on the top-right to play or download your episode!

### Option B: Interactive CLI
```bash
uv run adk run podcast_agent
```

### Option C: Automated End-to-End Test
```bash
uv run python test_podcast_agent.py
```
