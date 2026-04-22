from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from weather_gift.content import get_art_text, select_content


class ContentTests(unittest.TestCase):
    def test_select_content_returns_expected_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))

            result = select_content(
                "morning",
                {"category": "sunny"},
                now=datetime(2026, 4, 17, 8, 30),
                chooser=lambda options: options[0],
                **paths,
            )

        self.assertEqual(
            set(result),
            {"greeting", "message_id", "message_text", "art_key"},
        )
        self.assertEqual(result["greeting"], "morning hi")
        self.assertEqual(result["message_id"], "m1")
        self.assertEqual(result["message_text"], "morning message one")
        self.assertEqual(result["art_key"], "sun-a")

    def test_select_content_avoids_immediate_greeting_repeat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))
            now = datetime(2026, 4, 17, 8, 30)

            first = select_content(
                "morning",
                {"category": "sunny"},
                now=now,
                chooser=lambda options: options[0],
                **paths,
            )
            second = select_content(
                "morning",
                {"category": "sunny"},
                now=now + timedelta(minutes=1),
                chooser=lambda options: options[0],
                **paths,
            )

        self.assertEqual(first["greeting"], "morning hi")
        self.assertEqual(second["greeting"], "morning hello")

    def test_select_content_blocks_recent_messages_for_14_days(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))
            history_path = Path(temp_dir) / "message_history.json"
            history_path.write_text(
                json.dumps(
                    [{"timestamp": "2026-04-10T08:30:00", "message_id": "m1"}]
                ),
                encoding="utf-8",
            )

            result = select_content(
                "morning",
                {"category": "sunny"},
                now=datetime(2026, 4, 17, 8, 30),
                chooser=lambda options: options[0],
                **paths,
            )

        self.assertEqual(result["message_id"], "m2")

    def test_select_content_blocks_art_used_in_last_five_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))
            history_path = Path(temp_dir) / "art_history.json"
            history_path.write_text(
                json.dumps(
                    [{"timestamp": f"2026-04-17T08:3{i}:00", "art_key": "sun-a"} for i in range(5)]
                ),
                encoding="utf-8",
            )

            result = select_content(
                "morning",
                {"category": "sunny"},
                now=datetime(2026, 4, 17, 8, 40),
                chooser=lambda options: options[0],
                **paths,
            )

        self.assertEqual(result["art_key"], "sun-b")

    def test_select_content_uses_one_time_special_day_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))
            special_days_path = Path(temp_dir) / "special_days.json"
            special_days_path.write_text(
                json.dumps(
                    [
                        {
                            "date": "2026-04-17",
                            "type": "birthday",
                            "greeting": "happy birthday, {name}!",
                            "message": "Age: {age}",
                            "tag": {"name": "Alex"},
                            "art": "birthday-cake",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            paths["special_days_path"] = special_days_path

            result = select_content(
                "morning",
                {"category": "sunny"},
                now=datetime(2026, 4, 17, 8, 30),
                chooser=lambda options: options[0],
                **paths,
            )

        self.assertEqual(result["greeting"], "happy birthday, Alex!")
        self.assertEqual(result["message_id"], "special-birthday-2026-04-17")
        self.assertEqual(result["message_text"], "Age: 0")
        self.assertEqual(result["art_key"], "birthday-cake")

    def test_select_content_uses_recurring_special_day_and_normal_art_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))
            special_days_path = Path(temp_dir) / "special_days.json"
            special_days_path.write_text(
                json.dumps(
                    [
                        {
                            "date": "04-17",
                            "type": "anniversary",
                            "message": "thinking of us today, {name}",
                            "tag": {"name": "Alex"}
                        }
                    ]
                ),
                encoding="utf-8",
            )
            paths["special_days_path"] = special_days_path

            result = select_content(
                "morning",
                {"category": "sunny"},
                now=datetime(2026, 4, 17, 8, 30),
                chooser=lambda options: options[0],
                **paths,
            )

        self.assertEqual(result["greeting"], "good morning!")
        self.assertEqual(result["message_id"], "special-anniversary-04-17")
        self.assertEqual(result["message_text"], "thinking of us today, Alex")
        self.assertEqual(result["art_key"], "sun-a")

    def test_get_art_text_returns_fallback_when_key_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))

            result = get_art_text("missing", art_path=paths["art_path"])

        self.assertEqual(result, "(fallback art)")

    def test_get_art_text_converts_escaped_newlines_to_multiline_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_content_files(Path(temp_dir))
            paths["art_path"].write_text(
                json.dumps(
                    {
                        "fallback": {"key": "fallback", "text": "(fallback art)"},
                        "morning": {
                            "sunny": [
                                {"key": "sun-a", "text": "line one\\nline two"},
                            ]
                        },
                        "afternoon": {},
                        "night": {},
                    }
                ),
                encoding="utf-8",
            )

            result = get_art_text("sun-a", art_path=paths["art_path"])

        self.assertEqual(result, "line one\nline two")

    def _write_content_files(self, temp_dir: Path) -> dict[str, Path]:
        greetings_path = temp_dir / "greetings.json"
        messages_path = temp_dir / "messages.json"
        art_path = temp_dir / "art.json"
        greeting_history_path = temp_dir / "greeting_history.json"
        message_history_path = temp_dir / "message_history.json"
        art_history_path = temp_dir / "art_history.json"
        special_days_path = temp_dir / "special_days.json"

        greetings_path.write_text(
            json.dumps(
                {
                    "morning": ["morning hi", "morning hello"],
                    "afternoon": ["afternoon hi"],
                    "night": ["night hi"],
                }
            ),
            encoding="utf-8",
        )
        messages_path.write_text(
            json.dumps(
                {
                    "morning": [
                        {"id": "m1", "text": "morning message one"},
                        {"id": "m2", "text": "morning message two"},
                    ],
                    "afternoon": [{"id": "a1", "text": "afternoon message"}],
                    "night": [{"id": "n1", "text": "night message"}],
                }
            ),
            encoding="utf-8",
        )
        art_path.write_text(
            json.dumps(
                {
                    "fallback": {"key": "fallback", "text": "(fallback art)"},
                    "morning": {
                        "sunny": [
                            {"key": "sun-a", "text": "sun a"},
                            {"key": "sun-b", "text": "sun b"},
                        ]
                    },
                    "afternoon": {"sunny": [{"key": "afternoon-sun", "text": "afternoon sun"}]},
                    "night": {"sunny": [{"key": "night-sun", "text": "night sun"}]},
                }
            ),
            encoding="utf-8",
        )
        special_days_path.write_text("[]", encoding="utf-8")

        return {
            "greetings_path": greetings_path,
            "messages_path": messages_path,
            "art_path": art_path,
            "special_days_path": special_days_path,
            "greeting_history_path": greeting_history_path,
            "message_history_path": message_history_path,
            "art_history_path": art_history_path,
        }


if __name__ == "__main__":
    unittest.main()
