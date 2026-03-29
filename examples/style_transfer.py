#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire", "loguru"]
# ///
# this_file: examples/style_transfer.py
"""Apply a .lines style to an image via MCP.

Extracts the fill structure (groups, layers, fills) from a .lines file and
applies it to any source image by driving Vexy Lines via its MCP API.
The result is exported as SVG.

Requires the Vexy Lines app to be running with the MCP server enabled
(Settings > MCP Server > Enable).

Usage:
    python style_transfer.py --style artwork.lines --image photo.jpg --output result.svg
    python style_transfer.py --style artwork.lines --image photo.jpg --output result.svg --dpi 150
"""

import sys
from pathlib import Path

import fire
from loguru import logger

from vexy_lines_utils.mcp import MCPClient, MCPError
from vexy_lines_utils.style import apply_style, extract_style


def style_transfer(
    *,
    style: str,
    image: str,
    output: str,
    dpi: int = 72,
    host: str = "127.0.0.1",
    port: int = 47384,
    timeout: float = 120.0,
    verbose: bool = False,
) -> None:
    """Apply a .lines style to an image and export SVG.

    Args:
        style: Path to the .lines file to extract the style from.
        image: Path to the source image (JPEG, PNG, TIFF, BMP, GIF, SVG, PDF).
        output: Destination path for the SVG output.
        dpi: Document DPI (lower = faster; 72 is good for screen, 300 for print).
        host: MCP server host address.
        port: MCP server port.
        timeout: Max seconds to wait for render completion.
        verbose: Enable debug logging.
    """
    if not verbose:
        logger.disable("vexy_lines_utils")

    style_path = Path(style)
    image_path = Path(image)
    output_path = Path(output)

    for p, _label in [(style_path, "Style"), (image_path, "Image")]:
        if not p.exists():
            sys.exit(1)

    # Extract fill structure from the .lines file (no app needed)
    extracted = extract_style(style_path)

    def _count_fills(nodes: list) -> tuple[int, int, int]:
        from vexy_lines_utils.parser import GroupInfo, LayerInfo

        g = la = fi = 0
        for node in nodes:
            if isinstance(node, GroupInfo):
                g += 1
                gg, ll, ff = _count_fills(node.children)
                g += gg
                la += ll
                fi += ff
            elif isinstance(node, LayerInfo):
                la += 1
                fi += len(node.fills)
        return g, la, fi

    _ng, _nl, _nf = _count_fills(extracted.groups)

    # Apply via MCP
    try:
        with MCPClient(host=host, port=port, timeout=timeout) as vl:
            svg_data = apply_style(vl, extracted, image_path, dpi=dpi)
    except MCPError:
        sys.exit(1)
    except ConnectionRefusedError:
        sys.exit(1)

    # Save SVG
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_data, encoding="utf-8")


if __name__ == "__main__":
    fire.Fire(style_transfer)
