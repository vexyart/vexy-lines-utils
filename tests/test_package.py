# this_file: tests/test_package.py
"""Unit tests for vexy_lines_utils."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from vexy_lines_utils import AutomationConfig, ExportStats, VexyLinesExporter, find_lines_files
from vexy_lines_utils.vexy_lines_utils import (
    AutomationError,
    FileValidationError,
    UIActions,
    WindowWatcher,
    validate_lines_file,
)

if TYPE_CHECKING:
    from pathlib import Path


def provider_from_sequences(sequences: list[list[str]]):
    """Utility to feed deterministic window titles into WindowWatcher."""

    remaining = list(sequences)

    def _provider() -> list[str]:
        if remaining:
            return remaining.pop(0)
        return []

    return _provider


def test_find_lines_files_when_file_then_direct_hit(tmp_path: Path) -> None:
    doc = tmp_path / "demo.lines"
    doc.write_text("data")
    assert find_lines_files(doc) == [doc]


def test_find_lines_files_when_directory_then_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.lines").write_text("x")
    (tmp_path / "a.lines").write_text("x")
    files = find_lines_files(tmp_path)
    assert [path.name for path in files] == ["a.lines", "b.lines"]


def test_export_stats_records_success_and_failure(tmp_path: Path) -> None:
    stats = ExportStats()
    first = tmp_path / "ok.lines"
    second = tmp_path / "broken.lines"
    stats.record_success(first)
    stats.record_failure(second, "boom")
    assert stats.processed == 2
    assert stats.success == 1
    assert stats.failures == [(str(second), "boom")]


def test_window_watcher_waits_for_presence() -> None:
    watcher = WindowWatcher(provider_from_sequences([[], ["Export"]]), poll_interval=0.01)
    watcher.wait_for_contains("Export", present=True, timeout=0.2)


def test_window_watcher_waits_for_disappearance() -> None:
    watcher = WindowWatcher(provider_from_sequences([["Save"], []]), poll_interval=0.01)
    watcher.wait_for_contains("Save", present=False, timeout=0.2)


def test_exporter_dry_run_counts_files(tmp_path: Path) -> None:
    (tmp_path / "demo.lines").write_text("")
    exporter = VexyLinesExporter(dry_run=True, ui_actions=UIActions(dry_run=True))
    stats = exporter.export(tmp_path)
    assert stats.success == 1
    assert stats.dry_run is True


def test_window_watcher_timeout() -> None:
    watcher = WindowWatcher(lambda: [], poll_interval=0.01)
    with pytest.raises(AutomationError) as exc_info:
        watcher.wait_for_contains("Never", present=True, timeout=0.05)
    assert exc_info.value.error_code == "TIMEOUT"


def test_validate_lines_file_valid(tmp_path: Path) -> None:
    """Test validation passes for valid .lines file."""
    doc = tmp_path / "valid.lines"
    doc.write_text("content")
    validate_lines_file(doc)  # Should not raise


def test_validate_lines_file_missing(tmp_path: Path) -> None:
    """Test validation fails for missing file."""
    doc = tmp_path / "missing.lines"
    with pytest.raises(FileValidationError) as exc_info:
        validate_lines_file(doc)
    assert "does not exist" in str(exc_info.value)


def test_validate_lines_file_empty(tmp_path: Path) -> None:
    """Test validation fails for empty file."""
    doc = tmp_path / "empty.lines"
    doc.write_text("")
    with pytest.raises(FileValidationError) as exc_info:
        validate_lines_file(doc)
    assert "empty" in str(exc_info.value)


def test_validate_lines_file_wrong_extension(tmp_path: Path) -> None:
    """Test validation fails for wrong file extension."""
    doc = tmp_path / "wrong.txt"
    doc.write_text("content")
    with pytest.raises(FileValidationError) as exc_info:
        validate_lines_file(doc)
    assert "Not a .lines file" in str(exc_info.value)


def test_automation_config_timeout_scaling() -> None:
    """Test timeout multiplier scaling."""
    config = AutomationConfig(timeout_multiplier=2.5)
    assert config.scale_timeout(10.0) == 25.0
    assert config.scale_timeout(5.0) == 12.5


def test_automation_error_codes() -> None:
    """Test AutomationError includes error codes."""
    error = AutomationError("Test message", "TEST_CODE")
    assert str(error) == "Test message"
    assert error.error_code == "TEST_CODE"


def test_file_validation_error_code() -> None:
    """Test FileValidationError has correct error code."""
    error = FileValidationError("File broken")
    assert error.error_code == "FILE_INVALID"
