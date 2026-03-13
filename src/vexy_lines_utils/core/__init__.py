#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/core/__init__.py
"""Core modules for vexy_lines_utils."""

from vexy_lines_utils.core.config import ExportConfig
from vexy_lines_utils.core.errors import (
    AutomationError,
    FileValidationError,
    format_error_with_context,
    get_error_suggestion,
)
from vexy_lines_utils.core.plist import PlistManager
from vexy_lines_utils.core.stats import ExportStats

__all__ = [
    "AutomationError",
    "ExportConfig",
    "ExportStats",
    "FileValidationError",
    "PlistManager",
    "format_error_with_context",
    "get_error_suggestion",
]
