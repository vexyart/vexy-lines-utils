#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/utils/interrupt.py
"""Interrupt handling for graceful shutdowns."""

from __future__ import annotations

import signal
import sys

from loguru import logger


class InterruptHandler:
    """Gracefully handle Ctrl+C interruptions."""

    def __init__(self):
        self.interrupted = False
        self.original_handler = signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, sig, frame):
        if not self.interrupted:
            self.interrupted = True
            logger.warning("\n⚠️  Interrupt received. Finishing current file...")
            logger.info("Press Ctrl+C again to force quit")
        else:
            logger.error("\n❌ Force quit!")
            sys.exit(1)

    def restore(self):
        """Restore the original signal handler."""
        signal.signal(signal.SIGINT, self.original_handler)

    def check(self) -> bool:
        """Check if we should stop processing."""
        return self.interrupted
