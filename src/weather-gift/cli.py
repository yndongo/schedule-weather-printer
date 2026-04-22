from __future__ import annotations

import argparse
from typing import Sequence

from weather_gift.main import main as run_main
from weather_gift.scheduler import main as schedule_main


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="weather-gift")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one card.")
    run_parser.add_argument("--mode", choices=("production", "test"), help="Run mode.")
    run_parser.add_argument("--config", dest="config_path", help="Optional config JSON path.")
    run_parser.add_argument("--now", help="Optional ISO timestamp for testing.")
    run_parser.add_argument(
        "--reset-fixtures",
        action="store_true",
        help="Reset test fixture rotation before running.",
    )

    schedule_parser = subparsers.add_parser("schedule", help="Run the scheduler loop.")
    schedule_parser.add_argument("--mode", choices=("production", "test"), help="Run mode.")
    schedule_parser.add_argument("--config", dest="config_path", help="Optional config JSON path.")
    schedule_parser.add_argument(
        "--stop-after-one-run",
        action="store_true",
        help="Exit after the next scheduled run.",
    )
    schedule_parser.add_argument(
        "--now",
        help="Optional ISO timestamp for one-shot scheduler testing.",
    )

    args = parser.parse_args(argv)
    if args.command == "run":
        forwarded_args: list[str] = []
        if args.mode:
            forwarded_args.extend(["--mode", args.mode])
        if args.config_path:
            forwarded_args.extend(["--config", args.config_path])
        if args.now:
            forwarded_args.extend(["--now", args.now])
        if args.reset_fixtures:
            forwarded_args.append("--reset-fixtures")
        return run_main(forwarded_args)

    forwarded_args = []
    if args.mode:
        forwarded_args.extend(["--mode", args.mode])
    if args.config_path:
        forwarded_args.extend(["--config", args.config_path])
    if args.stop_after_one_run:
        forwarded_args.append("--stop-after-one-run")
    if args.now:
        forwarded_args.extend(["--now", args.now])
    return schedule_main(forwarded_args)


if __name__ == "__main__":
    raise SystemExit(main())
