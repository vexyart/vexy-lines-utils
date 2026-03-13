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
        titles = self.title_provider()
        if not titles:
            return "No windows visible"
        return f"Windows: {', '.join(repr(t) for t in titles)}"

    def wait_for_contains(self, needle: str, *, present: bool, timeout: float) -> None:
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
        raise AutomationError(msg, "WINDOW_TIMEOUT")

    def wait_for_any(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.title_provider():
                return
            time.sleep(self.poll_interval)
        msg = "Timed out waiting for the application window"
        raise AutomationError(msg, "APP_NOT_FOUND")
