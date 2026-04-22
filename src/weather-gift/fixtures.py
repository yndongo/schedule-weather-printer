from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TIME_OF_DAY_VALUES = ("morning", "afternoon", "night")
DEFAULT_INDEX_FILENAME = "fixture_index.json"


def load_weather_fixture(
    time_of_day: str,
    fixture_root: str | Path,
    *,
    index_path: str | Path | None = None,
    reset: bool = False,
) -> dict[str, Any]:
    root_path = Path(fixture_root)
    state_path = Path(index_path) if index_path is not None else root_path / DEFAULT_INDEX_FILENAME
    normalized_time_of_day = _normalize_time_of_day(time_of_day)

    if reset:
        reset_fixture_index(state_path, time_of_day=normalized_time_of_day)

    fixture_files = _get_fixture_files(root_path, normalized_time_of_day)
    if not fixture_files:
        return {}

    state = _load_index_state(state_path)
    current_index = int(state.get(normalized_time_of_day, 0))
    selected_index = current_index % len(fixture_files)
    selected_path = fixture_files[selected_index]
    fixture_payload = _load_fixture_file(selected_path)

    state[normalized_time_of_day] = (selected_index + 1) % len(fixture_files)
    _save_index_state(state_path, state)
    return fixture_payload


def reset_fixture_index(
    index_path: str | Path,
    *,
    time_of_day: str | None = None,
) -> None:
    state_path = Path(index_path)
    state = _load_index_state(state_path)

    if time_of_day is None:
        state = _empty_index_state()
    else:
        state[_normalize_time_of_day(time_of_day)] = 0

    _save_index_state(state_path, state)


def _get_fixture_files(root_path: Path, time_of_day: str) -> list[Path]:
    fixture_dir = root_path / time_of_day
    if not fixture_dir.is_dir():
        return []
    return sorted(path for path in fixture_dir.glob("*.json") if path.is_file())


def _load_fixture_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def _load_index_state(path: Path) -> dict[str, int]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return _empty_index_state()

    if not isinstance(payload, dict):
        return _empty_index_state()

    state = _empty_index_state()
    for time_of_day in TIME_OF_DAY_VALUES:
        value = payload.get(time_of_day, 0)
        try:
            state[time_of_day] = max(0, int(value))
        except (TypeError, ValueError):
            state[time_of_day] = 0
    return state


def _save_index_state(path: Path, state: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)


def _empty_index_state() -> dict[str, int]:
    return {time_of_day: 0 for time_of_day in TIME_OF_DAY_VALUES}


def _normalize_time_of_day(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in TIME_OF_DAY_VALUES:
        return normalized
    return "morning"
