# Google ADK: Built-in Tools, Grounding & Pricing Guide

This document covers how built-in server-side tools (such as Google Search) work in Google's Agent Development Kit (ADK), how to combine them with custom function calling, and their associated pricing structure.

---

## 1. Tool Types in Google ADK

In Google ADK and the Gemini ecosystem, tools are categorized into two main types:

| Tool Category | Execution Location | Examples | Description |
| :--- | :--- | :--- | :--- |
| **Built-in / Server-Side Tools** | Google Servers / Gemini Cloud | `google_search`, `code_execution` | Executed directly on Google infrastructure; results are grounded internally by Gemini without local execution. |
| **Client-Side Function Calling** | Local Application Runtime | Custom Python callables (e.g., `get_weather`) | Gemini returns a structured `tool_call`, your local app runs the function, and passes back a `tool_response`. |

---

## 2. Using the Built-in Google Search Tool

Google ADK provides a pre-configured `google_search` instance from `google.adk.tools`. It attaches native Google Search Grounding to the Gemini model requests.

### Basic Implementation
```python
from google.adk import Agent
from google.adk.tools import google_search

search_agent = Agent(
    name="search_bot",
    model="gemini-3.1-flash-lite",
    instruction="You are a helpful research assistant.",
    tools=[google_search],
)
```

---

## 3. Combining Built-in Tools with Custom Function Calling

### The Common Pitfall (400 ClientError)
When combining a **built-in server-side tool** (e.g., `google_search`) with **custom client-side function calling** (e.g., `get_weather`) in the same agent, the Gemini API raises this error:

```text
400 INVALID_ARGUMENT: Please enable tool_config.include_server_side_tool_invocations to use Built-in tools with Function calling.
```

### Why Does This Happen?
When custom functions are supplied, the Gemini API expects client-side tool turns. To allow the model to execute server-side tools (like Google Search) while retaining custom function declarations, the API requires an explicit flag: `include_server_side_tool_invocations = True`.

### The Solution in Google ADK
Pass `generate_content_config` with `types.ToolConfig(include_server_side_tool_invocations=True)` into your `Agent` definition:

```python
from google.adk import Agent
from google.adk.tools import google_search
from google.genai import types

from adk_simple_bot.prompt import ROOT_AGENT_INSTRUCTION
from adk_simple_bot.tools import get_weather

root_agent = Agent(
    name="adk_simple_bot",
    model="gemini-3.1-flash-lite",
    description="A helpful assistant that can search Google and check live weather conditions",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[get_weather, google_search],
    generate_content_config=types.GenerateContentConfig(
        tool_config=types.ToolConfig(
            include_server_side_tool_invocations=True
        )
    ),
)
```

---

## 4. Server-Side Tools Pricing & Costs

### A. Google Search Grounding (`google_search`)
Using Google Search Grounding incurs a **per-query search fee** on top of normal model token rates:

* **Free Tier Allowance:** **5,000 free search queries per month** (shared across eligible Gemini models).
* **Paid Rate (after 5,000 queries):** **$14.00 per 1,000 search queries** ($0.014 per search query).
* **Multiple Queries per Prompt:** If a single user request causes the model to generate multiple search queries (e.g. querying two distinct topics like "Google stock price" and "Apple stock price"), each search query is counted individually toward your quota/bill.

### B. Standard Token Costs
Regular token costs still apply regardless of tool usage:
* **Input Tokens:** Standard per-token rates for user prompts and conversation history.
* **Output Tokens:** Standard per-token rates for generated model responses.

### C. Cost Comparison Across Tools

| Tool Type | Example | Additional Tool Surcharge |
| :--- | :--- | :--- |
| **Google Search Grounding** | `google_search` | **$14 / 1,000 queries** (after 5,000 free queries/month) |
| **Built-in Code Execution** | `code_execution` | **$0 extra** (only regular model token usage) |
| **Client Function Calling** | `get_weather` | **$0 extra** (only regular model token usage) |

---

## 5. Summary & Best Practices

1. **Always enable `include_server_side_tool_invocations`** when an agent combines custom functions with Google Search.
2. **Monitor search volumes** in production environments to stay within expected free tier limits or budget for $14/1,000 queries.
3. **Use targeted system instructions** so the agent only invokes `google_search` when fresh or unknown web data is genuinely necessary.
