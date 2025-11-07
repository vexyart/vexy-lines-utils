#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/core/errors.py
"""Error classes for Vexy Lines automation."""

from __future__ import annotations


class AutomationError(RuntimeError):
    """Raised when the automation flow cannot continue."""

    def __init__(self, message: str, error_code: str = "UNKNOWN") -> None:
        super().__init__(message)
        self.error_code = error_code


class FileValidationError(AutomationError):
    """Raised when a .lines file is invalid or corrupted."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "FILE_INVALID")
