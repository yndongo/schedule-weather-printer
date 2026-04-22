from __future__ import annotations

import unittest
from datetime import datetime

from weather_gift.main import ConfigError
from weather_gift.scheduler import get_next_run_time, run_scheduler, sleep_until_next_run


class SchedulerTests(unittest.TestCase):
    def test_get_next_run_time_returns_same_day_morning_when_before_morning(self) -> None:
        run_time, time_of_day = get_next_run_time(datetime(2026, 4, 17, 7, 0))

        self.assertEqual(run_time, datetime(2026, 4, 17, 8, 30))
        self.assertEqual(time_of_day, "morning")

    def test_get_next_run_time_rolls_to_next_day_after_night(self) -> None:
        run_time, time_of_day = get_next_run_time(datetime(2026, 4, 17, 21, 1))

        self.assertEqual(run_time, datetime(2026, 4, 18, 8, 30))
        self.assertEqual(time_of_day, "morning")

    def test_sleep_until_next_run_sleeps_for_positive_delay(self) -> None:
        calls: list[float] = []

        sleep_until_next_run(
            datetime(2026, 4, 17, 8, 30),
            now_provider=lambda: datetime(2026, 4, 17, 8, 0),
            sleeper=lambda seconds: calls.append(seconds),
        )

        self.assertEqual(calls, [1800.0])

    def test_run_scheduler_runs_once_and_stops_in_one_shot_mode(self) -> None:
        now_values = iter(
            [
                datetime(2026, 4, 17, 8, 30),
                datetime(2026, 4, 17, 8, 30),
            ]
        )
        calls: list[dict] = []

        def now_provider() -> datetime:
            return next(now_values)

        def run_once_func(**kwargs: object) -> dict:
            calls.append(kwargs)
            return {}

        exit_code = run_scheduler(
            mode="test",
            stop_after_one_run=True,
            now_provider=now_provider,
            sleeper=lambda seconds: None,
            run_once_func=run_once_func,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["now"], datetime(2026, 4, 17, 8, 30))
        self.assertEqual(calls[0]["mode"], "test")

    def test_run_scheduler_returns_non_zero_on_fatal_config_error(self) -> None:
        def run_once_func(**kwargs: object) -> dict:
            raise ConfigError("bad config")

        exit_code = run_scheduler(
            stop_after_one_run=True,
            now_provider=lambda: datetime(2026, 4, 17, 8, 30),
            sleeper=lambda seconds: None,
            run_once_func=run_once_func,
        )

        self.assertEqual(exit_code, 1)

    def test_run_scheduler_logs_and_continues_after_non_fatal_error(self) -> None:
        now_values = iter(
            [
                datetime(2026, 4, 17, 8, 30),
                datetime(2026, 4, 17, 8, 30),
                datetime(2026, 4, 17, 8, 31),
                datetime(2026, 4, 17, 8, 31),
            ]
        )
        calls: list[datetime] = []

        def now_provider() -> datetime:
            return next(now_values)

        def run_once_func(**kwargs: object) -> dict:
            calls.append(kwargs["now"])
            if len(calls) == 1:
                raise RuntimeError("temporary error")
            raise ConfigError("stop after retry")

        exit_code = run_scheduler(
            stop_after_one_run=False,
            now_provider=now_provider,
            sleeper=lambda seconds: None,
            run_once_func=run_once_func,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            calls,
            [
                datetime(2026, 4, 17, 8, 30),
                datetime(2026, 4, 17, 17, 30),
            ],
        )


if __name__ == "__main__":
    unittest.main()
