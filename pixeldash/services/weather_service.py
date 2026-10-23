"""Fetch current weather from OpenWeather, with a ten-minute cache."""

import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from pixeldash.config import get_config

logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(self):
        load_dotenv(".env")
        config = get_config()
        self.api_key = os.getenv("OPENWEATHER_API_KEY") or config.get("weather.api_key")
        self.city = config.get("weather.city")
        self.units = config.get("weather.units")
        self._ensure_api_key()
        if not self.city.strip():
            raise ValueError("Set weather.city in your configuration before selecting weather")
        self.cache_duration = 600
        self.last_fetch = None
        self.cached_data = None

    def _ensure_api_key(self):
        if not self.api_key:
            raise ValueError("Set weather.api_key in your config or OPENWEATHER_API_KEY")

    def get_weather(self) -> Optional[dict]:
        now = time.monotonic()
        if self.last_fetch is not None and now - self.last_fetch < self.cache_duration:
            return self.cached_data
        # Cache failures too so an unavailable service is not retried every frame.
        self.last_fetch = now
        try:
            response = requests.get(
                "https://api.openweathermap.org/geo/1.0/direct",
                params={"q": self.city, "limit": 1, "appid": self.api_key},
                timeout=5,
            )
            response.raise_for_status()
            location = response.json()[0]
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": location["lat"],
                    "lon": location["lon"],
                    "appid": self.api_key,
                    "units": self.units,
                },
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            # Reject incomplete responses before replacing the last good reading.
            float(data["main"]["temp"])
            for key in ("main", "description", "icon"):
                if not isinstance(data["weather"][0][key], str):
                    raise ValueError("Invalid weather condition")
            self.cached_data = data
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
            logger.warning("Could not fetch weather data; retrying in 10 minutes.")
        return self.cached_data

    def get_temperature(self) -> Optional[float]:
        weather = self.get_weather()
        return float(weather["main"]["temp"]) if weather else None

    def get_condition(self) -> Optional[str]:
        weather = self.get_weather()
        return weather["weather"][0]["main"] if weather else None

    def get_description(self) -> Optional[str]:
        weather = self.get_weather()
        return weather["weather"][0]["description"] if weather else None

    def get_icon_code(self) -> Optional[str]:
        weather = self.get_weather()
        return weather["weather"][0]["icon"] if weather else None
