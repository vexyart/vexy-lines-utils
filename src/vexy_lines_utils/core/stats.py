#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/core/stats.py
"""Statistics tracking for batch operations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ExportStats:
    """Outcome of a batch operation."""

    processed: int = 0
    success: int = 0
    skipped: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    validation_failures: list[tuple[str, str]] = field(default_factory=list)
    dry_run: bool = False
    start_time: float = field(default_factory=time.monotonic)
    file_times: list[float] = field(default_factory=list)

    def record_success(self, path: Path, *, elapsed: float | None = None) -> None:
        """Record a successful export."""
        self.processed += 1
        self.success += 1
        if elapsed is not None:
            self.file_times.append(elapsed)
        logger.success(f"Exported {path.name}")

    def record_skipped(self, path: Path) -> None:
        """Record a file that was skipped (PDF already exists)."""
        self.processed += 1
        self.skipped += 1
        logger.info(f"Skipping {path.name} - PDF already exists")

    def record_failure(self, path: Path, reason: str) -> None:
        """Record a failed export."""
        self.processed += 1
        self.failures.append((str(path), reason))
        logger.error(f"{path.name} failed: {reason}")

    def record_validation_failure(self, path: Path, reason: str) -> None:
        """Record a PDF validation failure."""
        self.processed += 1
        self.validation_failures.append((str(path), reason))
        logger.error(f"{path.name} validation failed: {reason}")

    def get_total_time(self) -> float:
        """Get total elapsed time since stats tracking started."""
        return time.monotonic() - self.start_time

    def get_average_time(self) -> float:
        """Get average time per successfully exported file."""
        if not self.file_times:
            return 0.0
        return sum(self.file_times) / len(self.file_times)

    def as_dict(self) -> dict[str, object]:
        """Convert stats to dictionary."""
        return {
            "processed": self.processed,
            "success": self.success,
            "skipped": self.skipped,
            "failed": len(self.failures),
            "failures": list(self.failures),
            "validation_failed": len(self.validation_failures),
            "validation_failures": list(self.validation_failures),
            "dry_run": self.dry_run,
            "total_time": round(self.get_total_time(), 2),
            "average_time": round(self.get_average_time(), 2) if self.file_times else None,
        }

    def human_summary(self) -> str:
        """Get human-readable summary."""
        state = "dry-run " if self.dry_run else ""
        summary = f"{state}{self.success}/{self.processed} exports succeeded"
        if self.skipped > 0:
            summary += f" ({self.skipped} skipped)"
        if self.failures:
            summary += f", {len(self.failures)} failed"
        if self.validation_failures:
            summary += f", {len(self.validation_failures)} validation failed"
        if not self.dry_run and self.file_times:
            avg_time = self.get_average_time()
            summary += f", avg {avg_time:.1f}s per file"
        return summary
