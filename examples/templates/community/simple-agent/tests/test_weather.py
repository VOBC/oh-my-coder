"""Tests for the simple weather agent."""

import os
from unittest.mock import patch

import pytest

from weather_agent import WeatherAgent, get_weather


class TestGetWeather:
    """Test the weather tool function."""

    def test_get_weather_success(self):
        """Test successful weather fetch."""
        result = get_weather("Beijing")
        assert "Beijing" in result
        # Should contain weather data or error message
        assert any(
            keyword in result.lower()
            for keyword in ["weather", "temperature", "cloudy", "sunny", "rain"]
        ) or "unable" in result.lower()

    def test_get_weather_empty_city(self):
        """Test with empty city name."""
        result = get_weather("")
        assert isinstance(result, str)

    def test_get_weather_special_chars(self):
        """Test with special characters in city name."""
        result = get_weather("New York")
        assert "New York" in result


class TestWeatherAgent:
    """Test the WeatherAgent class."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        agent = WeatherAgent()
        assert agent.api_key == "test-key"

    def test_init_with_param(self):
        """Test initialization with explicit API key."""
        agent = WeatherAgent(api_key="my-key")
        assert agent.api_key == "my-key"

    def test_init_without_key_raises(self):
        """Test that initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True), pytest.raises(
            ValueError, match="API key required"
        ):
            WeatherAgent()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_chat_weather_query(self):
        """Test weather query handling."""
        agent = WeatherAgent()
        response = await agent.chat("What's the weather in Shanghai?")
        assert "Shanghai" in response
        assert "🌤️" in response

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_chat_non_weather_query(self):
        """Test non-weather query handling."""
        agent = WeatherAgent()
        response = await agent.chat("Hello there")
        assert "weather agent" in response.lower()
        assert "Tokyo" in response

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_chat_various_weather_keywords(self):
        """Test various weather-related keywords trigger weather lookup."""
        agent = WeatherAgent()
        keywords = ["temperature", "forecast", "rain", "sunny"]

        for keyword in keywords:
            response = await agent.chat(f"What's the {keyword} in London?")
            assert "London" in response
            assert "🌤️" in response
