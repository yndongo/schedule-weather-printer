from __future__ import annotations

import sys
from typing import TextIO


def write_output(
    card_text: str,
    *,
    output: TextIO | None = None,
) -> None:
    destination = output or sys.stdout
    destination.write(card_text)
    destination.write("\n")
    destination.flush()
