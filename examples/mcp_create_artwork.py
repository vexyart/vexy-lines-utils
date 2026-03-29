#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire"]
# ///
# this_file: examples/mcp_create_artwork.py
"""Create a multi-fill artwork via the MCP API.

Loads a source image into Vexy Lines, adds a fill layer, renders it,
and exports the result. Uses the MCP server's direct export engine
(not OS automation), which supports more formats than the CLI exporter.

Source image formats: JPEG, PNG, TIFF, BMP, GIF, SVG, PDF
Export formats:       PDF, SVG, PNG, JPEG, EPS

Raster exports (PNG, JPEG) require a full pixel render and can be slow
for large or high-DPI documents. Use --timeout to increase the wait.

Usage:
    python mcp_create_artwork.py photo.jpg output.pdf
    python mcp_create_artwork.py photo.jpg output.svg
    python mcp_create_artwork.py photo.jpg output.png --dpi 150 --timeout 180
"""

import sys

import fire

from vexy_lines_utils.mcp import MCPClient, MCPError


def create_artwork(
    source_image: str,
    output_path: str,
    *,
    dpi: int = 300,
    host: str = "127.0.0.1",
    port: int = 47384,
    timeout: float = 120.0,
) -> None:
    """Create a multi-fill artwork and export it.

    Args:
        source_image: Path to source image (JPEG, PNG, TIFF, BMP, GIF, SVG, PDF).
        output_path: Export path. Format from extension: .pdf, .svg, .png, .jpg, .eps.
        dpi: Document resolution in dots per inch.
        host: MCP server address.
        port: MCP server port.
        timeout: Max seconds to wait for render and export. Increase for large
            raster exports (PNG/JPEG) at high DPI.
    """
    try:
        with MCPClient(host=host, port=port, timeout=timeout) as vl:
            # Create document from source image
            vl.new_document(dpi=dpi, source_image=source_image)

            # Get the root group
            tree = vl.get_layer_tree()
            root_id = tree.id

            # Add a linear engraving fill
            layer1 = vl.add_layer(group_id=root_id)
            vl.add_fill(
                layer_id=layer1["id"],
                fill_type="linear",
                color="#000000",
                params={"interval": 28, "angle": 45, "thickness": 27, "thickness_min": 0},
            )

            # Render and wait for completion
            vl.render_all()
            if not vl.wait_for_render(timeout=timeout):
                pass

            # Export
            vl.export_document(output_path)

    except MCPError:
        sys.exit(1)


if __name__ == "__main__":
    fire.Fire(create_artwork)
