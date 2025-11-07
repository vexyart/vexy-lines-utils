#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/exporters/standard.py
"""Standard Vexy Lines exporter implementation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.automation.bridges import ApplicationBridge, PyXABridge
from vexy_lines_utils.core.errors import AutomationError
from vexy_lines_utils.exporters.base import BaseExporter

if TYPE_CHECKING:
    from vexy_lines_utils.core.config import AutomationConfig


class VexyLinesExporter(BaseExporter):
    """Batch exports .lines documents to PDF using the Vexy Lines UI."""

    def __init__(self, *, config: AutomationConfig | None = None, bridge: ApplicationBridge | None = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self._bridge = bridge

    @property
    def bridge(self) -> ApplicationBridge:
        if self._bridge is None:
            if self.dry_run:
                msg = "Dry-run mode requires a test bridge"
                raise AutomationError(msg)
            self._bridge = PyXABridge(self.config)
        return self._bridge

    def _process_file(self, file_path: Path) -> None:
        """Process a single file."""
        pdf_path = file_path.with_suffix(".pdf")
        self.bridge.activate()
        self._open_document(file_path)
        self._trigger_export()
        self._handle_save_dialog(file_path)
        self._verify_export(pdf_path)
        self._close_document()

    def _trigger_export(self) -> None:
        """Trigger the export dialog."""
        # Try keyboard shortcut first (Cmd+E) - most reliable
        logger.debug("Attempting to trigger Export dialog with Cmd+E")
        self._ui.hotkey("command", "e")
        time.sleep(0.5)  # Give dialog time to appear

        # Check if dialog appeared
        try:
            self.watcher.wait_for_contains(
                needle=self.config.export_window_title,
                present=True,
                timeout=2.0,  # Short timeout for keyboard shortcut
            )
            logger.debug("Export dialog opened via keyboard shortcut")
        except AutomationError:
            # Fallback to menu click if keyboard shortcut failed
            logger.debug("Keyboard shortcut failed, trying menu click")
            menu_name, item_name = self.config.export_menu
            if not self.bridge.click_menu_item(menu_name, item_name):
                logger.error(f"Menu click failed for {menu_name} > {item_name}")
                msg = "Failed to open Export dialog via menu or keyboard"
                raise AutomationError(msg, "MENU_CLICK_FAILED")

            # Wait for dialog after menu click
            self.watcher.wait_for_contains(
                needle=self.config.export_window_title,
                present=True,
                timeout=self.config.scale_timeout(self.config.wait_for_dialog),
            )
            logger.debug("Export dialog opened via menu click")

        time.sleep(self.config.post_action_delay)
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)

    def _handle_save_dialog(self, file_path: Path, *, retry_count: int = 0) -> None:
        """Handle save dialog with smart retry on navigation failures.

        Args:
            file_path: Path to the file being exported
            retry_count: Current retry attempt (for recursive calls)
        """
        max_navigation_retries = 2  # Try up to 3 strategies (0, 1, 2)

        self.watcher.wait_for_contains(
            needle=self.config.save_window_title,
            present=True,
            timeout=self.config.wait_for_dialog,
        )
        folder_path = str(file_path.parent)
        pdf_name = file_path.with_suffix(".pdf").name

        # Try navigation strategy based on retry count
        try:
            if retry_count == 0:
                # Primary strategy: Just set filename (often we're already in the right folder)
                logger.debug(f"Setting filename to {pdf_name}")
                self._set_filename_simple(pdf_name)
            elif retry_count == 1:
                # Secondary strategy: Navigate to folder first with Command-Shift-G
                logger.info("Retry: navigating to folder first")
                self._navigate_to_folder_goto(folder_path)
                self._set_filename_simple(pdf_name)
            else:
                # Tertiary strategy: Type full path directly
                logger.info("Final retry: typing full path")
                self._navigate_to_folder_direct(folder_path, pdf_name)

            # Save - try multiple methods
            logger.debug("Attempting to save file")

            # Method 1: Press Enter (should work when filename field is focused)
            self._ui.press("enter")
            time.sleep(0.5)

            # Check if dialog closed
            try:
                self.watcher.wait_for_contains(
                    needle=self.config.save_window_title,
                    present=False,
                    timeout=1.0,  # Quick check
                )
                logger.debug("Save completed via Enter key")
                return  # Success!
            except AutomationError:
                # Dialog still open, try alternative methods
                logger.debug("Enter key didn't work, trying tab to Save button")

                # Method 2: Tab to Save button and press Return
                for _ in range(3):
                    self._ui.press("tab")
                    time.sleep(0.1)
                self._ui.press("return")
                time.sleep(0.5)

            # Handle potential overwrite dialog
            self._ui.press("enter")
            time.sleep(0.2)

            # Final wait for save to complete
            self.watcher.wait_for_contains(
                needle=self.config.save_window_title,
                present=False,
                timeout=self.config.wait_for_dialog,
            )
        except AutomationError:
            if retry_count < max_navigation_retries:
                logger.warning(f"Navigation strategy {retry_count + 1} failed, trying alternative")
                time.sleep(1)  # Brief pause before retry
                self._handle_save_dialog(file_path, retry_count=retry_count + 1)
            else:
                raise

    def _navigate_to_folder_goto(self, folder_path: str) -> None:
        """Navigate using Command-Shift-G (Go to Folder)."""
        self._ui.hotkey("command", "shift", "g")
        time.sleep(self.config.post_action_delay)
        self._ui.copy_text(folder_path)
        self._ui.hotkey("command", "v")
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)

    def _navigate_to_folder_direct(self, folder_path: str, filename: str) -> None:
        """Navigate by typing full path directly."""
        full_path = str(Path(folder_path) / filename)
        self._ui.copy_text(full_path)
        self._ui.hotkey("command", "v")
        time.sleep(self.config.post_action_delay)

    def _set_filename_simple(self, pdf_name: str) -> None:
        """Set just the filename in the save dialog."""
        self._ui.hotkey("command", "a")
        time.sleep(self.config.post_action_delay / 2)
        self._ui.copy_text(pdf_name)
        self._ui.hotkey("command", "v")
        time.sleep(self.config.post_action_delay / 2)
