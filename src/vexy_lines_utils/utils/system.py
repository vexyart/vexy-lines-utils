#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/utils/system.py
"""System-level utilities."""

from __future__ import annotations

import subprocess

from loguru import logger


def speak(text: str) -> None:
    """Use macOS VoiceOver to announce status, ignoring failures.

    Args:
        text: Text to speak via macOS 'say' command
    """
    try:
        subprocess.run(["say", text], check=False)  # noqa: S603, S607
    except Exception:  # pragma: no cover - best effort
        logger.debug("say command unavailable")
