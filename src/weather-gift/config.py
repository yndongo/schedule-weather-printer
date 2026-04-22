from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from weather_gift.content import (
    ART_PATH,
    ART_HISTORY_PATH,
    GREETINGS_PATH,
    GREETING_HISTORY_PATH,
    MESSAGES_PATH,
    MESSAGE_HISTORY_PATH,
    SPECIAL_DAYS_PATH,
)
from weather_gift.format import DEFAULT_BORDER, DEFAULT_WIDTH

DEFAULT_VERSION = "0.1.0"
DEFAULT_VERSION_FILENAME = "VERSION.txt"
DEFAULT_CONFIG_FILENAME = "config.json"
DEFAULT_TEST_CONFIG_FILENAME = "config.test.json"
VALID_MODES = {"production", "test"}

DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "production",
    "card_width": DEFAULT_WIDTH,
    "border": DEFAULT_BORDER,
    "lucky_number": None,
    "weather_fixture_path": None,
    "weather_fixture_root": None,
    "weather_fixture_index_path": None,
    "paths": {
        "greetings": str(GREETINGS_PATH),
        "messages": str(MESSAGES_PATH),
        "art": str(ART_PATH),
        "special_days": str(SPECIAL_DAYS_PATH),
        "greeting_history": str(GREETING_HISTORY_PATH),
        "message_history": str(MESSAGE_HISTORY_PATH),
        "art_history": str(ART_HISTORY_PATH),
    },
}

REQUIRED_PATH_KEYS = ("greetings", "messages", "art", "special_days")
OPTIONAL_PATH_KEYS = ("greeting_history", "message_history", "art_history")


class ConfigError(Exception):
    pass


def load_config(
    config_path: str | Path | None = None,
    *,
    mode: str | None = None,
    repo_root: str | Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    config = deepcopy(DEFAULT_CONFIG)

    if config_path is not None:
        config = merge_config(config, _read_config_file(Path(config_path)))
    else:
        base_path = root / DEFAULT_CONFIG_FILENAME
        if base_path.is_file():
            config = merge_config(config, _read_config_file(base_path))
        if mode == "test":
            test_path = root / DEFAULT_TEST_CONFIG_FILENAME
            if test_path.is_file():
                config = merge_config(config, _read_config_file(test_path))

    if mode:
        config["mode"] = str(mode).strip().lower()

    validated_config, warnings = validate_config(config, repo_root=root)
    return validated_config, warnings


def validate_config(
    config: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    validated = deepcopy(DEFAULT_CONFIG)
    validated = merge_config(validated, config)
    warnings: list[str] = []

    mode = str(validated.get("mode", "")).strip().lower()
    if mode not in VALID_MODES:
        raise ConfigError(f"mode must be one of {sorted(VALID_MODES)}")
    validated["mode"] = mode

    try:
        card_width = int(validated.get("card_width", DEFAULT_WIDTH))
    except (TypeError, ValueError) as exc:
        raise ConfigError("card_width must be an integer") from exc
    if card_width < 8:
        raise ConfigError("card_width must be at least 8")
    validated["card_width"] = card_width

    border = str(validated.get("border", DEFAULT_BORDER) or DEFAULT_BORDER)
    if len(border) < 4:
        warnings.append("border is very short; using configured value anyway")
    validated["border"] = border

    lucky_number = validated.get("lucky_number")
    if lucky_number is not None:
        try:
            lucky_number = int(lucky_number)
        except (TypeError, ValueError) as exc:
            raise ConfigError("lucky_number must be an integer when provided") from exc
        if not 1 <= lucky_number <= 99:
            warnings.append("lucky_number is outside 1-99; formatter will clamp it")
        validated["lucky_number"] = lucky_number
    elif mode == "test":
        warnings.append("test mode has no fixed lucky_number; using default test value")
        validated["lucky_number"] = 7

    paths = validated.get("paths")
    if not isinstance(paths, dict):
        raise ConfigError("paths must be a JSON object")

    normalized_paths: dict[str, str] = {}
    for key in REQUIRED_PATH_KEYS:
        value = str(paths.get(key, "")).strip()
        if not value:
            raise ConfigError(f"paths.{key} is required")
        normalized_paths[key] = value
        if not Path(value).is_file():
            raise ConfigError(f"required file not found: {value}")

    for key in OPTIONAL_PATH_KEYS:
        value = str(paths.get(key, "")).strip()
        if not value:
            warnings.append(f"paths.{key} missing; using default path")
            value = str(DEFAULT_CONFIG["paths"][key])
        normalized_paths[key] = value

    validated["paths"] = normalized_paths

    for key in ("weather_fixture_path", "weather_fixture_root", "weather_fixture_index_path"):
        value = validated.get(key)
        if value in ("", None):
            validated[key] = None
        else:
            validated[key] = str(value)

    if mode == "test" and not validated["weather_fixture_path"] and not validated["weather_fixture_root"]:
        warnings.append("test mode has no weather fixture configured; live fetch will be used unless overridden")
    if validated["weather_fixture_root"] and not Path(validated["weather_fixture_root"]).exists():
        warnings.append("weather_fixture_root does not exist yet; test fixture rotation will fall back safely")
    if validated["weather_fixture_path"] and not Path(validated["weather_fixture_path"]).is_file():
        warnings.append("weather_fixture_path does not exist; weather will fall back safely")

    validated["version"] = get_version(root)
    return validated, warnings


def get_version(repo_root: str | Path | None = None) -> str:
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    git_version = _read_git_version(root)
    if git_version is not None:
        return git_version

    file_version = read_version_file(root / DEFAULT_VERSION_FILENAME)
    if file_version is not None:
        return file_version

    return DEFAULT_VERSION


def read_version_file(path: str | Path) -> str | None:
    version_path = Path(path)
    try:
        value = version_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return value or None


def merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_config_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config file is not valid json: {path}") from exc

    if not isinstance(loaded, dict):
        raise ConfigError("config file must contain a JSON object")
    return loaded


def _read_git_version(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    value = result.stdout.strip()
    return value or None


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
