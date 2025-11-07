#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/strategies/dialog_handler.py
"""Smart save dialog handling with multiple strategies."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.core.config import DialogStrategy, EnhancedAutomationConfig

if TYPE_CHECKING:
    from vexy_lines_utils.automation.window_watcher import WindowWatcher

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


class SmartDialogHandler:
    """Smart save dialog handling with multiple strategies."""

    def __init__(self, config: EnhancedAutomationConfig):
        self.config = config

    def handle_save_dialog(self, file_path: Path, window_watcher: WindowWatcher) -> bool:
        """Try multiple strategies to handle save dialog.

        Args:
            file_path: Path to the file being exported
            window_watcher: Window watcher to verify dialog closure

        Returns:
            True if successful, False otherwise
        """
        folder_path = str(file_path.parent)
        pdf_name = file_path.with_suffix(".pdf").name

        for _idx, strategy in enumerate(self.config.dialog_strategies):
            logger.debug(f"Trying dialog strategy: {strategy.value}")

            try:
                if strategy == DialogStrategy.APPLESCRIPT_DIALOG:
                    if self._try_applescript(folder_path, pdf_name):
                        # Wait for dialog to close
                        window_watcher.wait_for_patterns(self.config.save_window_patterns, present=False, timeout=5.0)
                        logger.success(f"Save dialog handled via {strategy.value}")
                        return True

                elif strategy == DialogStrategy.COMMAND_SHIFT_G and pyautogui and pyperclip:
                    if self._try_standard_navigation(folder_path, pdf_name):
                        window_watcher.wait_for_patterns(self.config.save_window_patterns, present=False, timeout=5.0)
                        logger.success(f"Save dialog handled via {strategy.value}")
                        return True

                elif strategy == DialogStrategy.DIRECT_PATH and pyautogui and pyperclip:
                    if self._try_direct_path(folder_path, pdf_name):
                        window_watcher.wait_for_patterns(self.config.save_window_patterns, present=False, timeout=5.0)
                        logger.success(f"Save dialog handled via {strategy.value}")
                        return True

                elif strategy == DialogStrategy.FILENAME_ONLY and pyautogui and pyperclip:
                    if self._try_filename_only(pdf_name):
                        window_watcher.wait_for_patterns(self.config.save_window_patterns, present=False, timeout=5.0)
                        logger.success(f"Save dialog handled via {strategy.value}")
                        return True

            except Exception as e:
                logger.warning(f"Dialog strategy {strategy.value} failed: {e}")
                continue

        logger.error("All dialog strategies failed")
        return False

    def _try_applescript(self, folder_path: str, filename: str) -> bool:
        """Handle save dialog using AppleScript."""
        script = f'''
        tell application "System Events"
            -- Wait for save dialog
            delay 0.5

            -- Try to navigate using Command-Shift-G
            keystroke "g" using {{command down, shift down}}
            delay 0.5

            -- Enter the path
            keystroke "{folder_path}"
            delay 0.2
            keystroke return
            delay 0.5

            -- Enter filename
            keystroke "a" using command down
            delay 0.2
            keystroke "{filename}"
            delay 0.2

            -- Save
            keystroke return
            delay 0.5

            -- Handle potential overwrite dialog
            keystroke return
        end tell
        '''

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"AppleScript dialog handling failed: {e}")
            return False

    def _try_standard_navigation(self, folder_path: str, filename: str) -> bool:
        """Standard Command-Shift-G navigation."""
        if not pyautogui or not pyperclip:
            return False

        try:
            # Navigate to folder
            pyautogui.hotkey("command", "shift", "g")
            time.sleep(0.5)
            pyperclip.copy(folder_path)
            pyautogui.hotkey("command", "v")
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.5)

            # Set filename
            pyautogui.hotkey("command", "a")
            time.sleep(0.2)
            pyperclip.copy(filename)
            pyautogui.hotkey("command", "v")
            time.sleep(0.2)

            # Save
            pyautogui.press("enter")
            time.sleep(0.5)

            # Handle overwrite
            pyautogui.press("enter")

            return True
        except Exception as e:
            logger.debug(f"Standard navigation failed: {e}")
            return False

    def _try_direct_path(self, folder_path: str, filename: str) -> bool:
        """Navigate by typing full path directly."""
        if not pyautogui or not pyperclip:
            return False

        try:
            full_path = str(Path(folder_path) / filename)
            pyperclip.copy(full_path)
            pyautogui.hotkey("command", "a")
            time.sleep(0.2)
            pyautogui.hotkey("command", "v")
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.5)
            # Handle overwrite
            pyautogui.press("enter")
            return True
        except Exception as e:
            logger.debug(f"Direct path failed: {e}")
            return False

    def _try_filename_only(self, filename: str) -> bool:
        """Set just the filename (assume already in right folder)."""
        if not pyautogui or not pyperclip:
            return False

        try:
            pyautogui.hotkey("command", "a")
            time.sleep(0.2)
            pyperclip.copy(filename)
            pyautogui.hotkey("command", "v")
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.5)
            # Handle overwrite
            pyautogui.press("enter")
            return True
        except Exception as e:
            logger.debug(f"Filename only failed: {e}")
            return False
