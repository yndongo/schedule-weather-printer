from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO, TypedDict

from weather_gift.config import ConfigError, load_config
from weather_gift.content import get_art_text, find_special_day, select_content
from weather_gift.format import DEFAULT_BORDER, DEFAULT_WIDTH, format_card
from weather_gift.fixtures import load_weather_fixture, reset_fixture_index
from weather_gift.output import write_output
from weather_gift.weather import fetch_noaa_weather, get_weather

LOGGER = logging.getLogger(__name__)

MORNING_START = time(hour=8, minute=30)
AFTERNOON_START = time(hour=17, minute=30)
NIGHT_START = time(hour=20, minute=30)


class RunResult(TypedDict):
    card_text: str
    time_of_day: str
    weather: dict[str, Any]
    message_id: str
    art_key: str
    special_date_type: str | None

def get_time_of_day(now: datetime) -> str:
    current_time = now.time()
    if current_time >= NIGHT_START:
        return "night"
    if current_time >= AFTERNOON_START:
        return "afternoon"
    if current_time >= MORNING_START:
        return "morning"
    return "night"


def run_once(
    *,
    now: datetime | None = None,
    mode: str | None = None,
    config_path: str | Path | None = None,
    weather_fetcher: Callable[[], dict[str, Any]] | None = None,
    chooser: Callable[[Sequence[Any]], Any] | None = None,
    output: TextIO | None = None,
    reset_fixtures: bool = False,
) -> RunResult:
    current_time = now or datetime.now()
    config, warnings = load_config(config_path, mode=mode)
    for warning in warnings:
        LOGGER.warning("config warning: %s", warning)
    paths = config["paths"]
    time_of_day = get_time_of_day(current_time)
    special_day = find_special_day(
        current_time,
        special_days_path=Path(paths["special_days"]),
    )
    weather = _get_weather_for_run(
        time_of_day=time_of_day,
        mode=str(config.get("mode", "production")),
        fetcher=weather_fetcher,
        fixture_path=config.get("weather_fixture_path"),
        fixture_root=config.get("weather_fixture_root"),
        fixture_index_path=config.get("weather_fixture_index_path"),
        reset_fixtures=reset_fixtures,
    )
    selection = select_content(
        time_of_day,
        weather,
        now=current_time,
        chooser=chooser,
        greetings_path=Path(paths["greetings"]),
        messages_path=Path(paths["messages"]),
        art_path=Path(paths["art"]),
        special_days_path=Path(paths["special_days"]),
        greeting_history_path=Path(paths["greeting_history"]),
        message_history_path=Path(paths["message_history"]),
        art_history_path=Path(paths["art_history"]),
    )
    art_text = get_art_text(selection["art_key"], art_path=Path(paths["art"]))
    card_text = format_card(
        selection["greeting"],
        weather,
        selection["message_text"],
        art_text=art_text,
        lucky_number=config.get("lucky_number"),
        width=config.get("card_width", DEFAULT_WIDTH),
        border=str(config.get("border", DEFAULT_BORDER)),
    )
    write_output(card_text, output=output)

    LOGGER.info(
        "run summary: version=%s mode=%s time_of_day=%s weather=%s/%s/%s message_id=%s art_key=%s special_date_type=%s",
        config.get("version"),
        config.get("mode", "production"),
        time_of_day,
        weather.get("category"),
        weather.get("wind_mph"),
        weather.get("rain_percent"),
        selection["message_id"],
        selection["art_key"],
        special_day.get("type") if special_day else None,
    )

    return {
        "card_text": card_text,
        "time_of_day": time_of_day,
        "weather": weather,
        "message_id": selection["message_id"],
        "art_key": selection["art_key"],
        "special_date_type": str(special_day.get("type")) if special_day else None,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Weather Gift card.")
    parser.add_argument("--mode", choices=("production", "test"), help="Run mode.")
    parser.add_argument("--config", dest="config_path", help="Optional config JSON path.")
    parser.add_argument("--now", help="Optional ISO timestamp for testing.")
    parser.add_argument(
        "--reset-fixtures",
        action="store_true",
        help="Reset test fixture rotation before running.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        current_time = datetime.fromisoformat(args.now) if args.now else None
        config, warnings = load_config(args.config_path, mode=args.mode)
        for warning in warnings:
            LOGGER.warning("startup warning: %s", warning)
        LOGGER.info(
            "startup: version=%s mode=%s width=%s border=%s",
            config.get("version"),
            config.get("mode"),
            config.get("card_width"),
            config.get("border"),
        )
        if args.reset_fixtures and config.get("weather_fixture_index_path"):
            reset_fixture_index(config["weather_fixture_index_path"])
        run_once(
            now=current_time,
            mode=config["mode"],
            config_path=args.config_path,
            reset_fixtures=args.reset_fixtures,
        )
    except ConfigError as exc:
        LOGGER.error("startup failed: %s", exc)
        return 1
    except ValueError as exc:
        LOGGER.error("startup failed: invalid --now value: %s", exc)
        return 1

    return 0


def _get_weather_for_run(
    *,
    time_of_day: str,
    mode: str,
    fetcher: Callable[[], dict[str, Any]] | None,
    fixture_path: str | None,
    fixture_root: str | None,
    fixture_index_path: str | None,
    reset_fixtures: bool,
) -> dict[str, Any]:
    failed = {"value": False}

    def tracked_fetcher() -> dict[str, Any]:
        try:
            if fetcher is not None:
                return fetcher()
            if fixture_path:
                with Path(fixture_path).open("r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if not isinstance(loaded, dict):
                    raise ValueError("weather fixture must contain a JSON object")
                return loaded
            if mode == "test" and fixture_root:
                return load_weather_fixture(
                    time_of_day,
                    fixture_root,
                    index_path=fixture_index_path,
                    reset=reset_fixtures,
                )
            return fetch_noaa_weather()
        except Exception:  # noqa: BLE001
            failed["value"] = True
            raise

    weather = get_weather(fetcher=tracked_fetcher)
    if failed["value"] or (mode == "test" and fixture_root and not weather):
        return {**weather, "unavailable": True}
    return weather

if __name__ == "__main__":
    raise SystemExit(main())
