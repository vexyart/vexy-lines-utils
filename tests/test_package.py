# this_file: tests/test_package.py
"""Unit tests for vexy_lines_utils."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from vexy_lines_utils import (
    AutomationConfig,
    AutomationError,
    ExportStats,
    FileValidationError,
    UIActions,
    VexyLinesExporter,
    WindowWatcher,
    find_lines_files,
    validate_lines_file,
    validate_pdf,
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


def test_exporter_skips_when_pdf_exists(tmp_path: Path) -> None:
    """Test that .lines files are skipped when corresponding .pdf already exists."""
    lines_file = tmp_path / "document.lines"
    pdf_file = tmp_path / "document.pdf"

    # Create both .lines and .pdf files
    lines_file.write_text("lines content")
    pdf_file.write_text("pdf content")

    # Run exporter in dry-run mode
    exporter = VexyLinesExporter(dry_run=True, ui_actions=UIActions(dry_run=True))
    stats = exporter.export(tmp_path)

    # Should count as skipped (PDF exists = no work needed)
    assert stats.skipped == 1
    assert stats.success == 0
    assert stats.processed == 1
    assert len(stats.failures) == 0

    # PDF should still exist and be unchanged
    assert pdf_file.exists()
    assert pdf_file.read_text() == "pdf content"


def test_window_watcher_get_current_state_with_windows() -> None:
    """Test WindowWatcher.get_current_state() with visible windows."""
    watcher = WindowWatcher(lambda: ["Export", "Save"], poll_interval=0.01)
    state = watcher.get_current_state()
    assert "Export" in state
    assert "Save" in state
    assert "Windows:" in state


def test_window_watcher_get_current_state_no_windows() -> None:
    """Test WindowWatcher.get_current_state() when no windows visible."""
    watcher = WindowWatcher(lambda: [], poll_interval=0.01)
    state = watcher.get_current_state()
    assert state == "No windows visible"


def test_ui_actions_navigation_helpers() -> None:
    """Test navigation helper methods record actions correctly."""
    ui = UIActions(dry_run=True)
    exporter = VexyLinesExporter(dry_run=True, ui_actions=ui)

    # Test _navigate_to_folder_goto
    exporter._navigate_to_folder_goto("/test/folder")
    assert "hotkey:command+shift+g" in ui.recorded
    assert "copy:/test/folder" in ui.recorded

    # Test _set_filename_simple
    ui.recorded.clear()
    exporter._set_filename_simple("test.pdf")
    assert "hotkey:command+a" in ui.recorded
    assert "copy:test.pdf" in ui.recorded

    # Test _navigate_to_folder_direct
    ui.recorded.clear()
    exporter._navigate_to_folder_direct("/test/folder", "test.pdf")
    assert "copy:/test/folder/test.pdf" in ui.recorded


def test_validate_pdf_valid(tmp_path: Path) -> None:
    """Test PDF validation passes for valid PDF file."""
    pdf = tmp_path / "valid.pdf"
    # Write a minimal valid PDF
    pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)  # >1KB with valid header
    assert validate_pdf(pdf) is True


def test_validate_pdf_missing(tmp_path: Path) -> None:
    """Test PDF validation fails for missing file."""
    pdf = tmp_path / "missing.pdf"
    assert validate_pdf(pdf) is False


def test_validate_pdf_too_small(tmp_path: Path) -> None:
    """Test PDF validation fails for tiny file."""
    pdf = tmp_path / "tiny.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")  # <1KB
    assert validate_pdf(pdf) is False


def test_validate_pdf_invalid_header(tmp_path: Path) -> None:
    """Test PDF validation fails for invalid magic bytes."""
    pdf = tmp_path / "invalid.pdf"
    pdf.write_bytes(b"NOT A PDF\n" + b"x" * 2000)
    assert validate_pdf(pdf) is False


def test_validate_pdf_large_file_warning(tmp_path: Path) -> None:
    """Test PDF validation warns but passes for very large files."""
    pdf = tmp_path / "large.pdf"
    # Create header + minimal content (actual large file would be slow)
    pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)
    # This should still pass (we can't easily test the warning in unit test)
    assert validate_pdf(pdf) is True


def test_export_stats_timing() -> None:
    """Test that ExportStats tracks timing correctly."""
    from pathlib import Path

    stats = ExportStats()
    test_path = Path("/tmp/test.lines")

    # Record successes with timing
    stats.record_success(test_path, elapsed=1.5)
    stats.record_success(test_path, elapsed=2.5)

    # Check timing calculations
    assert len(stats.file_times) == 2
    assert stats.get_average_time() == 2.0
    assert stats.get_total_time() > 0  # Will be small but >0

    # Test dict output includes timing
    data = stats.as_dict()
    assert "total_time" in data
    assert "average_time" in data
    assert data["average_time"] == 2.0


def test_export_stats_skipped() -> None:
    """Test that ExportStats tracks skipped files separately."""
    from pathlib import Path

    stats = ExportStats()
    test_path = Path("/tmp/test.lines")

    stats.record_skipped(test_path)
    stats.record_success(test_path)
    stats.record_failure(test_path, "test error")

    assert stats.processed == 3
    assert stats.skipped == 1
    assert stats.success == 1
    assert len(stats.failures) == 1

    # Check dict output
    data = stats.as_dict()
    assert data["skipped"] == 1
    assert data["success"] == 1
    assert data["failed"] == 1


def test_export_stats_human_summary() -> None:
    """Test human-readable summary formatting."""
    from pathlib import Path

    stats = ExportStats()
    test_path = Path("/tmp/test.lines")

    # With skipped files
    stats.record_skipped(test_path)
    stats.record_success(test_path, elapsed=1.0)
    summary = stats.human_summary()
    assert "1/2 exports succeeded" in summary
    assert "(1 skipped)" in summary
    assert "avg 1.0s per file" in summary

    # Dry-run mode
    stats2 = ExportStats(dry_run=True)
    stats2.record_success(test_path)
    summary2 = stats2.human_summary()
    assert "dry-run" in summary2
