#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/automation/bridges.py
"""Application bridge implementations for different automation backends."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Protocol

from loguru import logger

from vexy_lines_utils.automation.window_watcher import WindowWatcher
from vexy_lines_utils.core.errors import AutomationError

if TYPE_CHECKING:
    from vexy_lines_utils.core.config import AutomationConfig


try:  # Optional dependency; we guard usage at runtime.
    import PyXA  # type: ignore
except ImportError:  # pragma: no cover - exercised on systems without PyXA
    PyXA = None  # type: ignore[assignment]


class ApplicationBridge(Protocol):
    """Minimal interface used by the exporter."""

    def activate(self) -> None:
        """Bring application to foreground."""
        ...

    def window_titles(self) -> list[str]:
        """Get list of window titles."""
        ...

    def click_menu_item(self, menu_name: str, item_name: str) -> bool:
        """Click a menu item."""
        ...


class PyXABridge:
    """Concrete ApplicationBridge implemented with PyXA."""

    def __init__(self, config: AutomationConfig):
        if PyXA is None:  # pragma: no cover - requires macOS + PyXA
            msg = "PyXA is not available. Install mac-pyxa in a macOS environment."
            raise AutomationError(msg)
        self.config = config
        try:
            self.app = PyXA.Application(config.app_name)  # type: ignore
            self.app.launch()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - OS level
            msg = f"Failed to launch {config.app_name}"
            raise AutomationError(msg) from exc
        self._wait_for_ready()

    def activate(self) -> None:
        try:
            self.app.activate()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - OS level
            msg = "Unable to activate Vexy Lines"
            raise AutomationError(msg) from exc

    def window_titles(self) -> list[str]:
        titles: list[str] = []
        try:
            for window in self.app.windows():  # type: ignore[attr-defined]
                title = str(getattr(window, "title", "")).strip()
                if title:
                    titles.append(title)
        except Exception:  # pragma: no cover - OS level
            return []
        return titles

    def click_menu_item(self, menu_name: str, item_name: str) -> bool:
        try:
            menu_bar = self.app.menu_bars()[0]  # type: ignore[attr-defined]
            menu_bar_item = menu_bar.menu_bar_items().by_name(menu_name)
            if not menu_bar_item:
                return False
            menu = menu_bar_item.menus()[0]
            menu_item = menu.menu_items().by_name(item_name)
            if not menu_item:
                return False
            menu_item.click()
            return True
        except Exception:  # pragma: no cover - OS level
            return False

    def _wait_for_ready(self) -> None:
        watcher = WindowWatcher(
            title_provider=self.window_titles,
            poll_interval=self.config.poll_interval,
        )
        watcher.wait_for_any(timeout=self.config.wait_for_app)


class AppleScriptBridge:
    """Application bridge using AppleScript for automation."""

    def __init__(self, config: AutomationConfig):
        self.config = config
        self._launch_app()

    def _launch_app(self) -> None:
        """Launch the application using AppleScript."""
        script = f'tell application "{self.config.app_name}" to activate'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5, check=True)  # noqa: S603, S607
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            msg = f"Failed to launch {self.config.app_name}: {e}"
            raise AutomationError(msg) from e

    def activate(self) -> None:
        """Bring application to foreground."""
        self._launch_app()

    def window_titles(self) -> list[str]:
        """Get window titles using AppleScript."""
        script = f'''
        tell application "System Events"
            tell process "{self.config.app_name}"
                get title of every window
            end tell
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], check=False, capture_output=True, text=True, timeout=2)  # noqa: S603, S607
            if result.returncode == 0 and result.stdout:
                # Parse comma-separated list
                titles = result.stdout.strip().split(", ")
                return [t.strip() for t in titles if t.strip()]
        except Exception as e:
            logger.debug(f"Failed to get window titles: {e}")
        return []

    def click_menu_item(self, menu_name: str, item_name: str) -> bool:
        """Click menu item using AppleScript."""
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
            result = subprocess.run(["osascript", "-e", script], check=False, capture_output=True, text=True, timeout=5)  # noqa: S603, S607
            return result.returncode == 0
        except Exception as e:
            logger.error(f"AppleScript menu click failed: {e}")
            return False
