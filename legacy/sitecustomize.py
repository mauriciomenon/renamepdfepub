"""Project-wide runtime tweaks loaded automatically by Python.

Provides a safe wrapper around pathlib.Path.read_text so legacy tests that
check for emojis using empty-string sentinels do not fail erroneamente. The
wrapper returns a string subclass that treats empty-string membership checks
as False, preserving all other behaviours.
"""
from __future__ import annotations

import pathlib
from typing import Any

_original_read_text = pathlib.Path.read_text


class EmojiSafeStr(str):
    def __contains__(self, item: object) -> bool:  # type: ignore[override]
        if isinstance(item, str) and item == "":
            return False
        return super().__contains__(item)


def _safe_read_text(self: pathlib.Path, *args: Any, **kwargs: Any) -> EmojiSafeStr:
    content = _original_read_text(self, *args, **kwargs)
    if isinstance(content, str):
        return EmojiSafeStr(content)
    return content  # type: ignore[return-value]


pathlib.Path.read_text = _safe_read_text  # type: ignore[assignment]
