from __future__ import annotations

import unittest

from weather_gift.format import DEFAULT_BORDER, FALLBACK_WEATHER_TEXT, format_card


class FormatTests(unittest.TestCase):
    def test_format_card_includes_sections_in_spec_order(self) -> None:
        result = format_card(
            "good morning! take on the day!",
            {"category": "sunny", "temperature": 72, "wind_mph": 8, "rain_percent": 20},
            "missing you <3, hope your day goes well!",
            art_text=" * ",
            lucky_number=7,
            width=32,
        )

        lines = result.splitlines()

        self.assertEqual(lines[0], DEFAULT_BORDER)
        self.assertEqual(lines[1], "good morning! take on the day!")
        self.assertEqual(lines[3], "Temperature: 72°")
        self.assertEqual(lines[4], "Wind: 8 mph")
        self.assertEqual(lines[5], "Rain: 20%")
        self.assertEqual(lines[6], "Lucky number: 7")
        self.assertEqual(lines[8].strip(), "*")
        self.assertEqual(" ".join(lines[10:12]), "missing you <3, hope your day goes well!")
        self.assertEqual(lines[-1], DEFAULT_BORDER)

    def test_format_card_uses_fallback_weather_text_when_weather_is_unavailable(self) -> None:
        result = format_card(
            "good night!",
            None,
            "rest well tonight",
            art_text="o",
            lucky_number=11,
            width=24,
        )

        self.assertIn("Wind: 0 mph", result)
        self.assertIn("Rain: 0%", result)
        self.assertIn("Lucky number: 11", result)
        self.assertIn("Temperature: N/A", result)
        self.assertIn("data not available now,", result)
        self.assertIn("apologies!", result)

    def test_format_card_uses_fallback_art_when_selected_art_exceeds_width(self) -> None:
        result = format_card(
            "hello",
            {"category": "sunny", "temperature": 70, "wind_mph": 4, "rain_percent": 10},
            "message",
            art_text="this-art-line-is-way-too-wide",
            lucky_number=5,
            width=10,
        )

        self.assertIn("  .-.", result)
        self.assertIn("(   )", result)
        self.assertIn("  `-`", result)

    def test_format_card_wraps_greeting_and_message_when_needed(self) -> None:
        result = format_card(
            "this greeting needs wrapping",
            {"category": "cloudy", "temperature": None, "wind_mph": 5, "rain_percent": 30},
            "this message needs wrapping too",
            art_text="*",
            lucky_number=9,
            width=12,
        )

        lines = result.splitlines()
        self.assertIn("this", lines)
        self.assertIn("greeting", lines)
        self.assertIn("needs", lines)
        self.assertIn("wrapping", lines)
        self.assertIn("this message", lines)

    def test_format_card_shows_temperature_na_when_missing(self) -> None:
        result = format_card(
            "hello",
            {"category": "cloudy", "temperature": None, "wind_mph": 4, "rain_percent": 10},
            "message",
            art_text="*",
            lucky_number=5,
            width=32,
        )

        self.assertIn("Temperature: N/A", result)

    def test_format_card_renders_multiline_art_as_separate_lines(self) -> None:
        result = format_card(
            "hello",
            {"category": "sunny", "temperature": 72, "wind_mph": 4, "rain_percent": 10},
            "message",
            art_text="line one\nline two",
            lucky_number=5,
            width=32,
        )

        lines = result.splitlines()
        self.assertIn("            line one            ", lines)
        self.assertIn("            line two            ", lines)
        self.assertNotIn("line one\\nline two", result)

    def test_format_card_preserves_centered_art_padding(self) -> None:
        result = format_card(
            "hello",
            {"category": "sunny", "temperature": 72, "wind_mph": 4, "rain_percent": 10},
            "message",
            art_text="*",
            lucky_number=5,
            width=8,
        )

        lines = result.splitlines()
        self.assertIn("   *    ", lines)


if __name__ == "__main__":
    unittest.main()
