#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/exporters/base.py
"""Base exporter class with common functionality."""

from __future__ import annotations

import subprocess
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.automation.ui_actions import UIActions
from vexy_lines_utils.automation.window_watcher import WindowWatcher
from vexy_lines_utils.core.config import AutomationConfig
from vexy_lines_utils.core.errors import AutomationError, FileValidationError
from vexy_lines_utils.core.stats import ExportStats
from vexy_lines_utils.utils.file_utils import find_lines_files, validate_lines_file, validate_pdf

if TYPE_CHECKING:
    from pathlib import Path


class BaseExporter(ABC):
    """Base class for Vexy Lines exporters."""

    def __init__(
        self,
        *,
        config: AutomationConfig | None = None,
        ui_actions: UIActions | None = None,
        dry_run: bool = False,
    ):
        self.config = config or AutomationConfig()
        self.dry_run = dry_run
        self._ui = ui_actions or UIActions(dry_run=dry_run)
        self._watcher: WindowWatcher | None = None

    @property
    @abstractmethod
    def bridge(self):
        """Get the application bridge."""
        ...

    @property
    def watcher(self) -> WindowWatcher:
        """Get the window watcher."""
        if self._watcher is None:
            self._watcher = WindowWatcher(
                title_provider=self.bridge.window_titles,
                poll_interval=self.config.poll_interval,
            )
        return self._watcher

    def export(self, target: Path, *, verbose: bool = False) -> ExportStats:
        """Export .lines documents found under target to PDF.

        Args:
            target: Path to .lines file or directory to search
            verbose: Show detailed progress messages

        Returns:
            Export statistics
        """
        path = target.expanduser().resolve()
        logger.info(f"Scanning {path}")
        files = find_lines_files(path)
        if not files:
            msg = f"No .lines files found at {path}"
            raise AutomationError(msg, "NO_FILES")

        total_files = len(files)
        logger.info(f"Found {total_files} .lines file{'s' if total_files != 1 else ''} to process")

        stats = ExportStats(dry_run=self.dry_run)
        for idx, file_path in enumerate(files, start=1):
            file_start = time.monotonic()

            # Log progress with ETA
            progress_msg = f"[{idx}/{total_files}] Processing {file_path.name}"
            if stats.file_times and idx > 1:
                avg_time = stats.get_average_time()
                remaining = total_files - idx + 1
                eta_seconds = avg_time * remaining
                eta_min, eta_sec = divmod(int(eta_seconds), 60)
                if eta_min > 0:
                    progress_msg += f" (ETA: {eta_min}m {eta_sec}s)"
                else:
                    progress_msg += f" (ETA: {eta_sec}s)"
            logger.info(progress_msg)

            try:
                # Check if PDF already exists
                pdf_path = file_path.with_suffix(".pdf")
                if pdf_path.exists():
                    stats.record_skipped(file_path)
                    continue

                # Validate file before processing
                if not self.dry_run:
                    validate_lines_file(file_path)

                if self.dry_run:
                    stats.record_success(file_path)
                    continue

                # Try with retries for transient failures
                self._process_file_with_retry(file_path)
                elapsed = time.monotonic() - file_start
                stats.record_success(file_path, elapsed=elapsed)
            except FileValidationError as exc:
                stats.record_failure(file_path, f"Validation failed: {exc}")
            except AutomationError as exc:
                # Separate PDF validation failures from other automation errors
                if exc.error_code == "INVALID_PDF":
                    stats.record_validation_failure(file_path, str(exc))
                else:
                    stats.record_failure(file_path, str(exc))
            except Exception as exc:
                stats.record_failure(file_path, str(exc))

        # Log final summary
        total_time = stats.get_total_time()
        summary = stats.human_summary()
        logger.info(f"Batch complete: {summary}, total time {total_time:.1f}s")

        return stats

    def _process_file_with_retry(self, file_path: Path) -> None:
        """Process file with retry logic for transient failures."""
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{self.config.max_retries} for {file_path.name}")
                    # Log current UI state for diagnostics
                    if self._watcher:
                        ui_state = self._watcher.get_current_state()
                        logger.debug(f"Current UI state before retry: {ui_state}")
                    # Exponential backoff: 2, 4, 8 seconds...
                    time.sleep(2**attempt)

                self._process_file(file_path)
                return  # Success!

            except AutomationError as e:
                last_error = e
                # Don't retry certain errors
                if e.error_code in ["FILE_INVALID", "NO_FILES"]:
                    raise
                # Log detailed error information
                logger.warning(f"Attempt {attempt + 1} failed with error code {e.error_code}: {e}")
                if self._watcher and attempt < self.config.max_retries - 1:
                    ui_state = self._watcher.get_current_state()
                    logger.debug(f"UI state after failure: {ui_state}")

        # All retries exhausted
        if last_error:
            raise last_error
        msg = f"Failed after {self.config.max_retries} attempts"
        raise AutomationError(msg, "MAX_RETRIES")

    @abstractmethod
    def _process_file(self, file_path: Path) -> None:
        """Process a single file (implementation-specific)."""
        ...

    def _open_document(self, file_path: Path) -> None:
        """Open a document in Vexy Lines."""
        result = subprocess.run(
            ["open", "-a", self.config.app_name, str(file_path)],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            msg = f"Failed to open {file_path}: {result.stderr.strip()}"
            raise AutomationError(msg, "OPEN_FAILED")

        self.watcher.wait_for_contains(
            needle=file_path.stem,
            present=True,
            timeout=self.config.scale_timeout(self.config.wait_for_file),
        )
        time.sleep(self.config.post_action_delay)

    def _close_document(self, *, force: bool = False) -> None:
        """Close the current document if it has unsaved changes.

        After successful export, check if window title has '*' (unsaved changes).
        If yes, close with Cmd+W and handle the unsaved changes dialog.
        If no, skip closing to avoid unnecessary operations (unless force=True).

        Args:
            force: If True, close document even without unsaved changes marker
        """
        # Get current window titles
        titles = self.watcher.get_current_state()

        # Check if there's an asterisk indicating unsaved changes
        should_close = "*" in titles or force

        if should_close:
            if force and "*" not in titles:
                logger.debug("Force closing document (no unsaved changes marker)...")
            else:
                logger.debug("Detected unsaved changes marker (*) in window title, closing document...")

            # Close with Cmd+W
            self._ui.hotkey("command", "w")
            time.sleep(0.5)  # Give time for dialog to appear

            # Check if unsaved changes dialog appeared
            titles_after_close = self.watcher.get_current_state()
            unsaved_patterns = ["Unsaved Changes", "Warning", "Save"]

            if any(pattern.lower() in titles_after_close.lower() for pattern in unsaved_patterns):
                logger.debug("Unsaved changes dialog appeared, clicking Discard with Tab Tab Enter...")
                # Navigate to Discard button: Tab Tab Enter
                self._ui.press("tab")  # Save (default) -> Cancel
                time.sleep(0.2)
                self._ui.press("tab")  # Cancel -> Discard
                time.sleep(0.2)
                self._ui.press("enter")  # Click Discard
                time.sleep(self.config.post_action_delay)
        else:
            logger.debug("No unsaved changes marker in window title, skipping close...")

    def _verify_export(self, pdf_path: Path) -> None:
        """Verify that PDF export completed successfully and is valid."""
        deadline = time.monotonic() + self.config.wait_for_dialog
        while time.monotonic() < deadline:
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                # File exists and has content, now validate it
                if validate_pdf(pdf_path):
                    return  # Export successful and valid
                # If validation fails, treat as export failure
                msg = f"Export completed but PDF validation failed for {pdf_path.name}"
                raise AutomationError(msg, "INVALID_PDF")
            time.sleep(self.config.poll_interval)
        msg = f"Export did not finish for {pdf_path.name}"
        raise AutomationError(msg, "EXPORT_TIMEOUT")

    def close_final_document(self) -> None:
        """Close any remaining open document after batch export completes.

        This is called after the batch export summary is printed to close
        the last processed .lines file that may still be open.

        Unlike _close_document(), this forces close even without unsaved changes,
        since this is the final cleanup step after batch processing.
        """
        if self.dry_run:
            logger.debug("Dry-run mode: skipping final document close")
            return

        try:
            # Get current window titles to check if any document is open
            titles = self.watcher.get_current_state()

            if not titles or "No windows visible" in titles:
                logger.debug("No windows open, skipping final close")
                return

            # Activate Vexy Lines before sending close command
            logger.debug(f"Activating {self.config.app_name}...")
            self.bridge.activate()
            time.sleep(0.3)  # Brief pause to ensure app is frontmost

            # Force close the document (even without unsaved changes marker)
            self._close_document(force=True)
            logger.info("Final document closed")

        except Exception as e:
            # Don't fail the entire batch if final close fails
            logger.warning(f"Failed to close final document: {e}")
