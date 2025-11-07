#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/utils/file_utils.py
"""File handling utilities for Vexy Lines automation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.core.errors import FileValidationError

if TYPE_CHECKING:
    from pathlib import Path


def find_lines_files(path: Path) -> list[Path]:
    """Return sorted .lines files for the supplied target.

    Args:
        path: File or directory to search

    Returns:
        List of .lines file paths, sorted alphabetically
    """
    if path.is_file() and path.suffix.lower() == ".lines":
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.lines"))
    return []


def validate_lines_file(path: Path) -> None:
    """Validate that a .lines file is accessible and not corrupted.

    Args:
        path: Path to the .lines file

    Raises:
        FileValidationError: If file is invalid or inaccessible
    """
    if not path.exists():
        msg = f"File does not exist: {path}"
        raise FileValidationError(msg)

    if not path.is_file():
        msg = f"Not a file: {path}"
        raise FileValidationError(msg)

    if path.suffix.lower() != ".lines":
        msg = f"Not a .lines file: {path}"
        raise FileValidationError(msg)

    # Check file is readable and not empty
    try:
        size = path.stat().st_size
        if size == 0:
            msg = f"File is empty: {path}"
            raise FileValidationError(msg)
        # Very large files might indicate corruption
        if size > 500 * 1024 * 1024:  # 500MB
            logger.warning(f"Large file detected ({size // (1024 * 1024)} MB): {path}")
    except OSError as e:
        msg = f"Cannot access file {path}: {e}"
        raise FileValidationError(msg) from e


def validate_pdf(path: Path) -> bool:
    """Validate that an exported PDF file is complete and valid.

    Args:
        path: Path to the PDF file to validate

    Returns:
        True if PDF appears valid, False otherwise

    Checks:
        - File exists and is readable
        - File size is reasonable (>1KB, <500MB)
        - PDF magic bytes are correct (%PDF-)
    """
    min_pdf_size = 1024  # 1KB minimum for valid PDF
    max_pdf_size = 500 * 1024 * 1024  # 500MB warning threshold

    if not path.exists():
        logger.error(f"PDF does not exist: {path}")
        return False

    if not path.is_file():
        logger.error(f"PDF path is not a file: {path}")
        return False

    try:
        size = path.stat().st_size

        # Check minimum size (empty or nearly empty PDFs are invalid)
        if size < min_pdf_size:
            logger.error(f"PDF suspiciously small ({size} bytes): {path}")
            return False

        # Check maximum size (protect against runaway exports)
        if size > max_pdf_size:
            logger.warning(f"PDF unusually large ({size // (1024 * 1024)} MB): {path}")
            # Don't fail on large files, just warn

        # Verify PDF magic bytes
        with path.open("rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF-"):
                logger.error(f"Invalid PDF header (got {header!r}): {path}")
                return False

        logger.debug(f"PDF validation passed for {path.name} ({size} bytes)")
        return True

    except OSError as e:
        logger.error(f"Cannot access PDF {path}: {e}")
        return False
