from google.adk import Agent
from google.adk.tools import google_search
from adk_simple_bot.tools import get_weather

# Sub-agent 1: Handles custom function calls (live weather)
weather_agent = Agent(
    name="weather_agent",
    model="gemini-2.5-flash",
    description="Specialist agent that fetches live weather forecasts and conditions for cities.",
    instruction="You are a weather specialist. Call get_weather to find current weather conditions.",
    tools=[get_weather],
)

# Sub-agent 2: Handles Google Search grounding
search_agent = Agent(
    name="search_agent",
    model="gemini-2.5-flash",
    description="Specialist agent that searches Google for real-time web information and general knowledge.",
    instruction="You are a search specialist. Use Google Search to find current facts and information.",
    tools=[google_search],
)

# Root coordinator agent: Routes requests cleanly to the appropriate specialist
root_agent = Agent(
    name="adk_simple_bot",
    model="gemini-2.5-flash",
    description="Helpful coordinator assistant that routes requests to search or weather specialists.",
    instruction=(
        "You are a helpful assistant and coordinator. "
        "If the user asks about weather or atmospheric conditions, delegate to weather_agent. "
        "If the user asks about current events, facts, news, or requires web search, delegate to search_agent. "
        "Otherwise, answer the user directly and concisely."
    ),
    sub_agents=[weather_agent, search_agent],
)
