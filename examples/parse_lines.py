#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire", "loguru"]
# ///
# this_file: examples/parse_lines.py
"""Parse a .lines file and print its structure.

Usage:
    python parse_lines.py path/to/file.lines
    python parse_lines.py path/to/file.lines --verbose
"""

import sys

import fire
from loguru import logger

from vexy_lines_utils.parser import GroupInfo, LayerInfo, LinesDocument, parse


def _print_node(node: GroupInfo | LayerInfo, indent: int = 0) -> None:
    """Recursively print a group or layer with its fills."""
    "  " * indent

    if isinstance(node, GroupInfo):
        for child in node.children:
            _print_node(child, indent + 1)

    elif isinstance(node, LayerInfo):
        for _fill in node.fills:
            pass


def _count_nodes(doc: LinesDocument) -> tuple[int, int, int]:
    """Return (groups, layers, fills) totals."""
    groups = layers = fills = 0

    def _walk(nodes: list) -> None:
        nonlocal groups, layers, fills
        for node in nodes:
            if isinstance(node, GroupInfo):
                groups += 1
                _walk(node.children)
            elif isinstance(node, LayerInfo):
                layers += 1
                fills += len(node.fills)

    _walk(doc.groups)
    return groups, layers, fills


def parse_lines(path: str, *, verbose: bool = False) -> None:
    """Parse a .lines file and print its structure.

    Args:
        path: Path to the .lines file.
        verbose: Show all fill raw attributes.
    """
    if not verbose:
        logger.disable("vexy_lines_utils")

    try:
        doc = parse(path)
    except FileNotFoundError:
        sys.exit(1)

    # Header

    f"{len(doc.source_image_data):,} bytes" if doc.source_image_data else "none"
    f"{len(doc.preview_image_data):,} bytes" if doc.preview_image_data else "none"

    _n_groups, _n_layers, _n_fills = _count_nodes(doc)

    # Tree
    for node in doc.groups:
        _print_node(node)


if __name__ == "__main__":
    fire.Fire(parse_lines)
