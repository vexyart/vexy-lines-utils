#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/exporters/enhanced.py
"""Enhanced Vexy Lines exporter with multiple fallback strategies."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.automation.bridges import AppleScriptBridge, ApplicationBridge, PyXABridge
from vexy_lines_utils.core.config import EnhancedAutomationConfig, MenuStrategy
from vexy_lines_utils.core.errors import AutomationError
from vexy_lines_utils.exporters.base import BaseExporter
from vexy_lines_utils.strategies.dialog_handler import SmartDialogHandler
from vexy_lines_utils.strategies.menu_trigger import SmartMenuTrigger
from vexy_lines_utils.utils.interrupt import InterruptHandler

if TYPE_CHECKING:
    from pathlib import Path


class EnhancedVexyLinesExporter(BaseExporter):
    """Enhanced exporter with multiple fallback strategies and better error handling."""

    def __init__(
        self, *, config: EnhancedAutomationConfig | None = None, bridge: ApplicationBridge | None = None, **kwargs
    ):
        # Use EnhancedAutomationConfig if no config provided
        config = config or EnhancedAutomationConfig()
        super().__init__(config=config, **kwargs)
        self._bridge = bridge
        self.interrupt_handler = InterruptHandler()
        self.menu_trigger = SmartMenuTrigger(config)
        self.dialog_handler = SmartDialogHandler(config)

    @property
    def bridge(self) -> ApplicationBridge:
        if self._bridge is None:
            if self.dry_run:
                msg = "Dry-run mode requires a test bridge"
                raise AutomationError(msg)
            # Try to select the best bridge based on available strategies
            self._bridge = self._select_best_bridge()
        return self._bridge

    def _select_best_bridge(self) -> ApplicationBridge:
        """Select the best available bridge based on configuration."""
        # Check which bridge to use based on primary menu strategy
        if self.config.menu_strategies:
            primary_strategy = self.config.menu_strategies[0]
            if primary_strategy == MenuStrategy.APPLESCRIPT:
                try:
                    return AppleScriptBridge(self.config)
                except Exception as e:
                    logger.warning(f"AppleScript bridge failed: {e}")

        # Fallback to PyXA if available
        try:
            return PyXABridge(self.config)
        except Exception as e:
            logger.warning(f"PyXA bridge failed: {e}")

        # Last resort: try AppleScript again
        try:
            return AppleScriptBridge(self.config)
        except Exception as e:
            msg = "No automation bridge available"
            raise AutomationError(msg) from e

    def _process_file(self, file_path: Path) -> None:
        """Process a single file with interrupt handling."""
        # Check for interruption
        if self.interrupt_handler.check():
            msg = "Processing interrupted by user"
            raise AutomationError(msg, "USER_INTERRUPT")

        pdf_path = file_path.with_suffix(".pdf")
        self.bridge.activate()
        self._open_document(file_path)
        self._trigger_export_with_strategies()
        self._handle_save_with_strategies(file_path)
        self._verify_export(pdf_path)
        self._close_document()

    def _trigger_export_with_strategies(self) -> None:
        """Trigger export using smart menu strategies."""
        if not self.menu_trigger.trigger_export(self.watcher):
            # Fallback to standard method
            logger.warning("Smart menu strategies failed, trying standard method")
            menu_name, item_name = self.config.export_menu
            if not self.bridge.click_menu_item(menu_name, item_name):
                msg = "Failed to open Export dialog"
                raise AutomationError(msg, "MENU_CLICK_FAILED")
            self.watcher.wait_for_patterns(
                self.config.export_window_patterns,
                present=True,
                timeout=self.config.scale_timeout(self.config.wait_for_dialog),
            )

        time.sleep(self.config.post_action_delay)
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)

    def _handle_save_with_strategies(self, file_path: Path) -> None:
        """Handle save dialog using smart strategies."""
        # Wait for save dialog
        self.watcher.wait_for_patterns(
            self.config.save_window_patterns,
            present=True,
            timeout=self.config.wait_for_dialog,
        )

        # Try smart dialog handler first
        if not self.dialog_handler.handle_save_dialog(file_path, self.watcher):
            # Fallback to standard navigation
            logger.warning("Smart dialog strategies failed, using standard navigation")
            self._handle_save_standard(file_path)

    def _handle_save_standard(self, file_path: Path) -> None:
        """Standard save dialog handling (fallback)."""
        folder_path = str(file_path.parent)
        pdf_name = file_path.with_suffix(".pdf").name

        # Navigate to folder
        self._ui.hotkey("command", "shift", "g")
        time.sleep(self.config.post_action_delay)
        self._ui.copy_text(folder_path)
        self._ui.hotkey("command", "v")
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)

        # Set filename
        self._ui.hotkey("command", "a")
        time.sleep(self.config.post_action_delay / 2)
        self._ui.copy_text(pdf_name)
        self._ui.hotkey("command", "v")
        time.sleep(self.config.post_action_delay / 2)

        # Save
        self._ui.press("enter")
        time.sleep(self.config.post_action_delay)
        # Confirm overwrite
        self._ui.press("enter")

        # Wait for save to complete
        self.watcher.wait_for_patterns(
            self.config.save_window_patterns,
            present=False,
            timeout=self.config.wait_for_dialog,
        )

    def __del__(self):
        """Cleanup: restore interrupt handler."""
        if hasattr(self, "interrupt_handler"):
            self.interrupt_handler.restore()
