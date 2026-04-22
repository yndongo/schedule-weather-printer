from __future__ import annotations

import random
import textwrap
from typing import Any

from weather_gift.content import get_art_text

DEFAULT_WIDTH = 32
DEFAULT_BORDER = "-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-="
FALLBACK_WEATHER_TEXT = "data not available now, apologies!"
FALLBACK_ART_TEXT = "  .-.\n (   )\n  `-`"


def format_card(
    greeting: str,
    weather: dict[str, Any] | None,
    message_text: str,
    *,
    art_key: str | None = None,
    art_text: str | None = None,
    lucky_number: int | None = None,
    width: int = DEFAULT_WIDTH,
    border: str = DEFAULT_BORDER,
) -> str:
    card_width = max(8, int(width))
    border_line = build_border(card_width, border)
    weather_block = build_weather_block(weather, lucky_number=lucky_number, width=card_width)
    art_block = build_art_block(
        art_key=art_key,
        art_text=art_text,
        width=card_width,
    )
    message_block = wrap_block(message_text, width=card_width)

    sections = [
        border_line,
        *wrap_block(greeting, width=card_width),
        "",
        *weather_block,
        "",
        *art_block,
        "",
        *message_block,
        border_line,
    ]
    return "\n".join(sections)


def build_border(width: int, pattern: str = DEFAULT_BORDER) -> str:
    border_pattern = pattern or DEFAULT_BORDER
    repeats = (width // len(border_pattern)) + 1
    return (border_pattern * repeats)[:width]


def build_weather_block(
    weather: dict[str, Any] | None,
    *,
    lucky_number: int | None,
    width: int,
) -> list[str]:
    normalized_lucky_number = normalize_lucky_number(lucky_number)
    temperature = _get_weather_temperature(weather)
    wind_mph = _coerce_int(_get_weather_value(weather, "wind_mph"), default=0)
    rain_percent = _coerce_int(_get_weather_value(weather, "rain_percent"), default=0)

    lines = [
        f"Temperature: {format_temperature(temperature)}",
        f"Wind: {wind_mph} mph",
        f"Rain: {rain_percent}%",
        f"Lucky number: {normalized_lucky_number}",
    ]
    wrapped_lines = flatten_wrapped_lines(lines, width=width)

    if weather_is_unavailable(weather):
        wrapped_lines.extend(wrap_block(FALLBACK_WEATHER_TEXT, width=width))

    return wrapped_lines


def build_art_block(
    *,
    art_key: str | None,
    art_text: str | None,
    width: int,
) -> list[str]:
    resolved_art = resolve_art_text(art_key=art_key, art_text=art_text)
    if not art_fits_width(resolved_art, width=width):
        resolved_art = FALLBACK_ART_TEXT
    return center_art_lines(resolved_art, width=width)


def wrap_block(text: str, *, width: int) -> list[str]:
    normalized_text = str(text).strip()
    if not normalized_text:
        return [""]
    return textwrap.wrap(
        normalized_text,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
    ) or [""]


def center_art_lines(art_text: str, *, width: int) -> list[str]:
    lines = str(art_text).splitlines() or [""]
    return [line.center(width) for line in lines]


def flatten_wrapped_lines(lines: list[str], *, width: int) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(wrap_block(line, width=width))
    return wrapped


def resolve_art_text(*, art_key: str | None, art_text: str | None) -> str:
    if art_text:
        return str(art_text)
    if art_key:
        return get_art_text(art_key)
    return FALLBACK_ART_TEXT


def art_fits_width(art_text: str, *, width: int) -> bool:
    lines = str(art_text).splitlines() or [""]
    return all(len(line) <= width for line in lines)


def weather_is_unavailable(weather: dict[str, Any] | None) -> bool:
    if not weather:
        return True
    if bool(weather.get("unavailable")):
        return True
    required_fields = ("wind_mph", "rain_percent")
    return any(field not in weather for field in required_fields)


def normalize_lucky_number(lucky_number: int | None) -> int:
    if lucky_number is None:
        return random.randint(1, 99)
    return max(1, min(99, int(lucky_number)))


def format_temperature(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{int(value)}\N{DEGREE SIGN}"


def _get_weather_value(weather: dict[str, Any] | None, key: str) -> Any:
    if not weather:
        return None
    return weather.get(key)


def _get_weather_temperature(weather: dict[str, Any] | None) -> int | None:
    value = _get_weather_value(weather, "temperature")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
