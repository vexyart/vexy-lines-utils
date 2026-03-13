#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/__main__.py
"""Command-line interface for Vexy Lines utils."""

from __future__ import annotations

from pathlib import Path

import fire
from loguru import logger

from vexy_lines_utils.core.config import ExportConfig
from vexy_lines_utils.exporter import VexyLinesExporter
from vexy_lines_utils.utils.system import speak


class VexyLinesCLI:
    """Fire CLI surface."""

    MIN_TIMEOUT_MULTIPLIER = 0.1
    MAX_TIMEOUT_MULTIPLIER = 10
    MAX_RETRY_LIMIT = 10

    def export(
        self,
        input: str,  # noqa: A002
        *,
        output: str | None = None,
        format: str = "pdf",  # noqa: A002
        verbose: bool = False,
        dry_run: bool = False,
        force: bool = False,
        say_summary: bool = False,
        timeout_multiplier: float = 1.0,
        max_retries: int = 3,
    ) -> dict[str, object]:
        """Export .lines documents to PDF or SVG.

        Uses dialog-less export via plist configuration: quits the app, sets
        export preferences, launches the app, opens each file, triggers the
        File > Export menu item, then restores original preferences on exit.

        Args:
            input: Path to a .lines file or directory to search for .lines files.
            output: Destination file (when input is a file) or directory (when
                input is a directory).  Defaults to the same folder as each
                input file.
            format: Export format — 'pdf' (default) or 'svg'.
            verbose: Show detailed progress messages.
            dry_run: Preview files that would be processed without exporting.
            force: Re-export even if the output file already exists.
            say_summary: Announce completion via text-to-speech.
            timeout_multiplier: Scale all timeouts (2.0 = double all timeouts).
            max_retries: Maximum retry attempts for transient failures (0-10).
        """
        if verbose:
            logger.enable("vexy_lines_utils")

        if timeout_multiplier < self.MIN_TIMEOUT_MULTIPLIER or timeout_multiplier > self.MAX_TIMEOUT_MULTIPLIER:
            msg = f"timeout_multiplier must be between {self.MIN_TIMEOUT_MULTIPLIER} and {self.MAX_TIMEOUT_MULTIPLIER}"
            raise ValueError(msg)
        if max_retries < 0 or max_retries > self.MAX_RETRY_LIMIT:
            msg = f"max_retries must be between 0 and {self.MAX_RETRY_LIMIT}"
            raise ValueError(msg)

        config = ExportConfig(
            format=format,
            timeout_multiplier=timeout_multiplier,
            max_retries=max_retries,
        )
        exporter = VexyLinesExporter(config, dry_run=dry_run, force=force)
        stats = exporter.export(
            Path(input),
            Path(output) if output else None,
        )

        if say_summary:
            speak(stats.human_summary())

        return stats.as_dict()


def main() -> None:
    fire.Fire(VexyLinesCLI)


if __name__ == "__main__":
    main()
