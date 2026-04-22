from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Sequence, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = REPO_ROOT / "assets"
DATA_DIR = REPO_ROOT / "data"

GREETINGS_PATH = ASSETS_DIR / "greetings.json"
MESSAGES_PATH = ASSETS_DIR / "messages.json"
ART_PATH = ASSETS_DIR / "art.json"
SPECIAL_DAYS_PATH = ASSETS_DIR / "special_days.json"

GREETING_HISTORY_PATH = DATA_DIR / "greeting_history.json"
MESSAGE_HISTORY_PATH = DATA_DIR / "message_history.json"
ART_HISTORY_PATH = DATA_DIR / "art_history.json"

MESSAGE_REPEAT_DAYS = 14
MESSAGE_RETENTION_DAYS = 21
ART_REPEAT_RUNS = 5
TIME_OF_DAY_VALUES = ("morning", "afternoon", "night")

FALLBACK_GREETINGS = {
    "morning": ["good morning!"],
    "afternoon": ["good afternoon!"],
    "night": ["good night!"],
}
FALLBACK_MESSAGES = {
    "morning": [{"id": "morning-fallback", "text": "hope your morning feels light and steady today"}],
    "afternoon": [{"id": "afternoon-fallback", "text": "hope the rest of your day feels a little easier"}],
    "night": [{"id": "night-fallback", "text": "hope tonight gives you some quiet and rest"}],
}
FALLBACK_ART = {
    "fallback": {"key": "neutral-smile", "text": "  .-.\n (   )\n  `-`"},
    "morning": {},
    "afternoon": {},
    "night": {},
}


class ContentSelection(TypedDict):
    greeting: str
    message_id: str
    message_text: str
    art_key: str


def select_content(
    time_of_day: str,
    weather: dict[str, Any],
    *,
    now: datetime | None = None,
    chooser: Callable[[Sequence[Any]], Any] | None = None,
    greetings_path: Path = GREETINGS_PATH,
    messages_path: Path = MESSAGES_PATH,
    art_path: Path = ART_PATH,
    special_days_path: Path = SPECIAL_DAYS_PATH,
    greeting_history_path: Path = GREETING_HISTORY_PATH,
    message_history_path: Path = MESSAGE_HISTORY_PATH,
    art_history_path: Path = ART_HISTORY_PATH,
) -> ContentSelection:
    current_time = now or datetime.now()
    pick = chooser or random.choice
    normalized_time_of_day = _normalize_time_of_day(time_of_day)
    weather_category = str(weather.get("category", "cloudy"))
    special_day = find_special_day(current_time, special_days_path=special_days_path)

    if special_day is not None:
        return select_special_content(
            special_day,
            normalized_time_of_day,
            weather_category,
            now=current_time,
            chooser=pick,
            art_path=art_path,
            history_path=art_history_path,
        )

    greeting = select_greeting(
        normalized_time_of_day,
        now=current_time,
        chooser=pick,
        greetings_path=greetings_path,
        history_path=greeting_history_path,
    )
    message = select_message(
        normalized_time_of_day,
        now=current_time,
        chooser=pick,
        messages_path=messages_path,
        history_path=message_history_path,
    )
    art = select_art(
        normalized_time_of_day,
        weather_category,
        now=current_time,
        chooser=pick,
        art_path=art_path,
        history_path=art_history_path,
    )

    return {
        "greeting": greeting,
        "message_id": message["id"],
        "message_text": message["text"],
        "art_key": art["key"],
    }


def select_special_content(
    special_day: dict[str, Any],
    time_of_day: str,
    weather_category: str,
    *,
    now: datetime,
    chooser: Callable[[Sequence[Any]], Any],
    art_path: Path,
    history_path: Path,
) -> ContentSelection:
    special_type = str(special_day.get("type", "special")).strip().lower() or "special"
    tags = _build_special_tags(special_day, now)
    greeting = _render_special_text(
        special_day.get("greeting"),
        tags,
        fallback=_default_special_greeting(time_of_day, special_type, tags),
    )
    message_text = _render_special_text(
        special_day.get("message"),
        tags,
        fallback=_default_special_message(special_type, tags),
    )
    message_id = str(special_day.get("id") or f"special-{special_type}-{_special_day_id_suffix(special_day)}")

    art_key = str(special_day.get("art", "")).strip()
    if art_key:
        return {
            "greeting": greeting,
            "message_id": message_id,
            "message_text": message_text,
            "art_key": art_key,
        }

    art = select_art(
        time_of_day,
        weather_category,
        now=now,
        chooser=chooser,
        art_path=art_path,
        history_path=history_path,
    )
    return {
        "greeting": greeting,
        "message_id": message_id,
        "message_text": message_text,
        "art_key": art["key"],
    }


def select_greeting(
    time_of_day: str,
    *,
    now: datetime,
    chooser: Callable[[Sequence[Any]], Any],
    greetings_path: Path,
    history_path: Path,
) -> str:
    greetings = load_greetings(greetings_path)
    options = greetings.get(time_of_day, FALLBACK_GREETINGS["morning"])
    history = _load_history(history_path)
    last_greeting = history[-1]["value"] if history else None

    available = [greeting for greeting in options if greeting != last_greeting]
    selected = chooser(available or options)

    _save_history(
        history_path,
        [{"timestamp": now.isoformat(), "value": selected}],
    )
    return selected


def select_message(
    time_of_day: str,
    *,
    now: datetime,
    chooser: Callable[[Sequence[Any]], Any],
    messages_path: Path,
    history_path: Path,
) -> dict[str, str]:
    messages = load_messages(messages_path)
    options = messages.get(time_of_day, FALLBACK_MESSAGES["morning"])
    history = _load_history(history_path)

    retention_cutoff = now - timedelta(days=MESSAGE_RETENTION_DAYS)
    recent_cutoff = now - timedelta(days=MESSAGE_REPEAT_DAYS)

    retained_history = [
        entry
        for entry in history
        if _parse_timestamp(entry.get("timestamp")) >= retention_cutoff
    ]
    blocked_ids = {
        entry["message_id"]
        for entry in retained_history
        if _parse_timestamp(entry.get("timestamp")) >= recent_cutoff
        and "message_id" in entry
    }

    available = [message for message in options if message["id"] not in blocked_ids]
    selected = chooser(available or options)

    retained_history.append(
        {"timestamp": now.isoformat(), "message_id": selected["id"]}
    )
    _save_history(history_path, retained_history)
    return selected


def select_art(
    time_of_day: str,
    weather_category: str,
    *,
    now: datetime,
    chooser: Callable[[Sequence[Any]], Any],
    art_path: Path,
    history_path: Path,
) -> dict[str, str]:
    art_catalog = load_art(art_path)
    bucket = art_catalog.get(time_of_day, {})
    fallback_art = art_catalog["fallback"]
    options = bucket.get(weather_category) or bucket.get("cloudy") or [fallback_art]

    history = _load_history(history_path)
    recent_history = history[-ART_REPEAT_RUNS:]
    blocked_keys = {entry["art_key"] for entry in recent_history if "art_key" in entry}

    available = [art for art in options if art["key"] not in blocked_keys]
    selected = chooser(available or options)

    updated_history = recent_history + [
        {"timestamp": now.isoformat(), "art_key": selected["key"]}
    ]
    _save_history(history_path, updated_history[-ART_REPEAT_RUNS:])
    return selected


def get_art_text(art_key: str, *, art_path: Path = ART_PATH) -> str:
    art_catalog = load_art(art_path)
    fallback_art = art_catalog["fallback"]

    if art_key == fallback_art["key"]:
        return fallback_art["text"]

    for time_of_day in TIME_OF_DAY_VALUES:
        for entries in art_catalog.get(time_of_day, {}).values():
            for art in entries:
                if art.get("key") == art_key:
                    return str(art.get("text", fallback_art["text"]))

    extras = art_catalog.get("fallback", {}).get("extras", [])
    for art in extras:
        if art.get("key") == art_key:
            return str(art.get("text", fallback_art["text"]))

    return fallback_art["text"]


def load_greetings(path: Path = GREETINGS_PATH) -> dict[str, list[str]]:
    data = _load_json_file(path, FALLBACK_GREETINGS)
    return {
        "morning": _normalize_greeting_list(data.get("morning"), FALLBACK_GREETINGS["morning"]),
        "afternoon": _normalize_greeting_list(data.get("afternoon"), FALLBACK_GREETINGS["afternoon"]),
        "night": _normalize_greeting_list(data.get("night"), FALLBACK_GREETINGS["night"]),
    }


def load_messages(path: Path = MESSAGES_PATH) -> dict[str, list[dict[str, str]]]:
    data = _load_json_file(path, FALLBACK_MESSAGES)
    return {
        "morning": _normalize_message_list(data.get("morning"), FALLBACK_MESSAGES["morning"]),
        "afternoon": _normalize_message_list(data.get("afternoon"), FALLBACK_MESSAGES["afternoon"]),
        "night": _normalize_message_list(data.get("night"), FALLBACK_MESSAGES["night"]),
    }


def load_art(path: Path = ART_PATH) -> dict[str, Any]:
    data = _load_json_file(path, FALLBACK_ART)
    fallback_raw = data.get("fallback", {})
    fallback_art = _normalize_art_entry(fallback_raw, FALLBACK_ART["fallback"])

    extras: list[dict[str, str]] = []
    if isinstance(fallback_raw, dict):
        raw_extras = fallback_raw.get("extras", [])
        if isinstance(raw_extras, list):
            extras = [
                _normalize_art_entry(item, fallback_art)
                for item in raw_extras
                if isinstance(item, dict)
            ]

    catalog: dict[str, Any] = {
        "fallback": {**fallback_art, "extras": extras},
        "morning": {},
        "afternoon": {},
        "night": {},
    }

    for time_of_day in TIME_OF_DAY_VALUES:
        buckets = data.get(time_of_day, {})
        if not isinstance(buckets, dict):
            buckets = {}
        for category, entries in buckets.items():
            catalog[time_of_day][category] = _normalize_art_list(entries, [fallback_art])

    return catalog


def load_special_days(path: Path = SPECIAL_DAYS_PATH) -> list[dict[str, Any]]:
    data = _load_json_file(path, [])
    if not isinstance(data, list):
        return []

    special_days: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        date_value = str(item.get("date", "")).strip()
        if not date_value:
            continue
        special_days.append(item)
    return special_days


def find_special_day(
    now: datetime,
    *,
    special_days_path: Path = SPECIAL_DAYS_PATH,
) -> dict[str, Any] | None:
    current_date = now.date()
    recurring_match: dict[str, Any] | None = None

    for special_day in load_special_days(special_days_path):
        special_date = str(special_day.get("date", "")).strip()
        parsed_date = _parse_special_date(special_date)
        if parsed_date is None:
            continue

        if len(special_date) == 10 and parsed_date == current_date:
            return special_day
        if len(special_date) == 5 and parsed_date.month == current_date.month and parsed_date.day == current_date.day:
            recurring_match = special_day

    return recurring_match


def _normalize_greeting_list(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        return fallback

    greetings = [str(item).strip() for item in value if str(item).strip()]
    return greetings or fallback


def _normalize_message_list(
    value: Any,
    fallback: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        return fallback

    messages: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        message_id = str(item.get("id", "")).strip()
        text = str(item.get("text", "")).strip()
        if message_id and text:
            messages.append({"id": message_id, "text": text})

    return messages or fallback


def _normalize_art_list(value: Any, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        return fallback

    art_entries = [
        _normalize_art_entry(item, fallback[0])
        for item in value
        if isinstance(item, dict)
    ]
    return art_entries or fallback


def _normalize_art_entry(value: Any, fallback: dict[str, str]) -> dict[str, str]:
    if not isinstance(value, dict):
        return fallback

    art_key = str(value.get("key", "")).strip()
    text = str(value.get("text", "")).rstrip()
    text = text.replace("\\n", "\n")
    if not art_key or not text:
        return fallback
    return {"key": art_key, "text": text}


def _load_json_file(path: Path, fallback: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def _load_history(path: Path) -> list[dict[str, Any]]:
    data = _load_json_file(path, [])
    return data if isinstance(data, list) else []


def _save_history(path: Path, history: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)


def _parse_timestamp(value: Any) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min


def _parse_special_date(value: str) -> datetime.date | None:
    try:
        if len(value) == 10:
            return datetime.strptime(value, "%Y-%m-%d").date()
        if len(value) == 5:
            month_text, day_text = value.split("-", maxsplit=1)
            month = int(month_text)
            day = int(day_text)
            return datetime(2000, month, day).date()
    except ValueError:
        return None
    return None


def _build_special_tags(special_day: dict[str, Any], now: datetime) -> dict[str, Any]:
    tags = dict(special_day.get("tag", {})) if isinstance(special_day.get("tag"), dict) else {}
    if "name" in tags:
        tags["name"] = str(tags["name"])

    date_value = str(special_day.get("date", "")).strip()
    if len(date_value) == 10:
        try:
            event_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            if "age" not in tags:
                tags["age"] = now.date().year - event_date.year
        except ValueError:
            pass
    return tags


def _render_special_text(value: Any, tags: dict[str, Any], *, fallback: str) -> str:
    if value is None:
        return fallback

    text = str(value).strip()
    if not text:
        return fallback
    try:
        return text.format(**tags)
    except (KeyError, ValueError):
        return text


def _default_special_greeting(
    time_of_day: str,
    special_type: str,
    tags: dict[str, Any],
) -> str:
    name = str(tags.get("name", "")).strip()
    if special_type == "birthday" and name:
        return f"happy birthday, {name}!"
    if special_type == "birthday":
        return "happy birthday!"
    return select_default_greeting(time_of_day)


def _default_special_message(special_type: str, tags: dict[str, Any]) -> str:
    name = str(tags.get("name", "")).strip()
    if special_type == "birthday" and name:
        return f"thinking of you today, {name}"
    if special_type == "birthday":
        return "thinking of you today"
    return "thinking of you today"


def _special_day_id_suffix(special_day: dict[str, Any]) -> str:
    return str(special_day.get("date", "today")).replace(" ", "-").replace("/", "-")


def _normalize_time_of_day(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in TIME_OF_DAY_VALUES:
        return normalized
    return "morning"


def select_default_greeting(time_of_day: str) -> str:
    return FALLBACK_GREETINGS.get(time_of_day, FALLBACK_GREETINGS["morning"])[0]