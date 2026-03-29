#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire"]
# ///
# this_file: examples/test_export.py
"""Functional test: export a document in every supported format via MCP.

Requires Vexy Lines to be running with the MCP server active.
Creates a document, adds a fill, renders, then exports to PDF, SVG, PNG, JPEG, EPS.
Validates each export file for existence, size, and format-specific headers.

Usage:
    python test_export.py
    python test_export.py --source_image ~/Art/photo.jpg
    python test_export.py --keep          # don't delete temp exports
    python test_export.py --dpi 150       # lower DPI for faster raster export
    python test_export.py --timeout 180   # more time for large images
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import fire

from vexy_lines_utils.mcp import MCPClient, MCPError

if TYPE_CHECKING:
    from vexy_lines_utils.mcp.types import LayerNode


def _project_root() -> Path:
    """Detect project root via git rev-parse."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path(__file__).resolve().parent.parent


DEFAULT_IMAGE = _project_root() / "_private" / "mcp" / "girl2.jpeg"

# -- format validators --------------------------------------------------------

FORMATS = ["pdf", "svg", "png", "jpg", "eps"]


def _validate_pdf(path: Path) -> tuple[bool, str]:
    """Check PDF: exists, >1KB, starts with %PDF-."""
    if not path.exists():
        return False, "file does not exist"
    size = path.stat().st_size
    if size < 1024:
        return False, f"too small ({size} bytes, expected >1KB)"
    header = path.read_bytes()[:5]
    if header != b"%PDF-":
        return False, f"bad header: {header!r} (expected b'%PDF-')"
    return True, f"valid PDF, {size:,} bytes"


def _validate_svg(path: Path) -> tuple[bool, str]:
    """Check SVG: exists, >0, contains <svg or <?xml."""
    if not path.exists():
        return False, "file does not exist"
    size = path.stat().st_size
    if size == 0:
        return False, "file is empty"
    head = path.read_text(encoding="utf-8", errors="replace")[:2048]
    if "<svg" not in head and "<?xml" not in head:
        return False, f"no <svg or <?xml in first 2KB (got: {head[:80]!r}...)"
    return True, f"valid SVG, {size:,} bytes"


def _validate_png(path: Path) -> tuple[bool, str]:
    """Check PNG: exists, >1KB, starts with 0x89 P N G."""
    if not path.exists():
        return False, "file does not exist"
    size = path.stat().st_size
    if size < 1024:
        return False, f"too small ({size} bytes, expected >1KB)"
    header = path.read_bytes()[:4]
    if header != b"\x89PNG":
        return False, f"bad header: {header!r} (expected b'\\x89PNG')"
    return True, f"valid PNG, {size:,} bytes"


def _validate_jpeg(path: Path) -> tuple[bool, str]:
    """Check JPEG: exists, >1KB, starts with 0xff 0xd8."""
    if not path.exists():
        return False, "file does not exist"
    size = path.stat().st_size
    if size < 1024:
        return False, f"too small ({size} bytes, expected >1KB)"
    header = path.read_bytes()[:2]
    if header != b"\xff\xd8":
        return False, f"bad header: {header!r} (expected b'\\xff\\xd8')"
    return True, f"valid JPEG, {size:,} bytes"


def _validate_eps(path: Path) -> tuple[bool, str]:
    """Check EPS: exists, >0, starts with %!PS."""
    if not path.exists():
        return False, "file does not exist"
    size = path.stat().st_size
    if size == 0:
        return False, "file is empty"
    header = path.read_bytes()[:4]
    if header != b"%!PS":
        return False, f"bad header: {header!r} (expected b'%!PS')"
    return True, f"valid EPS, {size:,} bytes"


VALIDATORS = {
    "pdf": _validate_pdf,
    "svg": _validate_svg,
    "png": _validate_png,
    "jpg": _validate_jpeg,
    "eps": _validate_eps,
}


# -- tree helpers -------------------------------------------------------------


def _find_first(node: LayerNode, node_type: str) -> LayerNode | None:
    """Find the first node of a given type in the tree."""
    if node.type == node_type:
        return node
    for child in node.children:
        result = _find_first(child, node_type)
        if result:
            return result
    return None


# -- main test ----------------------------------------------------------------


def test_export(
    *,
    source_image: str | None = None,
    keep: bool = False,
    dpi: int = 300,
    timeout: int = 120,
    host: str = "127.0.0.1",
    port: int = 47384,
) -> None:
    """Export a document in every supported format and validate each output.

    Args:
        source_image: Path to source image. Defaults to _private/mcp/girl2.jpeg.
        keep: If True, don't delete the temp export directory.
        dpi: DPI for the document and raster exports.
        timeout: Max seconds to wait for render completion.
        host: MCP server host.
        port: MCP server port.
    """
    image = Path(source_image).expanduser().resolve() if source_image else DEFAULT_IMAGE
    if not image.exists():
        sys.exit(1)

    tmp_dir = Path(tempfile.mkdtemp(prefix="vexy_export_test_"))

    results: list[tuple[str, bool, str]] = []

    try:
        with MCPClient(host=host, port=port, timeout=float(timeout)) as vl:
            # -- 1. create document from source image -------------------------
            doc = vl.new_document(dpi=dpi, source_image=str(image))
            if doc.status != "ok":
                pass

            # -- 2. add a fill so there's content to export -------------------
            tree = vl.get_layer_tree()
            group = _find_first(tree, "group")
            group_id = group.id if group else doc.root_id

            layer = vl.add_layer(group_id=group_id)
            layer_id = layer.get("id", 0)
            vl.add_fill(
                layer_id=layer_id,
                fill_type="linear",
                color="#222222",
                params={"interval": 12, "angle": 45, "thickness": 1.5},
            )

            # -- 3. render and wait -------------------------------------------
            vl.render_all()
            rendered = vl.wait_for_render(timeout=float(timeout))
            if rendered:
                pass
            else:
                pass

            # -- 4. export each format ----------------------------------------
            for fmt in FORMATS:
                out_path = tmp_dir / f"export_test.{fmt}"
                label = fmt.upper()

                try:
                    vl.export_document(
                        path=str(out_path),
                        dpi=dpi,
                        format=fmt,
                    )

                    # Raster exports may be async — wait for file to appear and stabilize
                    _wait_for_file(out_path, max_wait=30)

                    validator = VALIDATORS[fmt]
                    passed, detail = validator(out_path)

                    if passed:
                        pass
                    else:
                        pass
                    results.append((label, passed, detail))

                except MCPError as e:
                    detail = f"MCP error: {e.message}"
                    results.append((label, False, detail))
                except Exception as e:
                    detail = f"unexpected error: {e}"
                    results.append((label, False, detail))

        # -- 5. summary -------------------------------------------------------
        for label, passed, detail in results:
            pass

        passed_count = sum(1 for _, p, _ in results if p)
        total = len(results)

        if passed_count < total:
            sys.exit(1)

    except MCPError:
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    finally:
        if keep:
            pass
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _wait_for_file(path: Path, max_wait: float = 30) -> None:
    """Wait for a file to appear and stop growing.

    Raster exports (PNG, JPEG) can be asynchronous — the MCP call returns
    before the file is fully written. Poll until the file exists and its
    size stabilises for two consecutive checks.
    """
    deadline = time.monotonic() + max_wait
    prev_size = -1

    while time.monotonic() < deadline:
        if path.exists():
            size = path.stat().st_size
            if size > 0 and size == prev_size:
                return  # file exists and size is stable
            prev_size = size
        time.sleep(0.5)

    # Don't raise — the validator will report the actual problem


if __name__ == "__main__":
    fire.Fire(test_export)
