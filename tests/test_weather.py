from __future__ import annotations

import unittest

from weather_gift.weather import get_weather


class WeatherTests(unittest.TestCase):
    def test_get_weather_returns_expected_shape(self) -> None:
        def fetcher() -> dict:
            return {
                "shortForecast": "Sunny",
                "temperature": 71.6,
                "windSpeed": "7 to 9 mph",
                "probabilityOfPrecipitation": {"value": 19.6},
            }

        result = get_weather(fetcher=fetcher)

        self.assertEqual(
            set(result),
            {"category", "temperature", "wind_mph", "rain_percent"},
        )
        self.assertEqual(result["category"], "sunny")
        self.assertEqual(result["temperature"], 72)
        self.assertEqual(result["wind_mph"], 8)
        self.assertEqual(result["rain_percent"], 20)

    def test_get_weather_uses_graceful_fallback_on_fetch_error(self) -> None:
        def fetcher() -> dict:
            raise RuntimeError("network unavailable")

        result = get_weather(fetcher=fetcher)

        self.assertEqual(result["category"], "cloudy")
        self.assertIsNone(result["temperature"])
        self.assertEqual(result["wind_mph"], 0)
        self.assertEqual(result["rain_percent"], 0)

    def test_get_weather_returns_none_when_temperature_is_missing_or_invalid(self) -> None:
        def fetcher() -> dict:
            return {
                "shortForecast": "Cloudy",
                "temperature": "unknown",
                "windSpeed": "4 mph",
                "probabilityOfPrecipitation": {"value": 30},
            }

        result = get_weather(fetcher=fetcher)

        self.assertEqual(result["category"], "cloudy")
        self.assertIsNone(result["temperature"])


if __name__ == "__main__":
    unittest.main()
