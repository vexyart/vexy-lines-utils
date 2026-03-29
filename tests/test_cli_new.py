# this_file: tests/test_cli_new.py
"""Unit tests for VexyLinesCLI new subcommands: info, file_tree, extract_source,
extract_preview, batch_convert, gui."""

from __future__ import annotations

from pathlib import Path

import pytest

from vexy_lines_utils import VexyLinesCLI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "_private" / "lines-examples"
CHAMELEON = EXAMPLES_DIR / "Chameleon.lines"
GIRL_LINEAR = EXAMPLES_DIR / "girl-linear.lines"

_examples_available = EXAMPLES_DIR.exists() and CHAMELEON.exists() and GIRL_LINEAR.exists()
skip_if_no_examples = pytest.mark.skipif(not _examples_available, reason="Example .lines files not available")


# ---------------------------------------------------------------------------
# info subcommand
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_info_returns_dict_when_valid_file():
    cli = VexyLinesCLI()
    result = cli.info(str(CHAMELEON))
    assert isinstance(result, dict)
    for key in ("caption", "dpi", "groups", "layers", "fills"):
        assert key in result, f"Expected key '{key}' in result"


@skip_if_no_examples
def test_info_json_output_when_requested(capsys):
    cli = VexyLinesCLI()
    result = cli.info(str(CHAMELEON), json_output=True)
    assert isinstance(result, dict)
    for key in ("caption", "dpi", "groups", "layers", "fills"):
        assert key in result, f"Expected key '{key}' in result"
    captured = capsys.readouterr()
    assert '"dpi"' in captured.out


# ---------------------------------------------------------------------------
# file_tree subcommand
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_file_tree_returns_string_when_valid_file():
    cli = VexyLinesCLI()
    result = cli.file_tree(str(CHAMELEON))
    assert isinstance(result, str)
    assert len(result) > 0
    assert "layer" in result or "fill" in result


@skip_if_no_examples
def test_file_tree_json_output_when_requested():
    cli = VexyLinesCLI()
    result = cli.file_tree(str(CHAMELEON), json_output=True)
    assert isinstance(result, str)
    assert "layer" in result or "{" in result


# ---------------------------------------------------------------------------
# extract_source subcommand
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_extract_source_creates_file_when_valid(tmp_path: Path):
    cli = VexyLinesCLI()
    out = tmp_path / "src.jpg"
    result = cli.extract_source(str(CHAMELEON), output=str(out))
    assert isinstance(result, dict)
    assert "error" not in result
    assert out.exists()
    data = out.read_bytes()
    assert data[:3] == b"\xff\xd8\xff", "Expected JPEG magic bytes"


# ---------------------------------------------------------------------------
# extract_preview subcommand
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_extract_preview_creates_file_when_valid(tmp_path: Path):
    cli = VexyLinesCLI()
    out = tmp_path / "pre.png"
    result = cli.extract_preview(str(CHAMELEON), output=str(out))
    assert isinstance(result, dict)
    assert "error" not in result
    assert out.exists()
    data = out.read_bytes()
    assert data[:4] == b"\x89PNG", "Expected PNG magic bytes"


# ---------------------------------------------------------------------------
# batch_convert subcommand
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_batch_convert_extracts_previews_when_valid_dir(tmp_path: Path):
    cli = VexyLinesCLI()
    result = cli.batch_convert(input_dir=str(EXAMPLES_DIR), output_dir=str(tmp_path), format="png", what="preview")
    assert isinstance(result, dict)
    assert "total" in result
    assert result["total"] >= 1
    png_files = list(tmp_path.glob("*.png"))
    assert len(png_files) >= 1, "Expected at least one PNG file in output directory"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_info_returns_error_when_missing_file():
    cli = VexyLinesCLI()
    result = cli.info("/nonexistent/does-not-exist.lines")
    assert isinstance(result, dict)
    assert "error" in result


def test_extract_source_returns_error_when_missing(tmp_path: Path):
    cli = VexyLinesCLI()
    result = cli.extract_source("/nonexistent/does-not-exist.lines", output=str(tmp_path / "out.jpg"))
    assert isinstance(result, dict)
    assert "error" in result


# ---------------------------------------------------------------------------
# gui subcommand
# ---------------------------------------------------------------------------


def test_gui_method_exists():
    cli = VexyLinesCLI()
    assert hasattr(cli, "gui")
    assert callable(cli.gui)
