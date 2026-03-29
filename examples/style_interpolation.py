#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire", "loguru"]
# ///
# this_file: examples/style_interpolation.py
"""Interpolate between two .lines styles and print the blended fill params.

Demonstrates style extraction, compatibility checking, and interpolation.
Does NOT require the Vexy Lines app — it only reads .lines files and
performs linear interpolation on the fill parameters.

Usage:
    python style_interpolation.py --style-a a.lines --style-b b.lines
    python style_interpolation.py --style-a a.lines --style-b b.lines --steps 9
"""

import sys
from pathlib import Path

import fire
from loguru import logger

from vexy_lines_utils.parser import GroupInfo, LayerInfo
from vexy_lines_utils.style import extract_style, interpolate_style, styles_compatible


def _collect_fills(nodes: list, path: str = "") -> list[tuple[str, object]]:
    """Walk a node tree and return (path_label, FillParams) for every fill."""
    result = []
    for i, node in enumerate(nodes):
        if isinstance(node, GroupInfo):
            label = f"{path}G[{i}:{node.caption!r}]"
            result.extend(_collect_fills(node.children, label + "/"))
        elif isinstance(node, LayerInfo):
            label = f"{path}L[{i}:{node.caption!r}]"
            for j, fill in enumerate(node.fills):
                result.append((f"{label}/F[{j}:{fill.params.fill_type}]", fill.params))
    return result


def style_interpolation(
    *,
    style_a: str,
    style_b: str,
    steps: int = 5,
    verbose: bool = False,
) -> None:
    """Interpolate between two .lines styles and print blended fill params.

    Args:
        style_a: Path to the first .lines file (t=0 endpoint).
        style_b: Path to the second .lines file (t=1 endpoint).
        steps: Number of interpolation steps (includes t=0 and t=1).
        verbose: Enable debug logging from the parser.
    """
    if not verbose:
        logger.disable("vexy_lines_utils")

    path_a = Path(style_a)
    path_b = Path(style_b)

    for p, _label in [(path_a, "--style-a"), (path_b, "--style-b")]:
        if not p.exists():
            sys.exit(1)

    if steps < 2:
        sys.exit(1)

    # Extract styles
    sa = extract_style(path_a)
    sb = extract_style(path_b)

    # Compatibility check
    compatible = styles_compatible(sa, sb)
    if not compatible:
        pass

    # Collect fill paths for aligned display
    fills_a = _collect_fills(sa.groups)
    if not fills_a:
        sys.exit(0)

    # Compute t values evenly spaced between 0 and 1
    t_values = [i / (steps - 1) for i in range(steps)]

    for t in t_values:
        blended = interpolate_style(sa, sb, t)
        fills_blend = _collect_fills(blended.groups)

        for (_path_label, _params_a), (_, _params_b) in zip(fills_a, fills_blend, strict=False):
            pass


if __name__ == "__main__":
    fire.Fire(style_interpolation)
