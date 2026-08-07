from google.adk import Agent

from adk_simple_bot.prompt import ROOT_AGENT_INSTRUCTION
from adk_simple_bot.tools import dummy_wether

root_agent = Agent(
    name="adk_simple_bot",
    model="gemini-2.5-flash",
    description="A bot that shortens messages while maintaining their core meaning",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[dummy_wether],
)