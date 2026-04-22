from __future__ import annotations

import unittest
from unittest.mock import patch

from weather_gift.cli import main


class CliTests(unittest.TestCase):
    def test_cli_run_forwards_to_main_entry(self) -> None:
        with patch("weather_gift.cli.run_main", return_value=0) as run_main:
            exit_code = main(["run", "--mode", "test", "--now", "2026-04-17T08:30:00"])

        self.assertEqual(exit_code, 0)
        run_main.assert_called_once_with(["--mode", "test", "--now", "2026-04-17T08:30:00"])

    def test_cli_schedule_forwards_to_scheduler_entry(self) -> None:
        with patch("weather_gift.cli.schedule_main", return_value=0) as schedule_main:
            exit_code = main(
                [
                    "schedule",
                    "--mode",
                    "test",
                    "--stop-after-one-run",
                    "--now",
                    "2026-04-17T08:30:00",
                ]
            )

        self.assertEqual(exit_code, 0)
        schedule_main.assert_called_once_with(
            ["--mode", "test", "--stop-after-one-run", "--now", "2026-04-17T08:30:00"]
        )


if __name__ == "__main__":
    unittest.main()
