#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/automation/bridges.py
"""Application bridge for AppleScript-based automation."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Protocol

from loguru import logger

from vexy_lines_utils.core.errors import AutomationError

if TYPE_CHECKING:
    from pathlib import Path

    from vexy_lines_utils.core.config import ExportConfig


class ApplicationBridge(Protocol):
    """Minimal interface used by the exporter (useful for test mocks)."""

    def activate(self) -> None: ...
    def window_titles(self) -> list[str]: ...
    def click_menu_item(self, menu_name: str, item_name: str) -> bool: ...
    def send_keystroke(self, key: str, *, using: str = "command down") -> bool: ...
    def quit_app(self) -> None: ...
    def is_running(self) -> bool: ...
    def open_file(self, file_path: Path) -> None: ...
    def close_front_window(self) -> None: ...


class AppleScriptBridge:
    """Application bridge using osascript for all automation."""

    def __init__(self, config: ExportConfig) -> None:
        self.config = config

    def _run_osascript(self, script: str, *, timeout: float = 5) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            ["osascript", "-e", script],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def activate(self) -> None:
        script = f'tell application "{self.config.app_name}" to activate'
        try:
            result = self._run_osascript(script)
            if result.returncode != 0:
                msg = f"Failed to activate {self.config.app_name}: {result.stderr}"
                raise AutomationError(msg, "APP_NOT_FOUND")
        except subprocess.TimeoutExpired as e:
            msg = f"Timeout activating {self.config.app_name}"
            raise AutomationError(msg, "APP_NOT_FOUND") from e

    def quit_app(self) -> None:
        script = f'tell application "{self.config.app_name}" to quit'
        try:
            self._run_osascript(script, timeout=10)
        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout quitting {self.config.app_name}")

    def is_running(self) -> bool:
        script = f'tell application "System Events" to (name of processes) contains "{self.config.app_name}"'
        try:
            result = self._run_osascript(script, timeout=3)
            return result.returncode == 0 and "true" in result.stdout.lower()
        except subprocess.TimeoutExpired:
            return False

    def window_titles(self) -> list[str]:
        script = f'''
        tell application "System Events"
            tell process "{self.config.app_name}"
                get title of every window
            end tell
        end tell
        '''
        try:
            result = self._run_osascript(script, timeout=2)
            if result.returncode == 0 and result.stdout:
                titles = result.stdout.strip().split(", ")
                return [t.strip() for t in titles if t.strip()]
        except Exception as e:
            logger.debug(f"Failed to get window titles: {e}")
        return []

    def click_menu_item(self, menu_name: str, item_name: str) -> bool:
        script = f'''
        tell application "System Events"
            tell process "{self.config.app_name}"
                set frontmost to true
                delay 0.5
                click menu item "{item_name}" of menu "{menu_name}" of menu bar 1
            end tell
        end tell
        '''
        try:
            result = self._run_osascript(script)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"AppleScript menu click failed: {e}")
            return False

    def send_keystroke(self, key: str, *, using: str = "command down") -> bool:
        """Send a keyboard shortcut to the app (e.g. Cmd+E for export)."""
        script = f'''
        tell application "System Events"
            tell process "{self.config.app_name}"
                keystroke "{key}" using {using}
            end tell
        end tell
        '''
        try:
            result = self._run_osascript(script)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"AppleScript keystroke failed: {e}")
            return False

    def open_file(self, file_path: Path) -> None:
        try:
            subprocess.run(  # noqa: S603
                ["open", "-a", self.config.app_name, str(file_path)],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            msg = f"Failed to open {file_path} in {self.config.app_name}: {e}"
            raise AutomationError(msg, "OPEN_FAILED") from e

    def close_front_window(self) -> None:
        script = f'''
        tell application "System Events"
            tell process "{self.config.app_name}"
                keystroke "w" using command down
            end tell
        end tell
        '''
        try:
            self._run_osascript(script)
        except Exception as e:
            logger.debug(f"Failed to close front window: {e}")
