#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/automation/ui_actions.py
"""UI automation actions for keyboard and clipboard operations."""

from __future__ import annotations

from vexy_lines_utils.core.errors import AutomationError

try:  # Optional dependency for UI automation.
    import pyautogui  # type: ignore
except ImportError:  # pragma: no cover - exercised on CI
    pyautogui = None  # type: ignore[assignment]

try:  # Clipboard helper.
    import pyperclip  # type: ignore
except ImportError:  # pragma: no cover - exercised on CI
    pyperclip = None  # type: ignore[assignment]


class UIActions:
    """Keyboard and clipboard automation helper."""

    def __init__(self, *, dry_run: bool = False):
        self.dry_run = dry_run
        self._pyautogui = pyautogui
        self._pyperclip = pyperclip
        self.recorded: list[str] = []
        if not dry_run:
            if self._pyautogui is None or self._pyperclip is None:
                msg = "pyautogui-ng and pyperclip are required for automation."
                raise AutomationError(msg)
            self._pyautogui.PAUSE = 0  # type: ignore[attr-defined]

    def press(self, key: str) -> None:
        """Press a single key.

        Args:
            key: Key to press (e.g., 'enter', 'escape')
        """
        self._record(f"press:{key}")
        if not self.dry_run:
            self._pyautogui.press(key)  # type: ignore[union-attr]

    def hotkey(self, *keys: str) -> None:
        """Press a key combination.

        Args:
            *keys: Keys to press together (e.g., 'command', 'shift', 'g')
        """
        combo = "+".join(keys)
        self._record(f"hotkey:{combo}")
        if not self.dry_run:
            self._pyautogui.hotkey(*keys)  # type: ignore[union-attr]

    def copy_text(self, text: str) -> None:
        """Copy text to clipboard.

        Args:
            text: Text to copy
        """
        self._record(f"copy:{text}")
        if not self.dry_run:
            self._pyperclip.copy(text)  # type: ignore[union-attr]

    def _record(self, action: str) -> None:
        """Record an action for debugging/replay."""
        self.recorded.append(action)
