#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/video.py
"""Video-to-video processing through Vexy Lines vector art fills.

Extracts video frames, processes each through Vexy Lines (load, add fill,
render, export SVG), converts SVG to PNG via resvg, and reassembles into
a new video preserving fps and audio.

Requires optional dependencies: pip install vexy-lines-utils[video]
    - av (PyAV): video frame extraction and assembly
    - resvg-py: fast SVG-to-PNG rasterisation
    - Pillow: image format bridging

Pipeline per frame:
    video frame -> temp PNG -> Vexy Lines MCP (fill + render) -> SVG string
    -> resvg (SVG -> RGBA pixels) -> PIL Image -> PyAV frame -> output video
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from vexy_lines_utils.mcp.client import MCPClient

if TYPE_CHECKING:
    from collections.abc import Callable

    from PIL import Image as _Image

    from vexy_lines_utils.style import Style


def _require(package: str, pip_name: str | None = None) -> None:
    """Raise ImportError with install instructions if a package is missing."""
    import importlib  # noqa: PLC0415

    try:
        importlib.import_module(package)
    except ImportError:
        install = pip_name or package
        msg = (
            f"'{package}' is required for video processing. "
            f"Install it with: pip install {install}\n"
            f"Or install all video deps: pip install vexy-lines-utils[video]"
        )
        raise ImportError(msg) from None


@dataclass
class VideoInfo:
    """Video file metadata."""

    width: int
    height: int
    fps: float
    total_frames: int
    duration: float
    has_audio: bool


def probe(path: str | Path) -> VideoInfo:
    """Get video metadata without decoding frames.

    Args:
        path: Path to a video file.

    Returns:
        VideoInfo with dimensions, fps, frame count, duration, audio flag.
    """
    _require("av")
    import av  # noqa: PLC0415

    container = av.open(str(path))
    vs = container.streams.video[0]
    info = VideoInfo(
        width=vs.codec_context.width,
        height=vs.codec_context.height,
        fps=float(vs.average_rate or vs.guessed_rate or 24),
        total_frames=vs.frames or 0,
        duration=float(vs.duration * vs.time_base) if vs.duration else 0,
        has_audio=len(container.streams.audio) > 0,
    )
    container.close()
    return info


def _default_frame_params(frame_index: int, total_frames: int) -> dict:
    """Default per-frame parameters: rotate angle smoothly across the video."""
    progress = frame_index / max(total_frames - 1, 1)
    return {"angle": progress * 180.0}


def _svg_to_pil(svg_string: str, width: int, height: int) -> _Image.Image:
    """Convert SVG string to PIL Image, resized to target dimensions.

    Tries svglab first (handles mm dimensions natively), falls back to
    direct resvg_py with dimension patching.
    """
    from PIL import Image  # noqa: PLC0415

    try:
        from svglab import parse_svg  # noqa: PLC0415

        svg = parse_svg(svg_string)
        svg.width = width
        svg.height = height
        img = svg.render()
        if img.size != (width, height):
            img = img.resize((width, height), Image.LANCZOS)
        return img
    except ImportError:
        pass

    # Fallback: resvg_py returns PNG bytes — decode with PIL and resize
    import io  # noqa: PLC0415
    import re  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    import resvg_py  # noqa: PLC0415

    # Patch mm dimensions to px (resvg cannot parse mm units)
    svg_fixed = re.sub(r'width="[^"]*mm"', f'width="{width}px"', svg_string, count=1)
    svg_fixed = re.sub(r'height="[^"]*mm"', f'height="{height}px"', svg_fixed, count=1)

    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", encoding="utf-8", delete=False) as f:
        f.write(svg_fixed)
        tmp_svg = Path(f.name)
    try:
        png_bytes = resvg_py.svg_to_bytes(svg_path=str(tmp_svg), width=width, height=height)
        img = Image.open(io.BytesIO(bytes(png_bytes)))
        if img.size != (width, height):
            img = img.resize((width, height), Image.LANCZOS)
        return img
    finally:
        tmp_svg.unlink(missing_ok=True)


def process_video(
    input_path: str | Path,
    output_path: str | Path,
    *,
    fill_type: str = "linear",
    color: str = "#000000",
    interval: float = 20,
    thickness: float = 15,
    thickness_min: float = 0,
    dpi: int = 72,
    frame_params: Callable[[int, int], dict] | None = None,
    max_frames: int | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    host: str = "127.0.0.1",
    port: int = 47384,
    timeout: float = 60.0,
) -> VideoInfo:
    """Process a video through Vexy Lines vector art fills.

    Each frame is loaded into Vexy Lines, a fill is applied, the result
    is rendered and exported as SVG, then converted to PNG via resvg and
    written to the output video. Audio is copied from the original.

    Args:
        input_path: Input video file (MP4, MOV, AVI, WebM, etc.).
        output_path: Output video file path.
        fill_type: Fill algorithm — linear, wave, circular, radial, spiral,
            scribble, halftone, handmade, fractals, trace.
        color: Fill colour as hex string (e.g. "#000000").
        interval: Spacing between strokes in pixels.
        thickness: Maximum stroke thickness in pixels.
        thickness_min: Minimum stroke thickness in pixels.
        dpi: Document DPI. Lower = faster. 72 is good for video.
        frame_params: Optional callback ``(frame_index, total_frames) -> dict``
            returning fill parameter overrides per frame. When None, the angle
            rotates smoothly from 0 to 180 degrees across the video.
        max_frames: Process only the first N frames (useful for testing).
        on_progress: Optional callback ``(frame_index, total_frames) -> None``
            called after each frame is processed.
        host: MCP server address.
        port: MCP server port.
        timeout: Render timeout per frame in seconds.

    Returns:
        VideoInfo of the input video.

    Raises:
        ImportError: If av, resvg-py, or Pillow are not installed.
        MCPError: If the MCP server is unreachable or a tool call fails.
    """
    _require("av")
    _require("PIL", "Pillow")
    # Either svglab or resvg-py is needed for SVG→PNG
    try:
        _require("svglab")
    except ImportError:
        _require("resvg_py", "resvg-py")
    import av  # noqa: PLC0415

    input_path = Path(input_path)
    output_path = Path(output_path)

    # Probe
    info = probe(input_path)
    total = min(info.total_frames, max_frames) if max_frames and info.total_frames else info.total_frames
    if frame_params is None:
        frame_params = _default_frame_params

    base_params = {
        "interval": interval,
        "thickness": thickness,
        "thickness_min": thickness_min,
    }

    from fractions import Fraction

    tmp_dir = Path(tempfile.mkdtemp(prefix="vexy_video_"))
    # Write video-only first, then merge audio in a second pass
    video_only = tmp_dir / "video_only.mp4"
    frame_index = 0

    try:
        # Pass 1: decode frames, process through Vexy Lines, write video
        in_ctr = av.open(str(input_path))
        out_ctr = av.open(str(video_only), mode="w")

        in_video = in_ctr.streams.video[0]
        out_video = out_ctr.add_stream("libx264", rate=Fraction(info.fps).limit_denominator(10000))
        out_video.width = info.width
        out_video.height = info.height
        out_video.pix_fmt = "yuv420p"

        with MCPClient(host=host, port=port, timeout=timeout) as vl:
            for packet in in_ctr.demux(in_video):
                for frame in packet.decode():
                    if max_frames and frame_index >= max_frames:
                        break

                    # Frame → temp PNG
                    tmp_png = tmp_dir / f"f{frame_index:06d}.png"
                    frame.to_image().save(str(tmp_png))

                    # Load into Vexy Lines
                    vl.new_document(
                        width=info.width,
                        height=info.height,
                        dpi=dpi,
                        source_image=str(tmp_png),
                    )

                    # Add fill with per-frame params
                    tree = vl.get_layer_tree()
                    layer = vl.add_layer(group_id=tree.id)
                    params = {**base_params, **frame_params(frame_index, total or 1)}
                    vl.add_fill(
                        layer_id=layer["id"],
                        fill_type=fill_type,
                        color=color,
                        params=params,
                    )

                    # Render → SVG → PNG → output frame
                    vl.render(timeout=timeout)
                    svg_string = vl.svg()
                    pil_img = _svg_to_pil(svg_string, info.width, info.height).convert("RGB")

                    out_frame = av.VideoFrame.from_image(pil_img)
                    out_frame.pts = frame_index
                    for out_pkt in out_video.encode(out_frame):
                        out_ctr.mux(out_pkt)

                    tmp_png.unlink()
                    frame_index += 1

                    if on_progress:
                        on_progress(frame_index, total or 0)
                    logger.debug("Frame {}/{}: params={}", frame_index, total, params)

                if max_frames and frame_index >= max_frames:
                    break

        # Flush encoder
        for pkt in out_video.encode():
            out_ctr.mux(pkt)
        out_ctr.close()
        in_ctr.close()

        # Pass 2: merge audio from original via ffmpeg
        if info.has_audio:
            import subprocess

            merged = tmp_dir / "merged.mp4"
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_only),
                    "-i",
                    str(input_path),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-shortest",
                    str(merged),
                ],
                capture_output=True,
                timeout=120,
                check=True,
            )
            shutil.move(str(merged), str(output_path))
        else:
            shutil.move(str(video_only), str(output_path))

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info("Processed {} frames → {}", frame_index, output_path)
    return info


def process_video_with_style(
    input_path: str | Path,
    output_path: str | Path,
    *,
    style: Style,
    end_style: Style | None = None,
    dpi: int = 72,
    max_frames: int | None = None,
    start_frame: int = 0,
    end_frame: int | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    host: str = "127.0.0.1",
    port: int = 47384,
    timeout: float = 60.0,
) -> VideoInfo:
    """Process video using Style objects with optional interpolation.

    Like process_video() but uses extracted Style objects instead of
    hardcoded fill parameters. If end_style is provided, interpolates
    between style and end_style across frames.

    Args:
        input_path: Input video file (MP4, MOV, AVI, WebM, etc.).
        output_path: Output video file path.
        style: Style to apply to every frame (or start style when end_style given).
        end_style: Optional end style. When provided, interpolates between
            style (t=0) and end_style (t=1) across the processed frame range.
        dpi: Document DPI. Lower = faster. 72 is good for video.
        max_frames: Process only the first N frames from start_frame (testing).
        start_frame: Index of the first frame to process (0-based, inclusive).
        end_frame: Index of the last frame to process (0-based, exclusive).
            When None, processes to the last frame in the video.
        on_progress: Optional callback ``(frame_index, total_frames) -> None``
            called after each frame is processed. frame_index is relative to
            the full video frame count.
        host: MCP server address.
        port: MCP server port.
        timeout: Render timeout per frame in seconds.

    Returns:
        VideoInfo of the input video.

    Raises:
        ImportError: If av, resvg-py (or svglab), or Pillow are not installed.
        MCPError: If the MCP server is unreachable or a tool call fails.
    """
    # Runtime import to avoid circular dependency at module load time
    from vexy_lines_utils.style import apply_style, interpolate_style  # noqa: PLC0415

    _require("av")
    _require("PIL", "Pillow")
    try:
        _require("svglab")
    except ImportError:
        _require("resvg_py", "resvg-py")
    import av  # noqa: PLC0415

    input_path = Path(input_path)
    output_path = Path(output_path)

    # Probe the input video
    info = probe(input_path)

    # Determine the frame window to process
    frame_start = start_frame
    frame_end = end_frame if end_frame is not None else info.total_frames
    if max_frames is not None:
        frame_end = min(frame_end, frame_start + max_frames)
    total_to_process = max(frame_end - frame_start, 1)

    from fractions import Fraction  # noqa: PLC0415

    tmp_dir = Path(tempfile.mkdtemp(prefix="vexy_video_style_"))
    video_only = tmp_dir / "video_only.mp4"
    frame_index = 0  # absolute frame counter (within the full video decode)
    processed = 0   # frames actually encoded to output

    try:
        in_ctr = av.open(str(input_path))
        out_ctr = av.open(str(video_only), mode="w")

        in_video = in_ctr.streams.video[0]
        out_video = out_ctr.add_stream("libx264", rate=Fraction(info.fps).limit_denominator(10000))
        out_video.width = info.width
        out_video.height = info.height
        out_video.pix_fmt = "yuv420p"

        with MCPClient(host=host, port=port, timeout=timeout) as vl:
            for packet in in_ctr.demux(in_video):
                for frame in packet.decode():
                    if frame_index < frame_start:
                        frame_index += 1
                        continue
                    if frame_index >= frame_end:
                        break

                    # Determine the style for this frame
                    if end_style is not None:
                        t = (frame_index - frame_start) / max(total_to_process - 1, 1)
                        current_style = interpolate_style(style, end_style, t)
                    else:
                        current_style = style

                    # Frame → temp PNG
                    tmp_png = tmp_dir / f"f{frame_index:06d}.png"
                    frame.to_image().save(str(tmp_png))

                    # Apply style via MCP → SVG string
                    svg_string = apply_style(vl, current_style, tmp_png, dpi=dpi)

                    # SVG → PIL → output frame
                    pil_img = _svg_to_pil(svg_string, info.width, info.height).convert("RGB")
                    out_frame = av.VideoFrame.from_image(pil_img)
                    out_frame.pts = processed
                    for out_pkt in out_video.encode(out_frame):
                        out_ctr.mux(out_pkt)

                    tmp_png.unlink()
                    frame_index += 1
                    processed += 1

                    if on_progress:
                        on_progress(frame_index, info.total_frames)
                    logger.debug(
                        "Frame {}/{} (video frame {}): style={}",
                        processed,
                        total_to_process,
                        frame_index,
                        current_style.source_path,
                    )

                if frame_index >= frame_end:
                    break

        # Flush encoder
        for pkt in out_video.encode():
            out_ctr.mux(pkt)
        out_ctr.close()
        in_ctr.close()

        # Merge audio from original if present
        if info.has_audio:
            import subprocess  # noqa: PLC0415

            merged = tmp_dir / "merged.mp4"
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_only),
                    "-i",
                    str(input_path),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-shortest",
                    str(merged),
                ],
                capture_output=True,
                timeout=120,
                check=True,
            )
            shutil.move(str(merged), str(output_path))
        else:
            shutil.move(str(video_only), str(output_path))

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info("Processed {} frames ({}-{}) → {}", processed, frame_start, frame_end, output_path)
    return info
