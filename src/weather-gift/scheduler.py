from __future__ import annotations

import argparse
import logging
import time as time_module
from datetime import datetime, timedelta, time
from typing import Callable, Sequence

from weather_gift.main import ConfigError, get_time_of_day as classify_time_of_day, run_once

LOGGER = logging.getLogger(__name__)

SCHEDULE = (
    ("morning", time(hour=8, minute=30)),
    ("afternoon", time(hour=17, minute=30)),
    ("night", time(hour=20, minute=30)),
)


def get_time_of_day(run_time: datetime) -> str:
    return classify_time_of_day(run_time)


def get_next_run_time(now: datetime) -> tuple[datetime, str]:
    for time_of_day, scheduled_time in SCHEDULE:
        candidate = datetime.combine(now.date(), scheduled_time, tzinfo=now.tzinfo)
        if now <= candidate:
            return candidate, time_of_day

    next_day = now.date() + timedelta(days=1)
    first_time_of_day, first_scheduled_time = SCHEDULE[0]
    return datetime.combine(next_day, first_scheduled_time, tzinfo=now.tzinfo), first_time_of_day


def sleep_until_next_run(
    next_run_time: datetime,
    *,
    now_provider: Callable[[], datetime] = datetime.now,
    sleeper: Callable[[float], None] = time_module.sleep,
) -> None:
    delay_seconds = (next_run_time - now_provider()).total_seconds()
    if delay_seconds > 0:
        sleeper(delay_seconds)


def run_scheduler(
    *,
    mode: str | None = None,
    config_path: str | None = None,
    stop_after_one_run: bool = False,
    now_provider: Callable[[], datetime] = datetime.now,
    sleeper: Callable[[float], None] = time_module.sleep,
    run_once_func: Callable[..., dict] = run_once,
) -> int:
    while True:
        current_time = now_provider()
        next_run_time, scheduled_time_of_day = get_next_run_time(current_time)
        LOGGER.info(
            "next scheduled run: time_of_day=%s at=%s",
            scheduled_time_of_day,
            next_run_time.isoformat(),
        )
        sleep_until_next_run(
            next_run_time,
            now_provider=now_provider,
            sleeper=sleeper,
        )

        run_time = next_run_time
        run_time_of_day = get_time_of_day(run_time)
        LOGGER.info("executing scheduled run: time_of_day=%s", run_time_of_day)

        try:
            run_once_func(
                now=run_time,
                mode=mode,
                config_path=config_path,
            )
        except ConfigError as exc:
            LOGGER.error("scheduler startup failed: %s", exc)
            return 1
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("scheduled run failed: %s", exc)
            if stop_after_one_run:
                return 1
        else:
            LOGGER.info("scheduled run completed: time_of_day=%s", run_time_of_day)
            if stop_after_one_run:
                return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Weather Gift scheduler.")
    parser.add_argument("--mode", choices=("production", "test"), help="Run mode.")
    parser.add_argument("--config", dest="config_path", help="Optional config JSON path.")
    parser.add_argument(
        "--now",
        help="Optional ISO timestamp for one-shot scheduler testing.",
    )
    parser.add_argument(
        "--stop-after-one-run",
        action="store_true",
        help="Exit after the next scheduled run.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        if args.now and not args.stop_after_one_run:
            LOGGER.error("--now is only supported with --stop-after-one-run")
            return 1

        if args.now:
            fixed_now = datetime.fromisoformat(args.now)
            now_provider = lambda: fixed_now
        else:
            now_provider = datetime.now

        return run_scheduler(
            mode=args.mode,
            config_path=args.config_path,
            stop_after_one_run=args.stop_after_one_run,
            now_provider=now_provider,
        )
    except ValueError as exc:
        LOGGER.error("scheduler startup failed: invalid --now value: %s", exc)
        return 1
    except KeyboardInterrupt:
        LOGGER.info("scheduler stopped by user")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
