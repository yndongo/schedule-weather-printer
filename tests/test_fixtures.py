from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from weather_gift.fixtures import load_weather_fixture, reset_fixture_index


class FixtureTests(unittest.TestCase):
    def test_load_weather_fixture_rotates_deterministically_within_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "fixtures"
            index_path = root / "fixture_index.json"
            self._write_fixture(root / "morning" / "01.json", {"shortForecast": "Sunny"})
            self._write_fixture(root / "morning" / "02.json", {"shortForecast": "Cloudy"})

            first = load_weather_fixture("morning", root, index_path=index_path)
            second = load_weather_fixture("morning", root, index_path=index_path)
            third = load_weather_fixture("morning", root, index_path=index_path)

        self.assertEqual(first["shortForecast"], "Sunny")
        self.assertEqual(second["shortForecast"], "Cloudy")
        self.assertEqual(third["shortForecast"], "Sunny")

    def test_load_weather_fixture_keeps_separate_indices_per_time_of_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "fixtures"
            index_path = root / "fixture_index.json"
            self._write_fixture(root / "morning" / "01.json", {"shortForecast": "Morning"})
            self._write_fixture(root / "afternoon" / "01.json", {"shortForecast": "Afternoon"})

            morning = load_weather_fixture("morning", root, index_path=index_path)
            afternoon = load_weather_fixture("afternoon", root, index_path=index_path)

        self.assertEqual(morning["shortForecast"], "Morning")
        self.assertEqual(afternoon["shortForecast"], "Afternoon")

    def test_reset_fixture_index_restarts_rotation_without_deleting_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "fixtures"
            index_path = root / "fixture_index.json"
            self._write_fixture(root / "night" / "01.json", {"shortForecast": "Night One"})
            self._write_fixture(root / "night" / "02.json", {"shortForecast": "Night Two"})

            load_weather_fixture("night", root, index_path=index_path)
            reset_fixture_index(index_path, time_of_day="night")
            reset_value = load_weather_fixture("night", root, index_path=index_path)

        self.assertEqual(reset_value["shortForecast"], "Night One")

    def test_load_weather_fixture_returns_safe_fallback_for_missing_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "fixtures"

            result = load_weather_fixture("morning", root)

        self.assertEqual(result, {})

    def _write_fixture(self, path: Path, payload: dict[str, str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
