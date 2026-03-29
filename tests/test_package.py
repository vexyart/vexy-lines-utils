# this_file: tests/test_package.py
"""Unit tests for vexy_lines_utils — dialog-less export architecture."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vexy_lines_utils import (
    AppleScriptBridge,
    AutomationError,
    ExportConfig,
    ExportStats,
    FileValidationError,
    PlistManager,
    VexyLinesCLI,
    VexyLinesExporter,
    WindowWatcher,
    __version__,
    find_lines_files,
    validate_lines_file,
    validate_pdf,
    validate_svg,
)
from vexy_lines_utils.core.errors import format_error_with_context, get_error_suggestion
from vexy_lines_utils.core.plist import FORMAT_CODES
from vexy_lines_utils.utils.file_utils import (
    expected_export_path,
    resolve_output_path,
    validate_export,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def provider_from_sequences(sequences: list[list[str]]):
    remaining = list(sequences)

    def _provider() -> list[str]:
        if remaining:
            return remaining.pop(0)
        return []

    return _provider


# ---------------------------------------------------------------------------
# 1. Package imports
# ---------------------------------------------------------------------------


class TestPackageImports:
    def test_all_public_symbols_importable(self) -> None:
        from vexy_lines_utils import __all__  # noqa: PLC0415

        assert "ExportConfig" in __all__
        assert "PlistManager" in __all__
        assert "AppleScriptBridge" in __all__
        assert "VexyLinesExporter" in __all__
        assert "WindowWatcher" in __all__
        assert "ExportStats" in __all__
        assert "find_lines_files" in __all__
        assert "validate_pdf" in __all__
        assert "validate_svg" in __all__
        assert "validate_lines_file" in __all__
        assert "AutomationError" in __all__
        assert "FileValidationError" in __all__

    def test_old_symbols_removed(self) -> None:
        import vexy_lines_utils  # noqa: PLC0415

        assert not hasattr(vexy_lines_utils, "AutomationConfig")
        assert not hasattr(vexy_lines_utils, "UIActions")
        assert not hasattr(vexy_lines_utils, "PyXABridge")
        assert not hasattr(vexy_lines_utils, "MenuStrategy")
        assert not hasattr(vexy_lines_utils, "DialogStrategy")

    def test_version_available(self) -> None:
        assert isinstance(__version__, str)


# ---------------------------------------------------------------------------
# 2. ExportConfig
# ---------------------------------------------------------------------------


class TestExportConfig:
    def test_defaults(self) -> None:
        cfg = ExportConfig()
        assert cfg.format == "pdf"
        assert cfg.app_name == "Vexy Lines"
        assert cfg.timeout_multiplier == 1.0
        assert cfg.max_retries == 3
        assert cfg.poll_interval == 0.2

    def test_format_case_insensitive(self) -> None:
        cfg = ExportConfig(format="PDF")
        assert cfg.format == "pdf"

    def test_format_svg(self) -> None:
        cfg = ExportConfig(format="svg")
        assert cfg.format == "svg"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="format must be one of"):
            ExportConfig(format="png")

    def test_timeout_multiplier_bounds(self) -> None:
        ExportConfig(timeout_multiplier=0.1)
        ExportConfig(timeout_multiplier=10.0)
        with pytest.raises(ValueError, match="timeout_multiplier"):
            ExportConfig(timeout_multiplier=0.05)
        with pytest.raises(ValueError, match="timeout_multiplier"):
            ExportConfig(timeout_multiplier=11.0)

    def test_max_retries_bounds(self) -> None:
        ExportConfig(max_retries=0)
        ExportConfig(max_retries=1)
        ExportConfig(max_retries=10)
        with pytest.raises(ValueError, match="max_retries"):
            ExportConfig(max_retries=-1)
        with pytest.raises(ValueError, match="max_retries"):
            ExportConfig(max_retries=11)

    def test_empty_app_name_raises(self) -> None:
        with pytest.raises(ValueError, match="app_name"):
            ExportConfig(app_name="  ")

    def test_scale_timeout(self) -> None:
        cfg = ExportConfig(timeout_multiplier=2.5)
        assert cfg.scale_timeout(10.0) == 25.0
        assert cfg.scale_timeout(5.0) == 12.5

    def test_export_menu_item_pdf(self) -> None:
        cfg = ExportConfig(format="pdf")
        assert cfg.export_menu_item == "Export PDF File"

    def test_export_menu_item_svg(self) -> None:
        cfg = ExportConfig(format="svg")
        assert cfg.export_menu_item == "Export SVG File"

    def test_export_extension(self) -> None:
        assert ExportConfig(format="pdf").export_extension == ".pdf"
        assert ExportConfig(format="svg").export_extension == ".svg"


# ---------------------------------------------------------------------------
# 3. PlistManager
# ---------------------------------------------------------------------------


class TestPlistManager:
    _EXISTING_XML = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        b'<plist version="1.0"><dict>'
        b"<key>export\xc2\xb7dlg\xc2\xb7checkLayers</key><false/>"
        b"<key>export\xc2\xb7dlg\xc2\xb7scale</key><real>2</real>"
        b"</dict></plist>\n"
    )

    def _make_defaults_mock(self, *, domain_exists: bool = False) -> MagicMock:
        def _side_effect(*args: str, _input: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
            if args[0] == "export":
                if domain_exists:
                    return subprocess.CompletedProcess(args, returncode=0, stdout=self._EXISTING_XML, stderr=b"")
                return subprocess.CompletedProcess(args, returncode=1, stdout=b"", stderr=b"Domain not found")
            return subprocess.CompletedProcess(args, returncode=0, stdout=b"", stderr=b"")

        return MagicMock(side_effect=_side_effect)

    def _write_calls(self, mock: MagicMock) -> dict[str, str]:
        """Extract {key: value_str} from all _defaults("write", ...) calls."""
        return {call.args[2]: call.args[4] for call in mock.call_args_list if call.args[0] == "write"}

    def test_applies_export_prefs_for_pdf(self) -> None:
        mock_def = self._make_defaults_mock()
        with (
            patch.object(PlistManager, "_quit_app"),
            patch("vexy_lines_utils.core.plist._defaults", mock_def),
            PlistManager("pdf", "Test App"),
        ):
            writes = self._write_calls(mock_def)
            assert writes["export·dlg·format"] == FORMAT_CODES["pdf"]
            assert writes["export·dlg·checkLayers"] == "0"
            assert writes["export·dlg·radioTransparent"] == "1"
            assert writes["export·dlg·exportMode"] == "1"
            assert writes["not_show_intro"] == "1"
            assert writes["not_show_wizard"] == "1"

    def test_applies_export_prefs_for_svg(self) -> None:
        mock_def = self._make_defaults_mock()
        with (
            patch.object(PlistManager, "_quit_app"),
            patch("vexy_lines_utils.core.plist._defaults", mock_def),
            PlistManager("svg", "Test App"),
        ):
            writes = self._write_calls(mock_def)
            assert writes["export·dlg·format"] == FORMAT_CODES["svg"]

    def test_restores_via_import_when_domain_existed(self) -> None:
        mock_def = self._make_defaults_mock(domain_exists=True)
        with (
            patch.object(PlistManager, "_quit_app"),
            patch("vexy_lines_utils.core.plist._defaults", mock_def),
            PlistManager("pdf", "Test App"),
        ):
            mock_def.reset_mock()
        restore_cmds = [call.args[0] for call in mock_def.call_args_list]
        assert "import" in restore_cmds
        assert "delete" not in restore_cmds

    def test_deletes_domain_when_it_did_not_exist(self) -> None:
        mock_def = self._make_defaults_mock(domain_exists=False)
        with (
            patch.object(PlistManager, "_quit_app"),
            patch("vexy_lines_utils.core.plist._defaults", mock_def),
            PlistManager("pdf", "Test App"),
        ):
            mock_def.reset_mock()
        restore_cmds = [call.args[0] for call in mock_def.call_args_list]
        assert "delete" in restore_cmds
        assert "import" not in restore_cmds

    def test_restores_on_exception(self) -> None:
        mock_def = self._make_defaults_mock(domain_exists=True)
        err_msg = "intentional"
        with (  # noqa: PT012
            patch.object(PlistManager, "_quit_app"),
            patch("vexy_lines_utils.core.plist._defaults", mock_def),
            pytest.raises(RuntimeError, match="intentional"),
            PlistManager("pdf", "Test App"),
        ):
            mock_def.reset_mock()
            raise RuntimeError(err_msg)
        restore_cmds = [call.args[0] for call in mock_def.call_args_list]
        assert "import" in restore_cmds

    def test_format_codes(self) -> None:
        assert FORMAT_CODES["pdf"] == "pdf"
        assert FORMAT_CODES["svg"] == "svg"


# ---------------------------------------------------------------------------
# 4. AppleScriptBridge
# ---------------------------------------------------------------------------


class TestAppleScriptBridge:
    def test_activate_builds_correct_command(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch.object(bridge, "_run_osascript", return_value=mock_result) as mock_run:
            bridge.activate()
            script = mock_run.call_args[0][0]
            assert "Vexy Lines" in script
            assert "activate" in script

    def test_activate_raises_on_failure(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "not found"
        with patch.object(bridge, "_run_osascript", return_value=mock_result):
            with pytest.raises(AutomationError) as exc_info:
                bridge.activate()
            assert exc_info.value.error_code == "APP_NOT_FOUND"

    def test_window_titles_parses_output(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Document.lines, Untitled\n"
        with patch.object(bridge, "_run_osascript", return_value=mock_result):
            titles = bridge.window_titles()
            assert titles == ["Document.lines", "Untitled"]

    def test_window_titles_returns_empty_on_error(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch.object(bridge, "_run_osascript", return_value=mock_result):
            assert bridge.window_titles() == []

    def test_click_menu_item_returns_bool(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        mock_ok = MagicMock(returncode=0)
        mock_fail = MagicMock(returncode=1)
        with patch.object(bridge, "_run_osascript", return_value=mock_ok):
            assert bridge.click_menu_item("File", "Export PDF File") is True
        with patch.object(bridge, "_run_osascript", return_value=mock_fail):
            assert bridge.click_menu_item("File", "Export PDF File") is False

    def test_open_file_calls_subprocess(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        with patch("vexy_lines_utils.automation.bridges.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            bridge.open_file(Path("/tmp/test.lines"))  # noqa: S108
            args = mock_run.call_args
            cmd = args[0][0]
            assert "open" in cmd
            assert "-a" in cmd
            assert "Vexy Lines" in cmd

    def test_open_file_raises_on_failure(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        with patch("vexy_lines_utils.automation.bridges.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="open", timeout=10)
            with pytest.raises(AutomationError) as exc_info:
                bridge.open_file(Path("/tmp/test.lines"))  # noqa: S108
            assert exc_info.value.error_code == "OPEN_FAILED"

    def test_is_running_returns_bool(self) -> None:
        cfg = ExportConfig()
        bridge = AppleScriptBridge(cfg)
        mock_true = MagicMock(returncode=0, stdout="true\n")
        mock_false = MagicMock(returncode=0, stdout="false\n")
        with patch.object(bridge, "_run_osascript", return_value=mock_true):
            assert bridge.is_running() is True
        with patch.object(bridge, "_run_osascript", return_value=mock_false):
            assert bridge.is_running() is False


# ---------------------------------------------------------------------------
# 5. WindowWatcher
# ---------------------------------------------------------------------------


class TestWindowWatcher:
    def test_wait_for_contains_present(self) -> None:
        watcher = WindowWatcher(provider_from_sequences([[], ["Export"]]), poll_interval=0.01)
        watcher.wait_for_contains("Export", present=True, timeout=0.2)

    def test_wait_for_contains_disappear(self) -> None:
        watcher = WindowWatcher(provider_from_sequences([["Save"], []]), poll_interval=0.01)
        watcher.wait_for_contains("Save", present=False, timeout=0.2)

    def test_wait_for_contains_timeout(self) -> None:
        watcher = WindowWatcher(lambda: [], poll_interval=0.01)
        with pytest.raises(AutomationError) as exc_info:
            watcher.wait_for_contains("Never", present=True, timeout=0.05)
        assert exc_info.value.error_code == "WINDOW_TIMEOUT"

    def test_wait_for_any_success(self) -> None:
        watcher = WindowWatcher(provider_from_sequences([[], ["Main"]]), poll_interval=0.01)
        watcher.wait_for_any(timeout=0.2)

    def test_wait_for_any_timeout(self) -> None:
        watcher = WindowWatcher(lambda: [], poll_interval=0.01)
        with pytest.raises(AutomationError) as exc_info:
            watcher.wait_for_any(timeout=0.05)
        assert exc_info.value.error_code == "APP_NOT_FOUND"

    def test_get_current_state_with_windows(self) -> None:
        watcher = WindowWatcher(lambda: ["Export", "Save"], poll_interval=0.01)
        state = watcher.get_current_state()
        assert "Export" in state
        assert "Save" in state
        assert "Windows:" in state

    def test_get_current_state_empty(self) -> None:
        watcher = WindowWatcher(lambda: [], poll_interval=0.01)
        assert watcher.get_current_state() == "No windows visible"


# ---------------------------------------------------------------------------
# 6. File utilities
# ---------------------------------------------------------------------------


class TestFileUtils:
    def test_find_lines_files_single_file(self, tmp_path: Path) -> None:
        doc = tmp_path / "demo.lines"
        doc.write_text("data")
        assert find_lines_files(doc) == [doc]

    def test_find_lines_files_directory_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "b.lines").write_text("x")
        (tmp_path / "a.lines").write_text("x")
        files = find_lines_files(tmp_path)
        assert [p.name for p in files] == ["a.lines", "b.lines"]

    def test_find_lines_files_empty_dir(self, tmp_path: Path) -> None:
        assert find_lines_files(tmp_path) == []

    def test_find_lines_files_wrong_extension(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("x")
        assert find_lines_files(tmp_path) == []

    def test_validate_lines_file_valid(self, tmp_path: Path) -> None:
        doc = tmp_path / "valid.lines"
        doc.write_text("content")
        validate_lines_file(doc)

    def test_validate_lines_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileValidationError, match="does not exist"):
            validate_lines_file(tmp_path / "missing.lines")

    def test_validate_lines_file_empty(self, tmp_path: Path) -> None:
        doc = tmp_path / "empty.lines"
        doc.write_text("")
        with pytest.raises(FileValidationError, match="empty"):
            validate_lines_file(doc)

    def test_validate_lines_file_wrong_extension(self, tmp_path: Path) -> None:
        doc = tmp_path / "wrong.txt"
        doc.write_text("content")
        with pytest.raises(FileValidationError, match=r"Not a \.lines file"):
            validate_lines_file(doc)

    def test_validate_pdf_valid(self, tmp_path: Path) -> None:
        pdf = tmp_path / "valid.pdf"
        pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)
        assert validate_pdf(pdf) is True

    def test_validate_pdf_missing(self, tmp_path: Path) -> None:
        assert validate_pdf(tmp_path / "missing.pdf") is False

    def test_validate_pdf_too_small(self, tmp_path: Path) -> None:
        pdf = tmp_path / "tiny.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        assert validate_pdf(pdf) is False

    def test_validate_pdf_invalid_header(self, tmp_path: Path) -> None:
        pdf = tmp_path / "invalid.pdf"
        pdf.write_bytes(b"NOT A PDF\n" + b"x" * 2000)
        assert validate_pdf(pdf) is False

    def test_validate_svg_valid_xml(self, tmp_path: Path) -> None:
        svg = tmp_path / "valid.svg"
        svg.write_text('<?xml version="1.0"?><svg></svg>')
        assert validate_svg(svg) is True

    def test_validate_svg_valid_svg_tag(self, tmp_path: Path) -> None:
        svg = tmp_path / "valid.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        assert validate_svg(svg) is True

    def test_validate_svg_missing(self, tmp_path: Path) -> None:
        assert validate_svg(tmp_path / "missing.svg") is False

    def test_validate_svg_empty(self, tmp_path: Path) -> None:
        svg = tmp_path / "empty.svg"
        svg.write_text("")
        assert validate_svg(svg) is False

    def test_validate_svg_invalid_content(self, tmp_path: Path) -> None:
        svg = tmp_path / "invalid.svg"
        svg.write_text("not svg content at all")
        assert validate_svg(svg) is False

    def test_validate_export_dispatches(self, tmp_path: Path) -> None:
        pdf = tmp_path / "f.pdf"
        pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)
        assert validate_export(pdf, "pdf") is True
        assert validate_export(pdf, "unknown") is False

    def test_expected_export_path(self, tmp_path: Path) -> None:
        lines = tmp_path / "doc.lines"
        assert expected_export_path(lines, "pdf") == tmp_path / "doc.pdf"
        assert expected_export_path(lines, "svg") == tmp_path / "doc.svg"

    def test_resolve_output_path_none(self, tmp_path: Path) -> None:
        assert resolve_output_path(tmp_path / "a.lines", None, "pdf") is None

    def test_resolve_output_path_directory(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        result = resolve_output_path(tmp_path / "a.lines", out_dir, "pdf")
        assert result == out_dir / "a.pdf"

    def test_resolve_output_path_file(self, tmp_path: Path) -> None:
        out_file = tmp_path / "custom.pdf"
        result = resolve_output_path(tmp_path / "a.lines", out_file, "pdf")
        assert result == out_file


# ---------------------------------------------------------------------------
# 7. ExportStats
# ---------------------------------------------------------------------------


class TestExportStats:
    def test_record_success_and_failure(self, tmp_path: Path) -> None:
        stats = ExportStats()
        first = tmp_path / "ok.lines"
        second = tmp_path / "broken.lines"
        stats.record_success(first)
        stats.record_failure(second, "boom")
        assert stats.processed == 2
        assert stats.success == 1
        assert stats.failures == [(str(second), "boom")]

    def test_timing(self) -> None:
        stats = ExportStats()
        stats.record_success(Path("/tmp/a.lines"), elapsed=1.5)  # noqa: S108
        stats.record_success(Path("/tmp/b.lines"), elapsed=2.5)  # noqa: S108
        assert len(stats.file_times) == 2
        assert stats.get_average_time() == 2.0
        assert stats.get_total_time() > 0

    def test_skipped(self) -> None:
        stats = ExportStats()
        p = Path("/tmp/test.lines")  # noqa: S108
        stats.record_skipped(p)
        stats.record_success(p)
        stats.record_failure(p, "error")
        assert stats.processed == 3
        assert stats.skipped == 1
        assert stats.success == 1
        assert len(stats.failures) == 1

    def test_validation_failures(self) -> None:
        stats = ExportStats()
        p = Path("/tmp/test.lines")  # noqa: S108
        stats.record_success(p, elapsed=1.0)
        stats.record_failure(p, "Export failed")
        stats.record_validation_failure(p, "PDF validation failed")
        assert stats.success == 1
        assert len(stats.failures) == 1
        assert len(stats.validation_failures) == 1
        assert stats.processed == 3

    def test_as_dict(self) -> None:
        stats = ExportStats()
        stats.record_success(Path("/tmp/a.lines"), elapsed=1.5)  # noqa: S108
        data = stats.as_dict()
        assert data["processed"] == 1
        assert data["success"] == 1
        assert data["skipped"] == 0
        assert data["failed"] == 0
        assert "total_time" in data
        assert data["average_time"] == 1.5
        assert data["dry_run"] is False

    def test_human_summary(self) -> None:
        stats = ExportStats()
        p = Path("/tmp/test.lines")  # noqa: S108
        stats.record_skipped(p)
        stats.record_success(p, elapsed=1.0)
        summary = stats.human_summary()
        assert "1/2 exports succeeded" in summary
        assert "(1 skipped)" in summary
        assert "avg 1.0s per file" in summary

    def test_human_summary_dry_run(self) -> None:
        stats = ExportStats(dry_run=True)
        stats.record_success(Path("/tmp/test.lines"))  # noqa: S108
        summary = stats.human_summary()
        assert "dry-run" in summary


# ---------------------------------------------------------------------------
# 8. Errors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_automation_error_code(self) -> None:
        error = AutomationError("Test message", "TEST_CODE")
        assert str(error) == "Test message"
        assert error.error_code == "TEST_CODE"

    def test_automation_error_default_code(self) -> None:
        error = AutomationError("msg")
        assert error.error_code == "UNKNOWN"

    def test_file_validation_error(self) -> None:
        error = FileValidationError("File broken")
        assert error.error_code == "FILE_INVALID"

    def test_error_suggestions_known_codes(self) -> None:
        assert "timeout_multiplier" in get_error_suggestion("WINDOW_TIMEOUT")
        assert "responsive" in get_error_suggestion("WINDOW_TIMEOUT")
        assert "disk space" in get_error_suggestion("EXPORT_TIMEOUT")
        assert "export settings" in get_error_suggestion("INVALID_PDF")
        assert "plist" in get_error_suggestion("PLIST_ERROR").lower()
        assert "installed" in get_error_suggestion("APP_NOT_FOUND").lower()

    def test_error_suggestion_unknown(self) -> None:
        assert "Check logs" in get_error_suggestion("UNKNOWN_ERROR")

    def test_format_error_with_context(self) -> None:
        formatted = format_error_with_context("WINDOW_TIMEOUT", "Operation timed out", "/path/to/file.lines")
        assert "Operation timed out" in formatted
        assert "/path/to/file.lines" in formatted
        assert "timeout_multiplier" in formatted
        assert "→" in formatted

    def test_format_error_without_file(self) -> None:
        formatted = format_error_with_context("WINDOW_TIMEOUT", "Timed out")
        assert "Timed out" in formatted
        assert "→" in formatted


# ---------------------------------------------------------------------------
# 9. VexyLinesExporter dry-run
# ---------------------------------------------------------------------------


class TestExporterDryRun:
    def test_dry_run_counts_files(self, tmp_path: Path) -> None:
        (tmp_path / "demo.lines").write_text("content")
        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=True)
        stats = exporter.export(tmp_path)
        assert stats.success == 1
        assert stats.dry_run is True

    def test_dry_run_batch(self, tmp_path: Path) -> None:
        for i in range(3):
            (tmp_path / f"test{i}.lines").write_text("content")
        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=True)
        stats = exporter.export(tmp_path)
        assert stats.success == 3
        assert stats.processed == 3
        assert stats.dry_run is True

    def test_no_files_raises(self, tmp_path: Path) -> None:
        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=True)
        with pytest.raises(AutomationError) as exc_info:
            exporter.export(tmp_path)
        assert exc_info.value.error_code == "NO_FILES"

    def test_multiple_files_to_single_output_raises(self, tmp_path: Path) -> None:
        (tmp_path / "a.lines").write_text("content")
        (tmp_path / "b.lines").write_text("content")
        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=True)
        with pytest.raises(AutomationError) as exc_info:
            exporter.export(tmp_path, Path("/tmp/single.pdf"))  # noqa: S108
        assert exc_info.value.error_code == "INVALID_OUTPUT"

    def test_human_summary_in_dry_run(self, tmp_path: Path) -> None:
        for i in range(3):
            (tmp_path / f"test{i}.lines").write_text("content")
        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=True)
        stats = exporter.export(tmp_path)
        summary = stats.human_summary()
        assert "3/3 exports succeeded" in summary
        assert "dry-run" in summary


# ---------------------------------------------------------------------------
# 10. VexyLinesExporter mocked success path
# ---------------------------------------------------------------------------


class TestExporterMocked:
    def test_success_path(self, tmp_path: Path) -> None:
        lines_file = tmp_path / "doc.lines"
        lines_file.write_text("content")
        expected_pdf = tmp_path / "doc.pdf"

        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=False)

        mock_bridge = MagicMock(spec=AppleScriptBridge)
        mock_bridge.window_titles.side_effect = [
            [],
            ["doc.lines"],
            ["doc.lines"],
            ["doc.lines"],
        ]
        mock_bridge.is_menu_item_enabled.return_value = True

        def create_pdf_on_click(*_args, **_kwargs):
            expected_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)
            return True

        mock_bridge.click_menu_item.side_effect = create_pdf_on_click

        mock_bridge.open_file.return_value = None

        with (
            patch("vexy_lines_utils.exporter.PlistManager") as mock_plist_cls,
            patch("vexy_lines_utils.exporter.AppleScriptBridge", return_value=mock_bridge),
            patch("vexy_lines_utils.exporter.WindowWatcher") as mock_watcher_cls,
        ):
            mock_plist_cls.return_value.__enter__ = MagicMock(return_value=None)
            mock_plist_cls.return_value.__exit__ = MagicMock(return_value=False)

            mock_watcher = MagicMock()
            mock_watcher_cls.return_value = mock_watcher

            def wfc_side_effect(needle, *, present, timeout):
                pass

            mock_watcher.wait_for_contains.side_effect = wfc_side_effect
            mock_watcher.wait_for_any.return_value = None

            stats = exporter.export(lines_file)

        assert stats.success == 1
        assert stats.processed == 1
        assert len(stats.failures) == 0

    def test_skip_existing(self, tmp_path: Path) -> None:
        lines_file = tmp_path / "doc.lines"
        lines_file.write_text("content")
        existing_pdf = tmp_path / "doc.pdf"
        existing_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)

        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=False, force=False)

        with (
            patch("vexy_lines_utils.exporter.PlistManager") as mock_plist_cls,
            patch("vexy_lines_utils.exporter.AppleScriptBridge") as mock_bridge_cls,
            patch("vexy_lines_utils.exporter.WindowWatcher") as mock_watcher_cls,
        ):
            mock_plist_cls.return_value.__enter__ = MagicMock(return_value=None)
            mock_plist_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_watcher = MagicMock()
            mock_watcher_cls.return_value = mock_watcher
            mock_watcher.wait_for_any.return_value = None
            mock_bridge = mock_bridge_cls.return_value

            stats = exporter.export(lines_file)

        assert stats.skipped == 1
        mock_bridge.open_file.assert_not_called()

    def test_force_removes_existing(self, tmp_path: Path) -> None:
        lines_file = tmp_path / "doc.lines"
        lines_file.write_text("content")
        existing_pdf = tmp_path / "doc.pdf"
        existing_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)

        config = ExportConfig()
        exporter = VexyLinesExporter(config, dry_run=False, force=True)

        mock_bridge = MagicMock(spec=AppleScriptBridge)
        mock_bridge.window_titles.side_effect = [
            [],
            ["doc.lines"],
            ["doc.lines"],
        ]
        mock_bridge.is_menu_item_enabled.return_value = True

        def create_pdf_on_click(*_args, **_kwargs):
            existing_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)
            return True

        mock_bridge.click_menu_item.side_effect = create_pdf_on_click
        mock_bridge.open_file.return_value = None

        with (
            patch("vexy_lines_utils.exporter.PlistManager") as mock_plist_cls,
            patch("vexy_lines_utils.exporter.AppleScriptBridge", return_value=mock_bridge),
            patch("vexy_lines_utils.exporter.WindowWatcher") as mock_watcher_cls,
        ):
            mock_plist_cls.return_value.__enter__ = MagicMock(return_value=None)
            mock_plist_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_watcher = MagicMock()
            mock_watcher_cls.return_value = mock_watcher
            mock_watcher.wait_for_contains.side_effect = lambda *a, **kw: None
            mock_watcher.wait_for_any.return_value = None

            stats = exporter.export(lines_file)

        assert stats.success == 1
        mock_bridge.click_menu_item.assert_called()


# ---------------------------------------------------------------------------
# 11. CLI validation
# ---------------------------------------------------------------------------


class TestCLIValidation:
    def test_invalid_timeout_multiplier(self) -> None:
        cli = VexyLinesCLI()
        with pytest.raises(ValueError, match="timeout_multiplier"):
            cli.export("/tmp/fake.lines", timeout_multiplier=0.01)  # noqa: S108

    def test_invalid_max_retries_negative(self) -> None:
        cli = VexyLinesCLI()
        with pytest.raises(ValueError, match="max_retries"):
            cli.export("/tmp/fake.lines", max_retries=-1)  # noqa: S108

    def test_invalid_max_retries_too_high(self) -> None:
        cli = VexyLinesCLI()
        with pytest.raises(ValueError, match="max_retries"):
            cli.export("/tmp/fake.lines", max_retries=11)  # noqa: S108


# ---------------------------------------------------------------------------
# 12. MCP CLI subcommands
# ---------------------------------------------------------------------------


class TestMCPCLI:
    """Tests for MCP-related CLI subcommands."""

    def _make_mock_client(self):
        """Create a mock MCPClient that works as context manager."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        return mock_client

    def test_mcp_status_when_server_reachable_then_returns_ok(self):
        from vexy_lines_utils.mcp.types import DocumentInfo

        mock_client = self._make_mock_client()
        mock_client.get_document_info.return_value = DocumentInfo(
            width_mm=100, height_mm=80, resolution=300, units="px", has_changes=False
        )
        with patch("vexy_lines_utils.__main__.MCPClient", return_value=mock_client):
            cli = VexyLinesCLI()
            result = cli.mcp_status()
            assert result["status"] == "ok"

    def test_mcp_status_when_server_unreachable_then_returns_error(self):
        from vexy_lines_utils.mcp import MCPError

        with patch(
            "vexy_lines_utils.__main__.MCPClient",
            side_effect=MCPError("Connection refused"),
        ):
            cli = VexyLinesCLI()
            result = cli.mcp_status()
            assert "error" in result

    def test_tree_when_document_open_then_returns_tree_text(self):
        from vexy_lines_utils.mcp.types import LayerNode

        mock_client = self._make_mock_client()
        mock_client.get_layer_tree.return_value = LayerNode(
            id=1,
            type="document",
            caption="Root",
            visible=True,
            children=[
                LayerNode(
                    id=2,
                    type="group",
                    caption="Group 1",
                    visible=True,
                    children=[
                        LayerNode(id=3, type="layer", caption="Layer 1", visible=True),
                    ],
                )
            ],
        )
        with patch("vexy_lines_utils.__main__.MCPClient", return_value=mock_client):
            cli = VexyLinesCLI()
            result = cli.tree()
            assert "document" in result
            assert "Root" in result

    def test_tree_json_output_when_document_open_then_returns_json_string(self):
        from vexy_lines_utils.mcp.types import LayerNode

        mock_client = self._make_mock_client()
        mock_client.get_layer_tree.return_value = LayerNode(id=1, type="document", caption="Root", visible=True)
        with patch("vexy_lines_utils.__main__.MCPClient", return_value=mock_client):
            cli = VexyLinesCLI()
            result = cli.tree(json_output=True)
            assert '"id": 1' in result
            assert '"type": "document"' in result

    def test_new_document_when_called_then_returns_result_dict(self):
        from vexy_lines_utils.mcp.types import NewDocumentResult

        mock_client = self._make_mock_client()
        mock_client.new_document.return_value = NewDocumentResult(
            status="ok", width=800, height=600, dpi=300, root_id=42
        )
        with patch("vexy_lines_utils.__main__.MCPClient", return_value=mock_client):
            cli = VexyLinesCLI()
            result = cli.new_document(width=800, height=600)
            assert result["status"] == "ok"
            assert result["root_id"] == 42

    def test_render_when_called_then_returns_result_dict(self):
        mock_client = self._make_mock_client()
        mock_client.render_all.return_value = "Rendering started"
        with patch("vexy_lines_utils.__main__.MCPClient", return_value=mock_client):
            cli = VexyLinesCLI()
            result = cli.render()
            assert result["result"] == "Rendering started"

    def test_add_fill_when_called_then_sends_correct_args(self):
        mock_client = self._make_mock_client()
        mock_client.add_fill.return_value = {"id": 99}
        with patch("vexy_lines_utils.__main__.MCPClient", return_value=mock_client):
            cli = VexyLinesCLI()
            result = cli.add_fill(layer_id=5, fill_type="linear", color="#ff0000")
            assert result == {"id": 99}
            mock_client.add_fill.assert_called_once_with(layer_id=5, fill_type="linear", color="#ff0000")

    def test_open_document_when_called_then_returns_ok(self):
        mock_client = self._make_mock_client()
        mock_client.open_document.return_value = "Opened successfully"
        with patch("vexy_lines_utils.__main__.MCPClient", return_value=mock_client):
            cli = VexyLinesCLI()
            result = cli.open("/tmp/test.lines")  # noqa: S108
            assert result["status"] == "ok"
            assert result["result"] == "Opened successfully"
