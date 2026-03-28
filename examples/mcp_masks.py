#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire"]
# ///
# this_file: examples/mcp_masks.py
"""Apply SVG path masks to restrict fills to specific regions.

Creates a circular mask on a fill layer, useful for isolating
features like eyes, faces, or specific areas of interest.

Requires a document to be already open in Vexy Lines.

Usage:
    python mcp_masks.py 42
    python mcp_masks.py 42 --mode add
"""
import sys

import fire

from vexy_lines_utils.mcp import MCPClient, MCPError

# SVG paths for elliptical eye-shaped masks (pixel coordinates)
EYE_MASK_LEFT = (
    "M 680 410 C 720 360 820 360 860 410 "
    "C 900 460 900 530 860 570 "
    "C 820 610 720 610 680 570 "
    "C 640 530 640 460 680 410 Z"
)
EYE_MASK_RIGHT = (
    "M 1180 410 C 1220 360 1320 360 1360 410 "
    "C 1400 460 1400 530 1360 570 "
    "C 1320 610 1220 610 1180 570 "
    "C 1140 530 1140 460 1180 410 Z"
)


def apply_masks(
    layer_id: int,
    *,
    mode: str = "create",
    host: str = "127.0.0.1",
    port: int = 47384,
) -> None:
    """Apply eye-shaped SVG masks to a layer.

    Args:
        layer_id: Target layer ID (get from `vexy-lines-utils tree`).
        mode: Mask mode — 'create' (replace), 'add' (union), 'sub' (subtract).
    """
    try:
        with MCPClient(host=host, port=port) as vl:
            print(f"Applying eye masks to layer {layer_id} (mode={mode})...")
            vl.set_layer_mask(
                layer_id=layer_id,
                paths=[EYE_MASK_LEFT, EYE_MASK_RIGHT],
                mode=mode,
            )
            print("Masks applied. Triggering render...")
            vl.render_all()
            vl.wait_for_render()
            print("Done! Fills should only appear in the eye regions.")
    except MCPError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    fire.Fire(apply_masks)
