#!/usr/bin/env python3
"""
Simple Weather Agent - Community Template Example

A minimal agent that demonstrates:
- Tool definition with @tool decorator
- OpenAI-compatible API integration
- Error handling and graceful degradation
"""

import os
import sys
from typing import Optional

import httpx
from pydantic import BaseModel, Field

# Add parent paths for omc imports (when running standalone)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from src.core.agent import Agent
from src.core.llm import LLMClient
from src.core.tool import tool


class WeatherResult(BaseModel):
    """Structured weather result."""
    city: str = Field(description="City name")
    temperature: str = Field(description="Current temperature")
    condition: str = Field(description="Weather condition")
    humidity: Optional[str] = Field(default=None, description="Humidity percentage")


@tool(description="Get current weather for a city")
def get_weather(city: str) -> str:
    """
    Fetch weather information for a given city.

    Args:
        city: City name (e.g., "Beijing", "Shanghai", "Tokyo")

    Returns:
        Weather description string
    """
    # Using wttr.in as a free weather API (no API key needed)
    try:
        url = f"https://wttr.in/{city}?format=%C|%t|%h"
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()

        parts = response.text.strip().split("|")
        if len(parts) >= 2:
            condition = parts[0]
            temp = parts[1]
            humidity = parts[2] if len(parts) > 2 else "N/A"
            return f"{city}: {condition}, {temp}, humidity {humidity}"
        return f"{city}: Weather data available but format unexpected"
    except httpx.TimeoutException:
        return f"{city}: Weather service timeout, please try again"
    except Exception as e:
        return f"{city}: Unable to fetch weather ({type(e).__name__})"


class WeatherAgent(Agent):
    """A simple weather query agent."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.llm = LLMClient(api_key=self.api_key)
        self.register_tool(get_weather)

    async def chat(self, message: str) -> str:
        """Process user message and return response."""
        # Simple intent detection
        weather_keywords = ["weather", "temperature", "forecast", "rain", "sunny"]
        if any(kw in message.lower() for kw in weather_keywords):
            # Extract city (simple heuristic)
            words = message.split()
            city = words[-1] if len(words) > 1 else "Beijing"
            weather_info = get_weather(city)
            return f"🌤️ {weather_info}\n\nPowered by Oh My Coder Community Template"

        return (
            "I'm a weather agent! Ask me about weather in any city.\n"
            "Example: 'What's the weather in Tokyo?'"
        )


def main():
    """CLI entry point."""
    import asyncio

    print("🌤️  Simple Weather Agent")
    print("=" * 40)
    print("Type 'quit' to exit\n")

    try:
        agent = WeatherAgent()
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye! 👋")
                break
            if not user_input:
                continue

            response = asyncio.run(agent.chat(user_input))
            print(f"Agent: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    main()
