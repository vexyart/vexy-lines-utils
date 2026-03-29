#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire", "loguru", "Pillow"]
# ///
# this_file: examples/extract_images.py
"""Extract source and preview images from a .lines file.

The source image is stored as JPEG (base64 + zlib inside the XML).
The preview image is stored as PNG (base64 inside the XML).
Both are extracted and saved to disk without requiring the Vexy Lines app.

Usage:
    python extract_images.py portrait.lines
    python extract_images.py portrait.lines --output-dir /tmp/extracted
    python extract_images.py portrait.lines --source-only
    python extract_images.py portrait.lines --preview-only
"""

import sys
from pathlib import Path

import fire
from loguru import logger

from vexy_lines_utils.parser import parse


def _image_size(data: bytes, label: str) -> str:
    """Return a human-readable size string. Tries Pillow for pixel dimensions."""
    size_str = f"{len(data):,} bytes"
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(data))
        size_str += f"  {img.width}x{img.height} px"
    except Exception:
        pass
    return f"{label}: {size_str}"


def extract_images(
    path: str,
    *,
    output_dir: str | None = None,
    source_only: bool = False,
    preview_only: bool = False,
) -> None:
    """Extract source (JPEG) and preview (PNG) images from a .lines file.

    Args:
        path: Path to the .lines file.
        output_dir: Directory for saved images. Defaults to the same directory
            as the input file.
        source_only: Extract only the source image.
        preview_only: Extract only the preview image.
    """
    logger.disable("vexy_lines_utils")

    input_path = Path(path)
    if not input_path.exists():
        sys.exit(1)

    out_dir = Path(output_dir) if output_dir else input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = parse(input_path)
    except Exception:
        sys.exit(1)

    stem = input_path.stem
    saved: list[Path] = []

    # Source image (JPEG)
    if not preview_only:
        if doc.source_image_data is None:
            pass
        else:
            dest = out_dir / f"{stem}_source.jpg"
            dest.write_bytes(doc.source_image_data)
            saved.append(dest)

    # Preview image (PNG)
    if not source_only:
        if doc.preview_image_data is None:
            pass
        else:
            dest = out_dir / f"{stem}_preview.png"
            dest.write_bytes(doc.preview_image_data)
            saved.append(dest)

    if saved:
        pass
    else:
        pass


if __name__ == "__main__":
    fire.Fire(extract_images)
