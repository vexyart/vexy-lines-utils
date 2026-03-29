# this_file: tests/test_style.py
"""Unit tests for vexy_lines_utils.style — style extraction, compatibility, and interpolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from vexy_lines_utils.parser import DocumentProps, FillNode, GroupInfo, LayerInfo
from vexy_lines_utils.style import (
    Style,
    _lerp,
    _lerp_color,
    extract_style,
    interpolate_style,
    styles_compatible,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "_private" / "lines-examples"
CHAMELEON = EXAMPLES_DIR / "Chameleon.lines"
GIRL_LINEAR = EXAMPLES_DIR / "girl-linear.lines"

_examples_available = EXAMPLES_DIR.exists() and CHAMELEON.exists() and GIRL_LINEAR.exists()
skip_if_no_examples = pytest.mark.skipif(not _examples_available, reason="Example .lines files not available")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_any_fill(nodes: list[GroupInfo | LayerInfo]) -> FillNode | None:
    """Recursively find the first FillNode in a style tree."""
    for node in nodes:
        if isinstance(node, GroupInfo):
            found = _find_any_fill(node.children)
            if found:
                return found
        elif isinstance(node, LayerInfo):
            if node.fills:
                return node.fills[0]
    return None


# ---------------------------------------------------------------------------
# 1. extract_style returns Style with non-empty groups
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_extract_style_returns_style_when_valid_file():
    style = extract_style(CHAMELEON)
    assert isinstance(style, Style)
    assert len(style.groups) > 0


# ---------------------------------------------------------------------------
# 2. extract_style has valid DocumentProps
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_extract_style_has_props_when_valid_file():
    style = extract_style(CHAMELEON)
    props = style.props
    assert isinstance(props, DocumentProps)
    assert props.width_mm > 0
    assert props.height_mm > 0
    assert props.dpi > 0


# ---------------------------------------------------------------------------
# 3. Chameleon fills have fill_type set
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_extract_style_has_fills_when_chameleon():
    style = extract_style(CHAMELEON)
    fill = _find_any_fill(style.groups)
    assert fill is not None, "Expected at least one fill in Chameleon.lines"
    assert fill.params.fill_type is not None
    assert len(fill.params.fill_type) > 0


# ---------------------------------------------------------------------------
# 4. Same file extracted twice is compatible
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_styles_compatible_when_same_file():
    a = extract_style(CHAMELEON)
    b = extract_style(CHAMELEON)
    assert styles_compatible(a, b) is True


# ---------------------------------------------------------------------------
# 5. Different-structure files are not compatible
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_styles_not_compatible_when_different_structure():
    a = extract_style(CHAMELEON)
    b = extract_style(GIRL_LINEAR)
    # Chameleon and girl-linear have different group/layer/fill structures
    assert styles_compatible(a, b) is False


# ---------------------------------------------------------------------------
# 6. interpolate at t=0 returns start style params
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_interpolate_style_at_zero_returns_start():
    a = extract_style(CHAMELEON)
    b = extract_style(CHAMELEON)
    result = interpolate_style(a, b, 0.0)
    fill_a = _find_any_fill(a.groups)
    fill_r = _find_any_fill(result.groups)
    assert fill_a is not None
    assert fill_r is not None
    # Numeric params should match a at t=0
    if fill_a.params.interval is not None and fill_r.params.interval is not None:
        assert abs(fill_r.params.interval - fill_a.params.interval) < 1e-9


# ---------------------------------------------------------------------------
# 7. interpolate at t=1.0 returns end style params
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_interpolate_style_at_one_returns_end():
    a = extract_style(CHAMELEON)
    b = extract_style(CHAMELEON)
    result = interpolate_style(a, b, 1.0)
    fill_b = _find_any_fill(b.groups)
    fill_r = _find_any_fill(result.groups)
    assert fill_b is not None
    assert fill_r is not None
    if fill_b.params.interval is not None and fill_r.params.interval is not None:
        assert abs(fill_r.params.interval - fill_b.params.interval) < 1e-9


# ---------------------------------------------------------------------------
# 8. interpolate(a, a, 0.5) leaves params unchanged
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_interpolate_style_midpoint_when_same_style():
    a = extract_style(CHAMELEON)
    b = extract_style(CHAMELEON)
    result = interpolate_style(a, b, 0.5)
    fill_a = _find_any_fill(a.groups)
    fill_r = _find_any_fill(result.groups)
    assert fill_a is not None
    assert fill_r is not None
    # lerp(x, x, 0.5) == x for any x
    if fill_a.params.interval is not None and fill_r.params.interval is not None:
        assert abs(fill_r.params.interval - fill_a.params.interval) < 1e-9
    if fill_a.params.angle is not None and fill_r.params.angle is not None:
        assert abs(fill_r.params.angle - fill_a.params.angle) < 1e-9


# ---------------------------------------------------------------------------
# 9. Incompatible styles: interpolate returns first style values
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_interpolate_incompatible_returns_first():
    a = extract_style(CHAMELEON)
    b = extract_style(GIRL_LINEAR)
    result = interpolate_style(a, b, 0.5)
    # Result should mirror a's structure since they are incompatible
    assert len(result.groups) == len(a.groups)
    fill_a = _find_any_fill(a.groups)
    fill_r = _find_any_fill(result.groups)
    assert fill_a is not None
    assert fill_r is not None
    assert fill_r.params.fill_type == fill_a.params.fill_type


# ---------------------------------------------------------------------------
# 10. _lerp basic values
# ---------------------------------------------------------------------------


def test_lerp_basic_values():
    assert _lerp(0.0, 10.0, 0.5) == 5.0


def test_lerp_at_zero_returns_start():
    assert _lerp(3.0, 7.0, 0.0) == 3.0


def test_lerp_at_one_returns_end():
    assert _lerp(3.0, 7.0, 1.0) == 7.0


def test_lerp_negative_values():
    assert _lerp(-10.0, 10.0, 0.5) == 0.0


# ---------------------------------------------------------------------------
# 11. _lerp_color black to white midpoint is middle gray
# ---------------------------------------------------------------------------


def test_lerp_color_black_to_white():
    result = _lerp_color("#000000", "#ffffff", 0.5)
    assert result == "#7f7f7f" or result == "#808080", f"Unexpected midpoint gray: {result}"


def test_lerp_color_at_zero_returns_start():
    assert _lerp_color("#ff0000", "#0000ff", 0.0) == "#ff0000"


def test_lerp_color_at_one_returns_end():
    assert _lerp_color("#ff0000", "#0000ff", 1.0) == "#0000ff"


# ---------------------------------------------------------------------------
# 12. _lerp_color same color unchanged
# ---------------------------------------------------------------------------


def test_lerp_color_same_color():
    result = _lerp_color("#ff0000", "#ff0000", 0.5)
    assert result == "#ff0000"


def test_lerp_color_same_color_blue():
    result = _lerp_color("#0000ff", "#0000ff", 0.5)
    assert result == "#0000ff"


# ---------------------------------------------------------------------------
# 13. source_path is set after extract
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_style_source_path_is_set():
    style = extract_style(CHAMELEON)
    assert style.source_path is not None
    assert style.source_path.endswith("Chameleon.lines")
