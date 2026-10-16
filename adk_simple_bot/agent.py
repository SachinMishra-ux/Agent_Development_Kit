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
            include_server_side_tool_invocations=True #due to google search tool
        )
    ),
)