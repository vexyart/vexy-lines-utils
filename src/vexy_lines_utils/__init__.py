#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/__init__.py
"""Public package interface for vexy_lines_utils.

This package provides both standard and enhanced automation utilities for
batch exporting Vexy Lines documents to PDF format on macOS.
"""

from __future__ import annotations

# Import version
from vexy_lines_utils.__version__ import __version__

# Automation imports
from vexy_lines_utils.automation.bridges import ApplicationBridge, PyXABridge
from vexy_lines_utils.automation.ui_actions import UIActions
from vexy_lines_utils.automation.window_watcher import WindowWatcher

# CLI imports
from vexy_lines_utils.cli import VexyLinesCLI, main

# Core imports
from vexy_lines_utils.core.config import AutomationConfig, EnhancedAutomationConfig
from vexy_lines_utils.core.errors import AutomationError, FileValidationError
from vexy_lines_utils.core.stats import ExportStats
from vexy_lines_utils.exporters.enhanced import EnhancedVexyLinesExporter

# Exporter imports
from vexy_lines_utils.exporters.standard import VexyLinesExporter

# Utils imports
from vexy_lines_utils.utils.file_utils import find_lines_files, validate_lines_file, validate_pdf
from vexy_lines_utils.utils.interrupt import InterruptHandler
from vexy_lines_utils.utils.system import speak

__all__ = [
    # Automation
    "ApplicationBridge",
    # Core
    "AutomationConfig",
    "AutomationError",
    "EnhancedAutomationConfig",
    "EnhancedVexyLinesExporter",
    "ExportStats",
    "FileValidationError",
    "InterruptHandler",
    "PyXABridge",
    "UIActions",
    # CLI
    "VexyLinesCLI",
    # Exporters
    "VexyLinesExporter",
    "WindowWatcher",
    # Version
    "__version__",
    # Utils
    "find_lines_files",
    "main",
    "speak",
    "validate_lines_file",
    "validate_pdf",
]
