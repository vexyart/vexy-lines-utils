#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/strategies/menu_trigger.py
"""Smart menu triggering with multiple fallback strategies."""

from __future__ import annotations

import subprocess
import time
from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.core.config import EnhancedAutomationConfig, MenuStrategy

if TYPE_CHECKING:
    from vexy_lines_utils.automation.window_watcher import WindowWatcher

try:
    import PyXA
except ImportError:
    PyXA = None

try:
    import pyautogui
except ImportError:
    pyautogui = None


class SmartMenuTrigger:
    """Smart menu triggering with multiple fallback strategies."""

    def __init__(self, config: EnhancedAutomationConfig):
        self.config = config

    def trigger_export(self, window_watcher: WindowWatcher) -> bool:
        """Try multiple strategies to trigger the Export menu.

        Args:
            window_watcher: Window watcher to verify dialog appearance

        Returns:
            True if successful, False otherwise
        """
        for strategy in self.config.menu_strategies:
            logger.debug(f"Trying menu strategy: {strategy.value}")

            try:
                if strategy == MenuStrategy.KEYBOARD_SHORTCUT and self.config.export_shortcut:
                    if self._try_keyboard_shortcut():
                        # Verify dialog appeared
                        window_watcher.wait_for_patterns(self.config.export_window_patterns, present=True, timeout=3.0)
                        logger.success(f"Export triggered via {strategy.value}")
                        return True

                elif strategy == MenuStrategy.APPLESCRIPT:
                    if self._try_applescript():
                        window_watcher.wait_for_patterns(self.config.export_window_patterns, present=True, timeout=3.0)
                        logger.success(f"Export triggered via {strategy.value}")
                        return True

                elif strategy == MenuStrategy.PYXA and PyXA:
                    if self._try_pyxa_menu():
                        window_watcher.wait_for_patterns(self.config.export_window_patterns, present=True, timeout=3.0)
                        logger.success(f"Export triggered via {strategy.value}")
                        return True

            except Exception as e:
                logger.warning(f"Strategy {strategy.value} failed: {e}")
                continue

        logger.error("All menu strategies failed")
        return False

    def _try_keyboard_shortcut(self) -> bool:
        """Try using keyboard shortcut."""
        if not self.config.export_shortcut or not pyautogui:
            return False

        try:
            pyautogui.hotkey(*self.config.export_shortcut)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.debug(f"Keyboard shortcut failed: {e}")
            return False

    def _try_applescript(self) -> bool:
        """Try using AppleScript to click menu."""
        menu_path = list(self.config.export_menu)
        script = f'''
        tell application "System Events"
            tell process "{self.config.app_name}"
                set frontmost to true
                delay 0.5
                click menu item "{menu_path[-1]}" of menu "{menu_path[-2]}" of menu bar 1
            end tell
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], check=False, capture_output=True, text=True, timeout=5)  # noqa: S603, S607
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"AppleScript failed: {e}")
            return False

    def _try_pyxa_menu(self) -> bool:
        """Try using PyXA menu click (original method)."""
        if not PyXA:
            return False

        try:
            app = PyXA.Application(self.config.app_name)
            menu_bar = app.menu_bars()[0]
            menu_name, item_name = self.config.export_menu
            menu_bar_item = menu_bar.menu_bar_items().by_name(menu_name)
            if not menu_bar_item:
                return False
            menu = menu_bar_item.menus()[0]
            menu_item = menu.menu_items().by_name(item_name)
            if not menu_item:
                return False
            menu_item.click()
            return True
        except Exception as e:
            logger.debug(f"PyXA menu click failed: {e}")
            return False
