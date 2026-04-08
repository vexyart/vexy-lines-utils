# this_file: src/vexy_lines_utils/gui/processing.py
"""Background processing logic for the GUI export pipeline.

Bridges the GUI's Export button to the style engine, parser, and video
modules.  All functions here run on a background thread -- GUI callbacks
(on_progress, on_complete, on_error) are expected to be thread-safe
(i.e. wrapped in ``app.after(0, ...)`` by the caller).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable


def process_export(
    mode: str,
    input_paths: list[str],
    style_path: str | None,
    end_style_path: str | None,
    output_path: str,
    fmt: str,
    size: str,
    *,
    audio: bool,
    frame_range: tuple[int, int] | None,
    on_progress: Callable[[int, int, str], None] | None = None,
    on_complete: Callable[[str], None] | None = None,
    on_error: Callable[[str], None] | None = None,
) -> None:
    """Run the export pipeline for the given mode.

    This function blocks until processing finishes.  It is designed to be
    called from a daemon thread so the GUI stays responsive.

    Args:
        mode: One of ``"lines"``, ``"images"``, ``"video"``.
        input_paths: File paths -- ``.lines`` files, image files, or a
            single-element list with the video path.
        style_path: Path to the start ``.lines`` style file (required for
            images/video modes).
        end_style_path: Optional end style for interpolation.
        output_path: Destination directory (non-MP4) or file path (MP4).
        fmt: Export format -- ``"SVG"``, ``"PNG"``, ``"JPG"``, ``"MP4"``,
            or ``"LINES"``.
        size: Size multiplier string -- ``"1x"``, ``"2x"``, etc.
        audio: Whether to include audio (video mode only).
        frame_range: ``(start_frame, end_frame)`` for video mode, or None.
        on_progress: ``(current, total, message)`` callback.
        on_complete: ``(success_message)`` callback.
        on_error: ``(error_message)`` callback.
    """
    try:
        if not input_paths:
            _report_error(on_error, "No input files selected.")
            return

        if mode == "lines":
            _process_lines(input_paths, output_path, fmt, on_progress, on_complete, on_error)
        elif mode == "images":
            _process_images(
                input_paths, style_path, end_style_path, output_path, fmt, size,
                on_progress, on_complete, on_error,
            )
        elif mode == "video":
            _process_video(
                input_paths[0], style_path, end_style_path, output_path, fmt, size,
                audio=audio, frame_range=frame_range,
                on_progress=on_progress, on_complete=on_complete, on_error=on_error,
            )
        else:
            _report_error(on_error, f"Unknown mode: {mode}")
    except Exception as exc:
        logger.exception("Export failed")
        _report_error(on_error, str(exc))


# ---------------------------------------------------------------------------
# Lines mode
# ---------------------------------------------------------------------------


def _process_lines(
    input_paths: list[str],
    output_path: str,
    fmt: str,
    on_progress: Callable[[int, int, str], None] | None,
    on_complete: Callable[[str], None] | None,
    on_error: Callable[[str], None] | None,
) -> None:
    """Process .lines files -- extract preview/source or copy."""
    from vexy_lines_utils.parser import parse  # noqa: PLC0415

    out_dir = Path(output_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(input_paths)

    for i, path in enumerate(input_paths):
        name = Path(path).stem
        _report_progress(on_progress, i, total, f"Processing {name}...")

        if fmt == "LINES":
            dest = out_dir / Path(path).name
            shutil.copy2(path, dest)

        elif fmt in ("PNG", "JPG"):
            doc = parse(path)
            if doc.preview_image_data is None:
                logger.warning("No preview image in {}, skipping", path)
                continue
            _save_image_bytes(doc.preview_image_data, out_dir / f"{name}.{fmt.lower()}", fmt)

        elif fmt == "SVG":
            _report_error(
                on_error,
                "SVG export from .lines files requires the Vexy Lines app (MCP). "
                "Use Images mode with a style instead.",
            )
            return

        else:
            _report_error(on_error, f"Unsupported format for Lines mode: {fmt}")
            return

    _report_progress(on_progress, total, total, "Done")
    _report_complete(on_complete, f"Exported {total} file(s) to {output_path}")


# ---------------------------------------------------------------------------
# Images mode
# ---------------------------------------------------------------------------


def _process_images(
    input_paths: list[str],
    style_path: str | None,
    end_style_path: str | None,
    output_path: str,
    fmt: str,
    size: str,
    on_progress: Callable[[int, int, str], None] | None,
    on_complete: Callable[[str], None] | None,
    on_error: Callable[[str], None] | None,
) -> None:
    """Apply a style (with optional interpolation) to each image via MCP."""
    from vexy_lines_utils.mcp.client import MCPClient, MCPError  # noqa: PLC0415
    from vexy_lines_utils.style import apply_style, extract_style, interpolate_style, styles_compatible  # noqa: PLC0415

    if not style_path:
        _report_error(on_error, "A style file is required for Images mode.")
        return

    out_dir = Path(output_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(input_paths)

    try:
        start_style = extract_style(style_path)
    except Exception as exc:
        _report_error(on_error, f"Failed to read style: {exc}")
        return

    end_style = None
    if end_style_path:
        try:
            end_style = extract_style(end_style_path)
        except Exception as exc:
            _report_error(on_error, f"Failed to read end style: {exc}")
            return
        if not styles_compatible(start_style, end_style):
            _report_error(on_error, "Start and end styles have incompatible structures.")
            return

    try:
        with MCPClient() as client:
            for i, img_path in enumerate(input_paths):
                name = Path(img_path).stem
                _report_progress(on_progress, i, total, f"Styling {name}...")

                if end_style is not None and total > 1:
                    t = i / max(total - 1, 1)
                    style = interpolate_style(start_style, end_style, t)
                else:
                    style = start_style

                svg_string = apply_style(client, style, img_path)

                if fmt == "SVG":
                    dest = out_dir / f"{name}.svg"
                    dest.write_text(svg_string, encoding="utf-8")
                elif fmt in ("PNG", "JPG"):
                    _save_svg_as_image(svg_string, out_dir / f"{name}.{fmt.lower()}", fmt, size)
                else:
                    _report_error(on_error, f"Unsupported format: {fmt}")
                    return

    except MCPError as exc:
        _report_error(on_error, f"MCP error: {exc.message}\n\nMake sure Vexy Lines is running.")
        return

    _report_progress(on_progress, total, total, "Done")
    _report_complete(on_complete, f"Exported {total} image(s) to {output_path}")


# ---------------------------------------------------------------------------
# Video mode
# ---------------------------------------------------------------------------


def _process_video(
    video_path: str,
    style_path: str | None,
    end_style_path: str | None,
    output_path: str,
    fmt: str,
    size: str,
    *,
    audio: bool,
    frame_range: tuple[int, int] | None,
    on_progress: Callable[[int, int, str], None] | None,
    on_complete: Callable[[str], None] | None,
    on_error: Callable[[str], None] | None,
) -> None:
    """Process video frames through the style engine."""
    from vexy_lines_utils.style import extract_style, styles_compatible  # noqa: PLC0415

    if not style_path:
        _report_error(on_error, "A style file is required for Video mode.")
        return

    try:
        start_style = extract_style(style_path)
    except Exception as exc:
        _report_error(on_error, f"Failed to read style: {exc}")
        return

    end_style = None
    if end_style_path:
        try:
            end_style = extract_style(end_style_path)
        except Exception as exc:
            _report_error(on_error, f"Failed to read end style: {exc}")
            return
        if not styles_compatible(start_style, end_style):
            _report_error(on_error, "Start and end styles have incompatible structures.")
            return

    if fmt == "MP4":
        _process_video_to_mp4(
            video_path, start_style, end_style, output_path, size,
            audio=audio, frame_range=frame_range,
            on_progress=on_progress, on_complete=on_complete, on_error=on_error,
        )
    elif fmt in ("SVG", "PNG", "JPG"):
        _process_video_to_frames(
            video_path, start_style, end_style, output_path, fmt, size,
            frame_range=frame_range,
            on_progress=on_progress, on_complete=on_complete, on_error=on_error,
        )
    else:
        _report_error(on_error, f"Unsupported format for Video mode: {fmt}")


def _process_video_to_mp4(
    video_path: str,
    start_style: object,
    end_style: object | None,
    output_path: str,
    size: str,
    *,
    audio: bool,
    frame_range: tuple[int, int] | None,
    on_progress: Callable[[int, int, str], None] | None,
    on_complete: Callable[[str], None] | None,
    on_error: Callable[[str], None] | None,
) -> None:
    """Render video frames through the style engine and reassemble as MP4."""
    import tempfile  # noqa: PLC0415

    from vexy_lines_utils.mcp.client import MCPClient, MCPError  # noqa: PLC0415
    from vexy_lines_utils.style import apply_style, interpolate_style  # noqa: PLC0415
    from vexy_lines_utils.video import _svg_to_pil, probe  # noqa: PLC0415

    try:
        import cv2  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
    except ImportError:
        _report_error(
            on_error,
            "opencv-python-headless is required for MP4 export. "
            "Install with: pip install opencv-python-headless",
        )
        return

    from PIL import Image  # noqa: PLC0415

    info = probe(video_path)
    start_frame = frame_range[0] if frame_range else 1
    end_frame = frame_range[1] if frame_range else info.total_frames
    total = end_frame - start_frame + 1
    scale = _parse_size_multiplier(size)

    out_w = int(info.width * scale)
    out_h = int(info.height * scale)

    tmp_dir = Path(tempfile.mkdtemp(prefix="vexy_gui_video_"))
    video_only = tmp_dir / "video_only.mp4"
    processed = 0

    cap = cv2.VideoCapture(str(video_path))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_only), fourcc, info.fps, (out_w, out_h))

    try:
        frame_index = 0

        with MCPClient() as client:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_index += 1
                if frame_index < start_frame:
                    continue
                if frame_index > end_frame:
                    break

                _report_progress(on_progress, processed, total, f"Frame {processed + 1}/{total}")

                tmp_png = tmp_dir / f"f{processed:06d}.png"
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                pil_img.save(str(tmp_png))

                if end_style is not None and total > 1:
                    t = processed / max(total - 1, 1)
                    style = interpolate_style(start_style, end_style, t)
                else:
                    style = start_style

                svg_string = apply_style(client, style, str(tmp_png))
                pil_result = _svg_to_pil(svg_string, out_w, out_h).convert("RGB")

                out_bgr = cv2.cvtColor(np.array(pil_result), cv2.COLOR_RGB2BGR)
                writer.write(out_bgr)

                tmp_png.unlink(missing_ok=True)
                processed += 1

        cap.release()
        writer.release()

        output = Path(output_path)
        if audio and info.has_audio and frame_range == (1, info.total_frames):
            import subprocess  # noqa: PLC0415

            merged = tmp_dir / "merged.mp4"
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "ffmpeg", "-y",
                    "-i", str(video_only),
                    "-i", str(video_path),
                    "-c:v", "copy", "-c:a", "aac",
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-shortest", str(merged),
                ],
                capture_output=True, timeout=120, check=True,
            )
            shutil.move(str(merged), str(output))
        else:
            shutil.move(str(video_only), str(output))

    except MCPError as exc:
        _report_error(on_error, f"MCP error: {exc.message}\n\nMake sure Vexy Lines is running.")
        return
    finally:
        cap.release()
        writer.release()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    _report_progress(on_progress, total, total, "Done")
    _report_complete(on_complete, f"Exported {processed} frames to {output_path}")


def _process_video_to_frames(
    video_path: str,
    start_style: object,
    end_style: object | None,
    output_path: str,
    fmt: str,
    size: str,
    *,
    frame_range: tuple[int, int] | None,
    on_progress: Callable[[int, int, str], None] | None,
    on_complete: Callable[[str], None] | None,
    on_error: Callable[[str], None] | None,
) -> None:
    """Extract video frames, style them, and save as individual files."""
    import tempfile  # noqa: PLC0415

    from vexy_lines_utils.mcp.client import MCPClient, MCPError  # noqa: PLC0415
    from vexy_lines_utils.style import apply_style, interpolate_style  # noqa: PLC0415
    from vexy_lines_utils.video import probe  # noqa: PLC0415

    try:
        import cv2  # noqa: PLC0415
    except ImportError:
        _report_error(
            on_error,
            "opencv-python-headless is required for video frame extraction. "
            "Install with: pip install opencv-python-headless",
        )
        return

    from PIL import Image  # noqa: PLC0415

    info = probe(video_path)
    start_frame = frame_range[0] if frame_range else 1
    end_frame = frame_range[1] if frame_range else info.total_frames
    total = end_frame - start_frame + 1
    scale = _parse_size_multiplier(size)

    out_w = int(info.width * scale)
    out_h = int(info.height * scale)

    out_dir = Path(output_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="vexy_gui_frames_"))
    processed = 0

    cap = cv2.VideoCapture(str(video_path))

    try:
        frame_index = 0

        with MCPClient() as client:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_index += 1
                if frame_index < start_frame:
                    continue
                if frame_index > end_frame:
                    break

                _report_progress(on_progress, processed, total, f"Frame {processed + 1}/{total}")

                tmp_png = tmp_dir / f"f{processed:06d}.png"
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                pil_img.save(str(tmp_png))

                if end_style is not None and total > 1:
                    t = processed / max(total - 1, 1)
                    style = interpolate_style(start_style, end_style, t)
                else:
                    style = start_style

                svg_string = apply_style(client, style, str(tmp_png))

                name = f"frame_{processed:06d}"
                if fmt == "SVG":
                    dest = out_dir / f"{name}.svg"
                    dest.write_text(svg_string, encoding="utf-8")
                elif fmt in ("PNG", "JPG"):
                    _save_svg_as_image(
                        svg_string, out_dir / f"{name}.{fmt.lower()}",
                        fmt, size, out_w, out_h,
                    )

                tmp_png.unlink(missing_ok=True)
                processed += 1

        cap.release()

    except MCPError as exc:
        _report_error(on_error, f"MCP error: {exc.message}\n\nMake sure Vexy Lines is running.")
        return
    finally:
        cap.release()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    _report_progress(on_progress, total, total, "Done")
    _report_complete(on_complete, f"Exported {processed} frame(s) to {output_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_size_multiplier(size: str) -> float:
    """Parse ``"1x"``, ``"2x"`` etc. into a float multiplier."""
    size = size.strip().lower().rstrip("x")
    try:
        return max(1.0, float(size))
    except (ValueError, TypeError):
        return 1.0


def _save_image_bytes(data: bytes, dest: Path, fmt: str) -> None:
    """Save raw image bytes (PNG) to *dest*, converting format if needed."""
    import io  # noqa: PLC0415

    from PIL import Image  # noqa: PLC0415

    img = Image.open(io.BytesIO(data))
    if fmt == "JPG":
        img = img.convert("RGB")
        img.save(dest, format="JPEG", quality=95)
    else:
        img.save(dest, format=fmt)


def _save_svg_as_image(
    svg_string: str,
    dest: Path,
    fmt: str,
    size: str,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """Rasterise an SVG string and save as PNG or JPG.

    If *width*/*height* are not provided, they are estimated from the SVG
    viewBox and the size multiplier.
    """
    from vexy_lines_utils.video import _svg_to_pil  # noqa: PLC0415

    if width is None or height is None:
        width, height = _estimate_svg_dimensions(svg_string, size)

    img = _svg_to_pil(svg_string, width, height)
    if fmt == "JPG":
        img = img.convert("RGB")
        img.save(dest, format="JPEG", quality=95)
    else:
        img.save(dest, format=fmt)


def _estimate_svg_dimensions(svg_string: str, size: str) -> tuple[int, int]:
    """Best-effort extraction of pixel dimensions from an SVG string."""
    import re  # noqa: PLC0415

    scale = _parse_size_multiplier(size)

    vb_match = re.search(r'viewBox="([^"]+)"', svg_string)
    if vb_match:
        parts = vb_match.group(1).split()
        if len(parts) >= 4:  # noqa: PLR2004
            try:
                w = int(float(parts[2]) * scale)
                h = int(float(parts[3]) * scale)
                return max(1, w), max(1, h)
            except (ValueError, IndexError):
                pass

    w_match = re.search(r'width="([\d.]+)', svg_string)
    h_match = re.search(r'height="([\d.]+)', svg_string)
    if w_match and h_match:
        try:
            w = int(float(w_match.group(1)) * scale)
            h = int(float(h_match.group(1)) * scale)
            return max(1, w), max(1, h)
        except (ValueError, IndexError):
            pass

    default = int(1024 * scale)
    return default, default


def _report_progress(
    callback: Callable[[int, int, str], None] | None,
    current: int,
    total: int,
    message: str,
) -> None:
    """Safely invoke a progress callback."""
    if callback is not None:
        try:
            callback(current, total, message)
        except Exception:
            logger.debug("Progress callback failed")


def _report_complete(callback: Callable[[str], None] | None, message: str) -> None:
    """Safely invoke a completion callback."""
    if callback is not None:
        try:
            callback(message)
        except Exception:
            logger.debug("Complete callback failed")


def _report_error(callback: Callable[[str], None] | None, message: str) -> None:
    """Safely invoke an error callback."""
    logger.error("Export error: {}", message)
    if callback is not None:
        try:
            callback(message)
        except Exception:
            logger.debug("Error callback failed")
