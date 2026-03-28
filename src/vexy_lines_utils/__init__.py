#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/__init__.py
"""Public package interface for vexy_lines_utils."""

from __future__ import annotations

from vexy_lines_utils.__main__ import VexyLinesCLI, main
from vexy_lines_utils.__version__ import __version__
from vexy_lines_utils.automation.bridges import AppleScriptBridge, ApplicationBridge
from vexy_lines_utils.automation.window_watcher import WindowWatcher
from vexy_lines_utils.core.config import ExportConfig
from vexy_lines_utils.core.errors import AutomationError, FileValidationError
from vexy_lines_utils.core.plist import PlistManager
from vexy_lines_utils.core.stats import ExportStats
from vexy_lines_utils.exporter import VexyLinesExporter
from vexy_lines_utils.mcp.client import MCPClient, MCPError
from vexy_lines_utils.utils.file_utils import find_lines_files, validate_lines_file, validate_pdf, validate_svg
from vexy_lines_utils.utils.interrupt import InterruptHandler
from vexy_lines_utils.utils.system import speak

__all__ = [
    "AppleScriptBridge",
    "ApplicationBridge",
    "AutomationError",
    "ExportConfig",
    "ExportStats",
    "FileValidationError",
    "InterruptHandler",
    "MCPClient",
    "MCPError",
    "PlistManager",
    "VexyLinesCLI",
    "VexyLinesExporter",
    "WindowWatcher",
    "__version__",
    "find_lines_files",
    "main",
    "speak",
    "validate_lines_file",
    "validate_pdf",
    "validate_svg",
]
