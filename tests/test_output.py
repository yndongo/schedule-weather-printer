from __future__ import annotations

import io
import unittest

from weather_gift.output import write_output


class OutputTests(unittest.TestCase):
    def test_write_output_writes_exact_card_text(self) -> None:
        output = io.StringIO()

        write_output("line one\nline two", output=output)

        self.assertEqual(output.getvalue(), "line one\nline two\n")


if __name__ == "__main__":
    unittest.main()
