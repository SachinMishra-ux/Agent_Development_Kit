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
                 ┌────────────────────────────────┴────────────────────────────────┐
                 │ 1. Mandatory Research             2. Scriptwriting              │
                 ▼                                   ▼                             │
      ┌─────────────────────┐             ┌─────────────────────┐                  │
      │   research_agent    │             │  scriptwriter_agent │                  │
      │                     │             │                     │                  │
      │ • google_search     │             │ • 2 or 3 Personas   │                  │
      │ • Live web facts &  │             │ • Spoken dialogue   │                  │
      │   debate angles     │             │ • Transfers back to │                  │
      │ • Transfers back to │             │   coordinator       │                  │
      │   coordinator       │             └──────────┬──────────┘                  │
      └─────────────────────┘                        │                             │
                                                     ▼                             │
                                          ┌─────────────────────┐                  │
                                          │ 🛑 HUMAN-IN-THE-    │                  │
                                          │    LOOP GATE        │                  │
                                          │ • Review Transcript │                  │
                                          │ • Approve / Edit /  │                  │
                                          │   Re-research       │                  │
                                          └──────────┬──────────┘                  │
                                                     │ (Only if Approved)          │
                                                     ▼                             │
                                          ┌─────────────────────┐                  │
                                          │audio_producer_agent │◄─────────────────┘
                                          │                     │ 3. Audio Synthesis
                                          │ • generate_podcast_ │    (Approved Only)
                                          │   audio             │
                                          │ • Neural Edge-TTS   │
                                          │ • Emits MP3 Session │
                                          │   Artifact          │
                                          └─────────────────────┘
```

### Components & Roles

1. **Root Coordinator Agent (`podcast_agent`)**:
   - Manages episode planning and user inputs.
   - Uses `read_document` to inspect uploaded files (PDFs, Word docs, text).
   - **Enforces the production pipeline**: delegates to `research_agent`, then to `scriptwriter_agent`, halts for the **Human-in-the-Loop approval gate**, and only delegates to `audio_producer_agent` upon approval.
   - Surfaces draft transcripts, handles revision cycles, and points users to the generated audio in the **Artifacts tab**.

2. **Research Subagent (`research_agent`)**:
   - Equipped solely with `google_search` for real-time web grounding and factual verification.
   - Synthesizes findings into a structured briefing (key takeaways, debate angles, surprising data).
   - Transfers the completed research brief back to `podcast_agent`.

3. **Scriptwriter Subagent (`scriptwriter_agent`)**:
   - Focuses 100% on dialogue writing and iterative revisions without any tool distraction.
   - Dynamically crafts spoken conversations tailored to the requested speaker count:
     - **2 Speakers**:
       * **Alex (Host)**: Inquisitive, charismatic narrator who frames questions.
       * **Morgan (Expert)**: Domain specialist who explains concepts with relatable analogies.
     - **3 Speakers**:
       * **Alex (Host)**: Moderator keeping time and guiding transitions.
       * **Morgan (Expert)**: Deep technical and factual authority.
       * **Taylor (Skeptic)**: Critical thinker who questions assumptions and plays devil's advocate.
   - Transfers the completed script turns back to `podcast_agent` for human editorial review.

4. **Audio Producer Subagent (`audio_producer_agent`)**:
   - Equipped with `generate_podcast_audio`.
   - Receives the **approved** dialogue turns and synthesizes the neural multi-speaker MP3 audio track.
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

The system enforces a **strict Human-in-the-Loop editorial gate immediately after scriptwriting and before audio generation**:

1. **Script Presentation & Pause (Turn 1)**:
   - `scriptwriter_agent` crafts the dialogue turns and returns them to `podcast_agent`.
   - `podcast_agent` displays the full dialogue script directly in the chat, halts execution, and explicitly prompts the user:
     - **APPROVE**: Reply `"Approve"` or `"Looks good"` to authorize audio generation.
     - **EDIT / REVISE**: Reply with desired adjustments (e.g., *"Make Morgan more skeptical"*, *"Shorten turn 2"*, *"Add Taylor as a 3rd host"*).
     - **RE-RESEARCH / REJECT**: Reply if you want fresh research on a different angle or topic.

2. **Branching Logic (Turn 2+)**:
   - **On Revision**: `podcast_agent` routes the feedback back to `scriptwriter_agent` (and `research_agent` if new information is needed). The script is updated and presented again for review. **Zero audio is synthesized during revisions**, saving compute and time.
   - **On Approval**: `podcast_agent` transfers the finalized script to `audio_producer_agent`. The neural MP3 is generated, saved to **ADK Session Artifacts**, and made available for immediate playback and download in the **Artifacts tab**.

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
