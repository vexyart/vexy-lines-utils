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


def get_error_suggestion(error_code: str) -> str:
    """Get recovery suggestion for a given error code.

    Args:
        error_code: The automation error code

    Returns:
        Actionable suggestion for recovering from the error
    """
    suggestions = {
        "APP_NOT_FOUND": (
            "Ensure Vexy Lines is installed and try: "
            "(1) Launch Vexy Lines manually, "
            "(2) Check the app name in configuration, "
            "(3) Verify accessibility permissions"
        ),
        "OPEN_FAILED": (
            "Check: (1) File permissions are readable, (2) Vexy Lines can open .lines files, (3) File is not corrupted"
        ),
        "WINDOW_TIMEOUT": (
            "Try: "
            "(1) Increase timeout_multiplier in config, "
            "(2) Check if Vexy Lines is responsive, "
            "(3) Close other dialogs that may be blocking"
        ),
        "EXPORT_MENU_TIMEOUT": (
            "Verify: "
            "(1) Vexy Lines File menu has 'Export...' option, "
            "(2) A document is open and active, "
            "(3) Menu bar is accessible (not in fullscreen mode)"
        ),
        "SAVE_DIALOG_TIMEOUT": (
            "Check: "
            "(1) Save dialog appeared correctly, "
            "(2) No other dialogs are blocking, "
            "(3) Increase wait_for_dialog timeout if system is slow"
        ),
        "EXPORT_TIMEOUT": (
            "Consider: "
            "(1) Increase wait_for_file timeout for large/complex files, "
            "(2) Check available disk space, "
            "(3) Verify Vexy Lines is not frozen"
        ),
        "INVALID_PDF": (
            "Investigate: "
            "(1) Check export settings in Vexy Lines, "
            "(2) Verify sufficient disk space, "
            "(3) Try exporting manually to confirm it works"
        ),
        "FILE_INVALID": (
            "Fix: "
            "(1) Check file is a valid .lines format, "
            "(2) Verify file is not empty or corrupted, "
            "(3) Try opening in Vexy Lines manually"
        ),
        "NO_FILES": (
            "Ensure: "
            "(1) Path contains .lines files, "
            "(2) File extension is exactly '.lines' (case-sensitive), "
            "(3) Directory is accessible"
        ),
        "USER_INTERRUPT": (
            "Export interrupted by user (Ctrl+C). "
            "Current file may be incomplete. "
            "Restart export to continue from where it left off"
        ),
    }
    return suggestions.get(error_code, "Check logs for more details and try again")


def format_error_with_context(error_code: str, base_message: str, file_path: str | None = None) -> str:
    """Format error message with context and recovery suggestions.

    Args:
        error_code: The automation error code
        base_message: The base error message
        file_path: Optional file path for context

    Returns:
        Formatted error message with context and suggestions
    """
    parts = [base_message]

    if file_path:
        parts.append(f"File: {file_path}")

    suggestion = get_error_suggestion(error_code)
    parts.append(f"→ {suggestion}")

    return "\n".join(parts)
