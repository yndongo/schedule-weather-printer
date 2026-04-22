from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from weather_gift.main import get_time_of_day, load_config, main, run_once


class MainTests(unittest.TestCase):
    def test_load_config_merges_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            custom_art_path = Path(temp_dir) / "custom-art.json"
            custom_art_path.write_text(
                json.dumps(
                    {
                        "fallback": {"key": "fallback", "text": "x"},
                        "morning": {"sunny": [{"key": "a", "text": "x"}]},
                        "afternoon": {"sunny": [{"key": "b", "text": "x"}]},
                        "night": {"sunny": [{"key": "c", "text": "x"}]},
                    }
                ),
                encoding="utf-8",
            )
            config_path.write_text(
                json.dumps(
                    {
                        "mode": "test",
                        "card_width": 40,
                        "paths": {"art": str(custom_art_path)},
                    }
                ),
                encoding="utf-8",
            )

            config, _warnings = load_config(config_path)

        self.assertEqual(config["mode"], "test")
        self.assertEqual(config["card_width"], 40)
        self.assertEqual(config["lucky_number"], 7)
        self.assertEqual(config["paths"]["art"], str(custom_art_path))

    def test_get_time_of_day_uses_spec_boundaries(self) -> None:
        self.assertEqual(get_time_of_day(datetime(2026, 4, 17, 8, 29)), "night")
        self.assertEqual(get_time_of_day(datetime(2026, 4, 17, 8, 30)), "morning")
        self.assertEqual(get_time_of_day(datetime(2026, 4, 17, 17, 29)), "morning")
        self.assertEqual(get_time_of_day(datetime(2026, 4, 17, 17, 30)), "afternoon")
        self.assertEqual(get_time_of_day(datetime(2026, 4, 17, 20, 29)), "afternoon")
        self.assertEqual(get_time_of_day(datetime(2026, 4, 17, 20, 30)), "night")

    def test_run_once_executes_end_to_end_in_test_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(temp_path)
            output = io.StringIO()

            result = run_once(
                now=datetime(2026, 4, 17, 8, 30),
                mode="test",
                config_path=config_path,
                weather_fetcher=lambda: {
                    "shortForecast": "Sunny",
                    "windSpeed": "7 to 9 mph",
                    "probabilityOfPrecipitation": {"value": 19.6},
                },
                chooser=lambda options: options[0],
                output=output,
            )

        self.assertEqual(result["time_of_day"], "morning")
        self.assertEqual(result["weather"]["category"], "sunny")
        self.assertEqual(result["message_id"], "m1")
        self.assertEqual(result["art_key"], "sun-a")
        self.assertIn("Wind: 8 mph", result["card_text"])
        self.assertIn("Lucky number: 7", result["card_text"])
        self.assertEqual(output.getvalue(), result["card_text"] + "\n")

    def test_run_once_prints_card_in_production_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(
                temp_path,
                extra_config={"mode": "production", "lucky_number": 7},
            )
            output = io.StringIO()

            result = run_once(
                now=datetime(2026, 4, 17, 8, 30),
                mode="production",
                config_path=config_path,
                weather_fetcher=lambda: {
                    "shortForecast": "Sunny",
                    "temperature": 72,
                    "windSpeed": "7 to 9 mph",
                    "probabilityOfPrecipitation": {"value": 19.6},
                },
                chooser=lambda options: options[0],
                output=output,
            )

        self.assertEqual(output.getvalue(), result["card_text"] + "\n")

    def test_run_once_uses_configured_card_width(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(
                temp_path,
                extra_config={"card_width": 20},
            )

            result = run_once(
                now=datetime(2026, 4, 17, 8, 30),
                mode="test",
                config_path=config_path,
                weather_fetcher=lambda: {
                    "shortForecast": "Sunny",
                    "temperature": 72,
                    "windSpeed": "7 to 9 mph",
                    "probabilityOfPrecipitation": {"value": 19.6},
                },
                chooser=lambda options: options[0],
                output=io.StringIO(),
            )

        lines = result["card_text"].splitlines()
        self.assertTrue(lines)
        self.assertEqual(len(lines[0]), 20)

    @patch("weather_gift.main.write_output")
    def test_run_once_writes_card_to_output_without_target(self, mock_write_output) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(temp_path)

            result = run_once(
                now=datetime(2026, 4, 17, 8, 30),
                mode="test",
                config_path=config_path,
                weather_fetcher=lambda: {
                    "shortForecast": "Sunny",
                    "temperature": 72,
                    "windSpeed": "7 to 9 mph",
                    "probabilityOfPrecipitation": {"value": 19.6},
                },
                chooser=lambda options: options[0],
            )

        mock_write_output.assert_called_once_with(
            result["card_text"],
            output=None,
        )

    def test_run_once_uses_rotating_test_fixtures_by_time_of_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            fixture_root = temp_path / "fixtures"
            fixture_index_path = fixture_root / "fixture_index.json"
            self._write_fixture(
                fixture_root / "morning" / "01.json",
                {
                    "shortForecast": "Sunny",
                    "windSpeed": "7 mph",
                    "probabilityOfPrecipitation": {"value": 10},
                },
            )
            self._write_fixture(
                fixture_root / "morning" / "02.json",
                {
                    "shortForecast": "Cloudy",
                    "windSpeed": "4 mph",
                    "probabilityOfPrecipitation": {"value": 30},
                },
            )
            config_path = self._write_config(
                temp_path,
                extra_config={
                    "weather_fixture_root": str(fixture_root),
                    "weather_fixture_index_path": str(fixture_index_path),
                },
            )

            first = run_once(
                now=datetime(2026, 4, 17, 8, 30),
                mode="test",
                config_path=config_path,
                chooser=lambda options: options[0],
                output=io.StringIO(),
            )
            second = run_once(
                now=datetime(2026, 4, 18, 8, 30),
                mode="test",
                config_path=config_path,
                chooser=lambda options: options[0],
                output=io.StringIO(),
            )

        self.assertEqual(first["weather"]["category"], "sunny")
        self.assertEqual(second["weather"]["category"], "cloudy")

    def test_run_once_can_reset_fixture_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            fixture_root = temp_path / "fixtures"
            fixture_index_path = fixture_root / "fixture_index.json"
            self._write_fixture(
                fixture_root / "morning" / "01.json",
                {
                    "shortForecast": "Sunny",
                    "windSpeed": "7 mph",
                    "probabilityOfPrecipitation": {"value": 10},
                },
            )
            self._write_fixture(
                fixture_root / "morning" / "02.json",
                {
                    "shortForecast": "Cloudy",
                    "windSpeed": "4 mph",
                    "probabilityOfPrecipitation": {"value": 30},
                },
            )
            config_path = self._write_config(
                temp_path,
                extra_config={
                    "weather_fixture_root": str(fixture_root),
                    "weather_fixture_index_path": str(fixture_index_path),
                },
            )

            run_once(
                now=datetime(2026, 4, 17, 8, 30),
                mode="test",
                config_path=config_path,
                chooser=lambda options: options[0],
                output=io.StringIO(),
            )
            reset_run = run_once(
                now=datetime(2026, 4, 18, 8, 30),
                mode="test",
                config_path=config_path,
                chooser=lambda options: options[0],
                output=io.StringIO(),
                reset_fixtures=True,
            )

        self.assertEqual(reset_run["weather"]["category"], "sunny")

    def test_main_returns_non_zero_on_invalid_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bad.json"
            config_path.write_text("{", encoding="utf-8")

            exit_code = main(["--config", str(config_path)])

        self.assertEqual(exit_code, 1)

    def test_python_m_weather_gift_cli_prints_visible_card(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            fixture_path = temp_path / "weather.json"
            fixture_path.write_text(
                json.dumps(
                    {
                        "shortForecast": "Sunny",
                        "temperature": 72,
                        "windSpeed": "7 to 9 mph",
                        "probabilityOfPrecipitation": {"value": 19.6},
                    }
                ),
                encoding="utf-8",
            )
            config_path = self._write_config(
                temp_path,
                extra_config={"weather_fixture_path": str(fixture_path)},
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "weather_gift.cli",
                    "run",
                    "--mode",
                    "test",
                    "--config",
                    str(config_path),
                    "--now",
                    "2026-04-17T08:30:00",
                ],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip())
        self.assertIn("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=", result.stdout)
        self.assertIn("Temperature: 72°", result.stdout)
        self.assertIn("Wind: 8 mph", result.stdout)

    def _write_config(
        self,
        temp_path: Path,
        *,
        extra_config: dict[str, object] | None = None,
    ) -> Path:
        greetings_path = temp_path / "greetings.json"
        messages_path = temp_path / "messages.json"
        art_path = temp_path / "art.json"
        special_days_path = temp_path / "special_days.json"
        config_path = temp_path / "config.json"
        greeting_history_path = temp_path / "greeting_history.json"
        message_history_path = temp_path / "message_history.json"
        art_history_path = temp_path / "art_history.json"

        greetings_path.write_text(
            json.dumps(
                {
                    "morning": ["morning hi", "morning hello"],
                    "afternoon": ["afternoon hi"],
                    "night": ["night hi"],
                }
            ),
            encoding="utf-8",
        )
        messages_path.write_text(
            json.dumps(
                {
                    "morning": [
                        {"id": "m1", "text": "morning message one"},
                        {"id": "m2", "text": "morning message two"},
                    ],
                    "afternoon": [{"id": "a1", "text": "afternoon message"}],
                    "night": [{"id": "n1", "text": "night message"}],
                }
            ),
            encoding="utf-8",
        )
        art_path.write_text(
            json.dumps(
                {
                    "fallback": {"key": "fallback", "text": "(fallback art)"},
                    "morning": {"sunny": [{"key": "sun-a", "text": "sun a"}]},
                    "afternoon": {"sunny": [{"key": "afternoon-sun", "text": "afternoon sun"}]},
                    "night": {"sunny": [{"key": "night-sun", "text": "night sun"}]},
                }
            ),
            encoding="utf-8",
        )
        special_days_path.write_text("[]", encoding="utf-8")
        greeting_history_path.write_text("[]", encoding="utf-8")
        message_history_path.write_text("[]", encoding="utf-8")
        art_history_path.write_text("[]", encoding="utf-8")
        config_data: dict[str, object] = {
            "mode": "test",
            "card_width": 32,
            "paths": {
                "greetings": str(greetings_path),
                "messages": str(messages_path),
                "art": str(art_path),
                "special_days": str(special_days_path),
                "greeting_history": str(greeting_history_path),
                "message_history": str(message_history_path),
                "art_history": str(art_history_path),
            },
        }
        if extra_config:
            config_data.update(extra_config)

        config_path.write_text(json.dumps(config_data), encoding="utf-8")
        return config_path

    def _write_fixture(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
