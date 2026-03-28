#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils[video]", "fire"]
# ///
# this_file: examples/mcp_create_video.py
"""Transform a video through Vexy Lines vector art fills.

Each frame is processed through Vexy Lines: load image, add fill, render,
export SVG, convert to PNG via resvg, assemble into output video with
original audio preserved.

Fill parameters can vary per frame — by default the angle rotates
smoothly across the video, creating an animated engraving effect.

Requires: Vexy Lines running with MCP server active.

Usage:
    python mcp_create_video.py input.mp4 output.mp4
    python mcp_create_video.py input.mp4 output.mp4 --fill_type wave
    python mcp_create_video.py input.mp4 output.mp4 --max_frames 10
    python mcp_create_video.py input.mp4 output.mp4 --interval 30 --thickness 25
"""

import sys

import fire

from vexy_lines_utils.mcp import MCPError
from vexy_lines_utils.video import probe, process_video


def create_video(
    input_path: str,
    output_path: str,
    *,
    fill_type: str = "linear",
    color: str = "#000000",
    interval: float = 20,
    thickness: float = 15,
    thickness_min: float = 0,
    dpi: int = 72,
    max_frames: int | None = None,
    timeout: float = 60.0,
) -> None:
    """Transform a video through Vexy Lines vector art fills.

    Args:
        input_path: Input video file (MP4, MOV, AVI, etc.).
        output_path: Output video file path.
        fill_type: Fill type — linear, wave, circular, radial, spiral,
            scribble, halftone, handmade, fractals, trace.
        color: Fill colour as hex string.
        interval: Spacing between strokes in pixels.
        thickness: Maximum stroke thickness in pixels.
        thickness_min: Minimum stroke thickness in pixels.
        dpi: Document DPI. Lower = faster. 72 is good for video.
        max_frames: Process only first N frames (for testing).
        timeout: Render timeout per frame in seconds.
    """
    # Show what we're working with
    info = probe(input_path)
    total = min(info.total_frames, max_frames) if max_frames else info.total_frames
    print(f"Input:  {input_path}")  # noqa: T201
    print(f"  {info.width}x{info.height} @ {info.fps:.1f} fps, {total} frames")  # noqa: T201
    if info.has_audio:
        print("  Audio: yes (will be copied)")  # noqa: T201
    print(f"Output: {output_path}")  # noqa: T201
    print(f"  Fill: {fill_type}, interval={interval}, thickness={thickness}, dpi={dpi}")  # noqa: T201
    print()  # noqa: T201

    def progress(i: int, n: int) -> None:
        print(f"  [{i}/{n}] Processed")  # noqa: T201

    process_video(
        input_path,
        output_path,
        fill_type=fill_type,
        color=color,
        interval=interval,
        thickness=thickness,
        thickness_min=thickness_min,
        dpi=dpi,
        max_frames=max_frames,
        on_progress=progress,
        timeout=timeout,
    )

    print(f"\nDone! {total} frames written to {output_path}")  # noqa: T201


if __name__ == "__main__":
    try:
        fire.Fire(create_video)
    except MCPError as e:
        print(f"MCP Error: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    except ImportError as e:
        print(f"Missing dependency: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped.")  # noqa: T201
        sys.exit(130)
