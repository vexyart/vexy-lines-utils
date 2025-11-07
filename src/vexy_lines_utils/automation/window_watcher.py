#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/automation/window_watcher.py
"""Window monitoring utilities."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.core.errors import AutomationError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


@dataclass
class WindowWatcher:
    """Polls Vexy Lines windows until a condition is met."""

    title_provider: Callable[[], Sequence[str]]
    poll_interval: float = 0.2

    def get_current_state(self) -> str:
        """Get current window state for diagnostics."""
        titles = self.title_provider()
        if not titles:
            return "No windows visible"
        return f"Windows: {', '.join(repr(t) for t in titles)}"

    def wait_for_contains(self, needle: str, *, present: bool, timeout: float) -> None:
        """Wait for a window title containing needle to appear/disappear.

        Args:
            needle: String to search for in window titles
            present: True to wait for appearance, False for disappearance
            timeout: Maximum time to wait in seconds

        Raises:
            AutomationError: If timeout is reached
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            titles = self.title_provider()
            has_title = any(needle in title for title in titles)
            if has_title == present:
                return
            time.sleep(self.poll_interval)
        state = "appear" if present else "disappear"
        current_state = self.get_current_state()
        msg = f"Timed out waiting for '{needle}' to {state}. Current state: {current_state}"
        logger.error(msg)
        raise AutomationError(msg, "TIMEOUT")

    def wait_for_any(self, timeout: float) -> None:
        """Wait for any window to appear.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            AutomationError: If no window appears within timeout
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.title_provider():
                return
            time.sleep(self.poll_interval)
        msg = "Timed out waiting for the application window"
        raise AutomationError(msg, "APP_NOT_READY")

    def wait_for_patterns(
        self, patterns: list[str], *, present: bool, timeout: float, case_sensitive: bool = False
    ) -> str | None:
        """Wait for any of the patterns to match in window titles.

        Args:
            patterns: List of patterns to search for
            present: True to wait for appearance, False for disappearance
            timeout: Maximum time to wait in seconds
            case_sensitive: Whether to use case-sensitive matching

        Returns:
            The pattern that matched (if present=True), or None

        Raises:
            AutomationError: If timeout is reached
        """
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            titles = self.title_provider()

            for title in titles:
                for pattern in patterns:
                    if case_sensitive:
                        if pattern in title:
                            if present:
                                return pattern
                    elif pattern.lower() in title.lower():
                        if present:
                            return pattern

            # If we're waiting for absence and no patterns matched, success
            if not present and not any(
                any((p in t if case_sensitive else p.lower() in t.lower()) for p in patterns) for t in titles
            ):
                return None

            time.sleep(self.poll_interval)

        # Timeout
        current_state = f"Windows: {', '.join(repr(t) for t in self.title_provider())}"
        patterns_str = ", ".join(patterns)
        state = "appear" if present else "disappear"
        msg = f"Timed out waiting for any of [{patterns_str}] to {state}. {current_state}"
        logger.error(msg)
        raise AutomationError(msg, "TIMEOUT")
