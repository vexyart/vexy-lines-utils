#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/exporter.py
"""Single concrete exporter for Vexy Lines dialog-less export."""

from __future__ import annotations

import shutil
import time
from pathlib import Path  # noqa: TC003

from loguru import logger

from vexy_lines_utils.automation.bridges import AppleScriptBridge
from vexy_lines_utils.automation.window_watcher import WindowWatcher
from vexy_lines_utils.core.config import ExportConfig  # noqa: TC001
from vexy_lines_utils.core.errors import AutomationError
from vexy_lines_utils.core.plist import PlistManager
from vexy_lines_utils.core.stats import ExportStats
from vexy_lines_utils.utils.file_utils import (
    expected_export_path,
    find_lines_files,
    resolve_output_path,
    validate_export,
    validate_lines_file,
)
from vexy_lines_utils.utils.interrupt import InterruptHandler

STABLE_SIZE_POLLS = 2
MIN_STABLE_INTERVAL = 0.3


class VexyLinesExporter:
    def __init__(self, config: ExportConfig, *, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run

    def export(self, input_path: Path, output_path: Path | None = None) -> ExportStats:
        input_path = input_path.expanduser().resolve()
        files = find_lines_files(input_path)
        if not files:
            msg = f"No .lines files found at {input_path}"
            raise AutomationError(msg, "NO_FILES")

        if output_path is not None:
            output_path = output_path.expanduser().resolve()
            if len(files) > 1 and output_path.suffix:
                msg = "Cannot export multiple files to a single output file"
                raise AutomationError(msg, "INVALID_OUTPUT")

        stats = ExportStats(dry_run=self.dry_run)

        if self.dry_run:
            for f in files:
                stats.record_success(f, elapsed=0.0)
            return stats

        interrupt = InterruptHandler()

        try:
            with PlistManager(self.config.format, self.config.app_name):
                bridge = AppleScriptBridge(self.config)
                bridge.activate()

                watcher = WindowWatcher(bridge.window_titles, self.config.poll_interval)
                watcher.wait_for_any(self.config.scale_timeout(self.config.wait_for_app))

                for file in files:
                    if interrupt.check():
                        logger.warning("Interrupted — stopping after current file")
                        break
                    self._process_file(file, bridge, watcher, output_path, stats)

                bridge.quit_app()
        finally:
            interrupt.restore()

        return stats

    def _process_file(
        self,
        file_path: Path,
        bridge: AppleScriptBridge,
        watcher: WindowWatcher,
        output_path: Path | None,
        stats: ExportStats,
    ) -> None:
        try:
            validate_lines_file(file_path)
        except Exception as e:
            stats.record_failure(file_path, str(e))
            return

        expected = expected_export_path(file_path, self.config.format)
        resolved = resolve_output_path(file_path, output_path, self.config.format)

        for attempt in range(1, self.config.max_retries + 1):
            start = time.monotonic()
            try:
                bridge.open_file(file_path)
                watcher.wait_for_contains(
                    file_path.stem,
                    present=True,
                    timeout=self.config.scale_timeout(self.config.wait_for_file),
                )
                time.sleep(self.config.post_action_delay)

                if not bridge.click_menu_item("File", self.config.export_menu_item):
                    msg = f"Failed to click menu item: {self.config.export_menu_item}"
                    raise AutomationError(msg, "EXPORT_MENU_TIMEOUT")

                self._wait_for_export(expected)

                if not validate_export(expected, self.config.format):
                    error_code = f"INVALID_{self.config.format.upper()}"
                    msg = f"Exported file failed validation: {expected}"
                    raise AutomationError(msg, error_code)

                if resolved is not None:
                    resolved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(expected), str(resolved))
                    logger.debug(f"Moved export to {resolved}")

                bridge.close_front_window()
                time.sleep(self.config.post_action_delay)

                elapsed = time.monotonic() - start
                stats.record_success(file_path, elapsed=elapsed)
                return

            except AutomationError as e:
                if attempt < self.config.max_retries:
                    logger.warning(f"Attempt {attempt} failed for {file_path.name}: {e} — retrying")
                    bridge.close_front_window()
                    time.sleep(self.config.post_action_delay)
                else:
                    stats.record_failure(file_path, str(e))
                    bridge.close_front_window()
                    return

    def _wait_for_export(self, path: Path) -> None:
        timeout = self.config.scale_timeout(self.config.wait_for_file)
        deadline = time.monotonic() + timeout
        last_size = -1
        stable_count = 0

        while time.monotonic() < deadline:
            if path.exists():
                try:
                    size = path.stat().st_size
                except OSError:
                    time.sleep(MIN_STABLE_INTERVAL)
                    continue
                if size > 0:
                    if size == last_size:
                        stable_count += 1
                        if stable_count >= STABLE_SIZE_POLLS:
                            return
                    else:
                        stable_count = 0
                    last_size = size
            time.sleep(MIN_STABLE_INTERVAL)

        msg = f"Timed out waiting for export file: {path}"
        raise AutomationError(msg, "EXPORT_TIMEOUT")
