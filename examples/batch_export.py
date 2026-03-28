#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire"]
# ///
# this_file: examples/batch_export.py
"""Batch export .lines documents to PDF or SVG.

Usage:
    python batch_export.py ~/Documents/vexy-projects
    python batch_export.py ~/Art/portrait.lines --format svg --verbose
"""
from pathlib import Path

import fire

from vexy_lines_utils import ExportConfig, VexyLinesExporter


def batch_export(
    input: str,
    *,
    format: str = "pdf",
    output: str | None = None,
    verbose: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Export .lines files to PDF or SVG."""
    config = ExportConfig(format=format)
    exporter = VexyLinesExporter(config, dry_run=dry_run, force=force)

    stats = exporter.export(Path(input), Path(output) if output else None)

    print(stats.human_summary())
    for path, reason in stats.failures:
        print(f"  Failed: {path} — {reason}")


if __name__ == "__main__":
    fire.Fire(batch_export)
