#!/usr/bin/env python3
# this_file: tests/test_refactored_modules.py
"""Tests for refactored module structure."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Test automation module imports
from vexy_lines_utils.automation import (  # noqa: F401
    ApplicationBridge,
    PyXABridge,
    UIActions,
    WindowWatcher,
)

# Test CLI imports
from vexy_lines_utils.cli import VexyLinesCLI, main  # noqa: F401

# Test core module imports
from vexy_lines_utils.core import (
    AutomationConfig,
    AutomationError,
    EnhancedAutomationConfig,
    ExportStats,
    FileValidationError,
)
from vexy_lines_utils.core.config import DialogStrategy, MenuStrategy

# Test exporters module imports
from vexy_lines_utils.exporters import (  # noqa: F401
    BaseExporter,
    EnhancedVexyLinesExporter,
    VexyLinesExporter,
)

# Test strategies module imports
from vexy_lines_utils.strategies import (  # noqa: F401
    SmartDialogHandler,
    SmartMenuTrigger,
)

# Test utils module imports
from vexy_lines_utils.utils import (  # noqa: F401
    InterruptHandler,
    find_lines_files,
    speak,
    validate_lines_file,
    validate_pdf,
)


class TestCoreModules:
    """Test core module functionality."""

    def test_automation_config(self):
        """Test AutomationConfig creation and defaults."""
        config = AutomationConfig()
        assert config.app_name == "Vexy Lines"
        assert config.poll_interval == 0.2
        assert config.max_retries == 3

    def test_enhanced_automation_config(self):
        """Test EnhancedAutomationConfig creation and defaults."""
        config = EnhancedAutomationConfig()
        assert config.app_name == "Vexy Lines"
        assert MenuStrategy.KEYBOARD_SHORTCUT in config.menu_strategies
        assert DialogStrategy.COMMAND_SHIFT_G in config.dialog_strategies

    def test_automation_error(self):
        """Test AutomationError creation."""
        error = AutomationError("Test error", "TEST_CODE")
        assert str(error) == "Test error"
        assert error.error_code == "TEST_CODE"

    def test_file_validation_error(self):
        """Test FileValidationError creation."""
        error = FileValidationError("Invalid file")
        assert str(error) == "Invalid file"
        assert error.error_code == "FILE_INVALID"

    def test_export_stats(self):
        """Test ExportStats functionality."""
        stats = ExportStats()
        path = Path("test.lines")

        stats.record_success(path, elapsed=1.5)
        assert stats.success == 1
        assert stats.processed == 1
        assert 1.5 in stats.file_times

        stats.record_skipped(path)
        assert stats.skipped == 1
        assert stats.processed == 2

        stats.record_failure(path, "Test failure")
        assert len(stats.failures) == 1
        assert stats.processed == 3


class TestUtilsModules:
    """Test utils module functionality."""

    def test_find_lines_files(self, tmp_path):
        """Test finding .lines files."""
        # Create test files
        (tmp_path / "file1.lines").touch()
        (tmp_path / "file2.lines").touch()
        (tmp_path / "file3.txt").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file4.lines").touch()

        # Test finding files
        files = find_lines_files(tmp_path)
        assert len(files) == 3
        assert all(f.suffix == ".lines" for f in files)

    def test_validate_lines_file(self, tmp_path):
        """Test .lines file validation."""
        valid_file = tmp_path / "test.lines"
        valid_file.write_text("test content")

        # Should not raise for valid file
        validate_lines_file(valid_file)

        # Test invalid cases
        nonexistent = tmp_path / "nonexistent.lines"
        with pytest.raises(FileValidationError):
            validate_lines_file(nonexistent)

        empty_file = tmp_path / "empty.lines"
        empty_file.touch()
        with pytest.raises(FileValidationError):
            validate_lines_file(empty_file)

    def test_validate_pdf(self, tmp_path):
        """Test PDF validation."""
        valid_pdf = tmp_path / "test.pdf"
        valid_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 1024)

        assert validate_pdf(valid_pdf) is True

        # Invalid PDF header
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_bytes(b"NOT_A_PDF" + b"x" * 1024)
        assert validate_pdf(invalid_pdf) is False

        # Too small PDF
        small_pdf = tmp_path / "small.pdf"
        small_pdf.write_bytes(b"%PDF-")
        assert validate_pdf(small_pdf) is False

    def test_interrupt_handler(self):
        """Test InterruptHandler functionality."""
        handler = InterruptHandler()
        assert handler.check() is False
        # Would need to simulate signals for full test


class TestAutomationModules:
    """Test automation module functionality."""

    def test_window_watcher(self):
        """Test WindowWatcher functionality."""
        mock_provider = MagicMock(return_value=["Window 1", "Test Window"])
        watcher = WindowWatcher(title_provider=mock_provider)

        state = watcher.get_current_state()
        assert "Window 1" in state
        assert "Test Window" in state

    def test_ui_actions_dry_run(self):
        """Test UIActions in dry run mode."""
        ui = UIActions(dry_run=True)

        ui.press("enter")
        ui.hotkey("command", "c")
        ui.copy_text("test")

        assert "press:enter" in ui.recorded
        assert "hotkey:command+c" in ui.recorded
        assert "copy:test" in ui.recorded


class TestBackwardCompatibility:
    """Test that all original exports are still available."""

    def test_main_package_exports(self):
        """Test main package exports for backward compatibility."""
        import vexy_lines_utils

        # Original exports
        assert hasattr(vexy_lines_utils, "AutomationConfig")
        assert hasattr(vexy_lines_utils, "AutomationError")
        assert hasattr(vexy_lines_utils, "ExportStats")
        assert hasattr(vexy_lines_utils, "VexyLinesExporter")
        assert hasattr(vexy_lines_utils, "VexyLinesCLI")
        assert hasattr(vexy_lines_utils, "find_lines_files")
        assert hasattr(vexy_lines_utils, "main")
        assert hasattr(vexy_lines_utils, "__version__")

        # New enhanced exports
        assert hasattr(vexy_lines_utils, "EnhancedAutomationConfig")
        assert hasattr(vexy_lines_utils, "EnhancedVexyLinesExporter")
        assert hasattr(vexy_lines_utils, "InterruptHandler")


class TestCLI:
    """Test CLI functionality."""

    def test_cli_validation(self):
        """Test CLI argument validation."""
        cli = VexyLinesCLI()

        # Test timeout multiplier validation
        with pytest.raises(ValueError, match="timeout_multiplier"):
            cli.export("test", timeout_multiplier=0.01)  # Too low

        with pytest.raises(ValueError, match="timeout_multiplier"):
            cli.export("test", timeout_multiplier=100)  # Too high

        # Test max_retries validation
        with pytest.raises(ValueError, match="max_retries"):
            cli.export("test", max_retries=-1)  # Negative

        with pytest.raises(ValueError, match="max_retries"):
            cli.export("test", max_retries=20)  # Too high
