from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from weather_gift.config import ConfigError, get_version, load_config, read_version_file, validate_config


class ConfigTests(unittest.TestCase):
    def test_validate_config_applies_defaults_and_returns_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = self._write_required_files(root)
            config, warnings = validate_config(
                {
                    "mode": "test",
                    "paths": paths,
                },
                repo_root=root,
            )

        self.assertEqual(config["mode"], "test")
        self.assertEqual(config["lucky_number"], 7)
        self.assertTrue(any("fixed lucky_number" in warning for warning in warnings))
        self.assertTrue(any("no weather fixture configured" in warning for warning in warnings))

    def test_validate_config_raises_for_missing_required_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = self._write_required_files(root)
            paths["messages"] = str(root / "missing-messages.json")

            with self.assertRaises(ConfigError):
                validate_config(
                    {
                        "mode": "production",
                        "paths": paths,
                    },
                    repo_root=root,
                )

    def test_load_config_uses_base_and_test_overlay_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = self._write_required_files(root)
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "card_width": 40,
                        "paths": paths,
                    }
                ),
                encoding="utf-8",
            )
            (root / "config.test.json").write_text(
                json.dumps(
                    {
                        "card_width": 48,
                    }
                ),
                encoding="utf-8",
            )

            config, warnings = load_config(mode="test", repo_root=root)

        self.assertEqual(config["card_width"], 48)
        self.assertEqual(config["mode"], "test")
        self.assertIsInstance(warnings, list)

    def test_get_version_falls_back_to_version_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "VERSION.txt").write_text("1.2.3\n", encoding="utf-8")

            with patch("weather_gift.config.subprocess.run", side_effect=FileNotFoundError):
                version = get_version(root)

        self.assertEqual(version, "1.2.3")

    def test_read_version_file_returns_none_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            version = read_version_file(Path(temp_dir) / "VERSION.txt")

        self.assertIsNone(version)

    def _write_required_files(self, root: Path) -> dict[str, str]:
        greetings = root / "greetings.json"
        messages = root / "messages.json"
        art = root / "art.json"
        special_days = root / "special_days.json"
        greetings.write_text('{"morning":["hi"],"afternoon":["hi"],"night":["hi"]}', encoding="utf-8")
        messages.write_text('{"morning":[{"id":"m1","text":"hello"}],"afternoon":[{"id":"a1","text":"hello"}],"night":[{"id":"n1","text":"hello"}]}', encoding="utf-8")
        art.write_text('{"fallback":{"key":"fallback","text":"x"},"morning":{"sunny":[{"key":"a","text":"x"}]},"afternoon":{"sunny":[{"key":"b","text":"x"}]},"night":{"sunny":[{"key":"c","text":"x"}]}}', encoding="utf-8")
        special_days.write_text("[]", encoding="utf-8")
        return {
            "greetings": str(greetings),
            "messages": str(messages),
            "art": str(art),
            "special_days": str(special_days),
        }


if __name__ == "__main__":
    unittest.main()
