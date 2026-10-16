# ⚡ Google ADK: Context Caching & Multi-Agent System Instructions Guide

## 1. Overview: What is Context Caching?

When interacting with Large Language Models (LLMs) like Google Gemini (Gemini 1.5, Gemini 2.0, Gemini 3.x), the model processes a sequence of tokens comprising:
1. **System Instructions** (`config.system_instruction`)
2. **Tool / Function Declarations**
3. **Conversation History & In-Session Contents**

Because API pricing and latency scale with token count, Gemini provides **Context Caching** (implicit and explicit prefix caching). If the beginning of the prompt (the prefix, especially the system instruction and tool definitions) remains **100% identical** across sequential requests, the model can reuse its pre-computed attention states from the cache.

Context caching provides:
- **Up to 80% lower latency** on subsequent turns.
- **Up to 75% cost savings** on cached prompt tokens.

---

## 2. Why the Performance Alert Occurred

In the Google ADK Developer Web UI (`adk web`), you may encounter this notification:

> ⚠️ **Performance Alert:**
> *"System instructions were modified between consecutive turns in this session. This change breaks context cache alignment, resulting in a cache miss that increases generation latency for subsequent requests."*

### Why does this happen in Multi-Agent workflows?

In a collaborative multi-agent architecture (e.g., `podcast_agent` transferring to `research_agent`, `scriptwriter_agent`, and `audio_producer_agent`):
- By default, each `Agent(instruction="...")` sends its own string as the model's `system_instruction`.
- When control transfers from **Agent A** to **Agent B**, the active agent changes.
- In Turn 4 (`audio_producer_agent`), the system instruction was `AUDIO_PRODUCER_INSTRUCTION`.
- In Turn 5 (`podcast_agent`), control returned to the coordinator, and the system instruction was swapped to `COORDINATOR_INSTRUCTION`.

Because the system instruction at the very top of the prompt changed between consecutive turns in the same session, Gemini could not match its cached prefix. This caused a **cache miss**, prompting ADK's performance profiler to flag the cache invalidation.

---

## 3. How Google ADK Solves This: `static_instruction` vs `instruction`

Google ADK's `LlmAgent` provides two distinct instruction fields specifically to optimize context caching:

| Parameter | Type | Where it goes in the LLM Request | Cache Behavior |
| :--- | :--- | :--- | :--- |
| **`static_instruction`** | `Optional[str]` | Sent directly as **`system_instruction`** at position 0. | **Cached prefix.** Never changes across agents or turns. |
| **`instruction`** (with `static_instruction` set) | `str` or `callable` | Automatically placed into **`contents`** (user-turn steering). | **Dynamic turn steering.** Can vary per agent without breaking the cache. |

### The Mechanism in ADK Core (`instructions.py`):
```python
# 1. Handle static_instruction: sets the static system instruction
if agent.static_instruction:
    static_content = _transformers.t_content(agent.static_instruction)
    llm_request.append_instructions(static_content)

# 2. Handle agent.instruction:
if agent.instruction and not agent.static_instruction:
    # If NO static_instruction is set: instruction goes directly to system_instruction
    # (causes cache miss when switching agents!)
    si = await _process_agent_instruction(agent, invocation_context)
    llm_request.append_instructions([si])
elif agent.instruction and agent.static_instruction:
    # When static_instruction IS set: dynamic instruction is added to user contents!
    # (preserves identical system_instruction prefix across all agents!)
    si = await _process_agent_instruction(agent, invocation_context)
    dynamic_content = types.Content(role='user', parts=[types.Part(text=si)])
    llm_request.contents.append(dynamic_content)
```

---

## 4. Implementation Pattern for Multi-Agent Systems

### Step 1: Define a Shared Studio Static Instruction
Define a shared static prompt that establishes the overall application identity and team roster:

```python
PODCAST_STUDIO_STATIC_INSTRUCTION = """You are an AI agent operating within the Autonomous Podcast Studio production system.
The studio produces high-quality, engaging, multi-speaker podcast episodes through a collaborative team of specialized agents:
- podcast_agent: Executive Producer coordinating planning, document reading, and pipeline orchestration.
- research_agent: Lead Researcher gathering real-time web facts, data, and debate angles via Google Search.
- scriptwriter_agent: Award-winning Scriptwriter drafting organic, multi-speaker spoken dialogue for distinct personas.
- audio_producer_agent: Technical Sound Engineer synthesizing neural multi-speaker MP3 audio and creating ADK Session Artifacts.

Maintain high journalistic standards, engaging conversational pacing, and seamless handoffs across the production team.
"""
```

### Step 2: Assign `static_instruction` to ALL Agents in the Tree

```python
# Coordinator
root_agent = Agent(
    name="podcast_agent",
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[research_agent, scriptwriter_agent, audio_producer_agent],
    tools=[read_document, load_artifacts],
)

# Research Subagent
research_agent = Agent(
    name="research_agent",
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=RESEARCHER_INSTRUCTION,
    tools=[google_search],
)

# Scriptwriter Subagent
scriptwriter_agent = Agent(
    name="scriptwriter_agent",
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=SCRIPTWRITER_INSTRUCTION,
    tools=[],
)

# Audio Producer Subagent
audio_producer_agent = Agent(
    name="audio_producer_agent",
    static_instruction=PODCAST_STUDIO_STATIC_INSTRUCTION,
    instruction=AUDIO_PRODUCER_INSTRUCTION,
    tools=[generate_podcast_audio],
)
```

### The Result:
- **`system_instruction` is 100% identical** across every turn in the session.
- Gemini's context cache hit rate reaches maximum efficiency.
- The ADK Web UI Performance Warning is completely resolved.
