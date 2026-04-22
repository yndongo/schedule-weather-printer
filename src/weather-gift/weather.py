from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, TypedDict
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)

DEFAULT_LATITUDE = 39.7684
DEFAULT_LONGITUDE = -86.1581
NOAA_TIMEOUT_SECONDS = 10
FALLBACK_CATEGORY = "cloudy"


class WeatherData(TypedDict):
    category: str
    temperature: int | None
    wind_mph: int
    rain_percent: int


def get_weather(
    fetcher: Callable[[], dict[str, Any]] | None = None,
) -> WeatherData:
    """Return the simplified weather payload used by content selection."""
    weather_fetcher = fetcher or fetch_noaa_weather

    try:
        raw_weather = weather_fetcher()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("weather fetch failed: %s", exc)
        return build_fallback_weather()

    try:
        return normalize_weather(raw_weather)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("weather normalization failed: %s", exc)
        return build_fallback_weather()


def fetch_noaa_weather() -> dict[str, Any]:
    """Fetch the next hourly forecast period from NOAA."""
    points_url = (
        f"https://api.weather.gov/points/{DEFAULT_LATITUDE},{DEFAULT_LONGITUDE}"
    )
    points_payload = _load_json(points_url)

    hourly_url = points_payload["properties"]["forecastHourly"]
    hourly_payload = _load_json(hourly_url)
    periods = hourly_payload["properties"]["periods"]
    if not periods:
        raise ValueError("no hourly forecast periods returned by NOAA")

    return periods[0]


def normalize_weather(raw_weather: dict[str, Any]) -> WeatherData:
    """Convert NOAA-style period data into the app's simplified shape."""
    temperature = _normalize_temperature(raw_weather.get("temperature"))
    wind_mph = _round_wind_mph(raw_weather.get("windSpeed"))
    rain_percent = _round_percent(
        _nested_value(raw_weather, "probabilityOfPrecipitation", "value")
    )
    category = simplify_weather_category(
        raw_weather.get("shortForecast"),
        wind_mph=wind_mph,
        rain_percent=rain_percent,
    )

    return {
        "category": category,
        "temperature": temperature,
        "wind_mph": wind_mph,
        "rain_percent": rain_percent,
    }


def build_fallback_weather() -> WeatherData:
    return {
        "category": FALLBACK_CATEGORY,
        "temperature": None,
        "wind_mph": 0,
        "rain_percent": 0,
    }


def simplify_weather_category(
    forecast_text: str | None,
    *,
    wind_mph: int,
    rain_percent: int,
) -> str:
    text = (forecast_text or "").lower()

    if "thunder" in text or "storm" in text:
        return "stormy"
    if "snow" in text or "blizzard" in text or "sleet" in text:
        return "snowy"
    if (
        "rain" in text
        or "shower" in text
        or "drizzle" in text
        or rain_percent >= 50
    ):
        return "rainy"
    if "sun" in text or "clear" in text or "fair" in text:
        return "sunny"
    if "cloud" in text or "overcast" in text or "fog" in text:
        return "cloudy"
    if "wind" in text or wind_mph >= 20:
        return "windy"

    return FALLBACK_CATEGORY


def _load_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "weather-gift-app/0.1 (local app)"})
    response = urlopen(request, timeout=NOAA_TIMEOUT_SECONDS)  # noqa: S310
    try:
        return json.load(response)
    finally:
        response.close()


def _round_wind_mph(wind_speed: Any) -> int:
    if wind_speed is None:
        return 0

    if isinstance(wind_speed, (int, float)):
        return int(round(wind_speed))

    values = [int(match) for match in re.findall(r"\d+", str(wind_speed))]
    if not values:
        return 0

    average = sum(values) / len(values)
    return int(round(average))


def _round_percent(value: Any) -> int:
    if value is None:
        return 0

    return max(0, min(100, int(round(float(value)))))


def _normalize_temperature(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _nested_value(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
