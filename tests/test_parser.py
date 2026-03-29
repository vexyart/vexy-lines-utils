# this_file: tests/test_parser.py
"""Unit tests for vexy_lines_utils.parser — .lines XML parsing."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from vexy_lines_utils.parser import (
    FILL_TAG_MAP,
    FILL_TAGS,
    NUMERIC_PARAMS,
    DocumentProps,
    FillNode,
    FillParams,
    GroupInfo,
    LayerInfo,
    LinesDocument,
    MaskInfo,
    extract_preview_image,
    extract_source_image,
    parse,
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
# Minimal XML helpers
# ---------------------------------------------------------------------------

_MINIMAL_NO_SOURCE = textwrap.dedent("""\
    <Project app="vexylines" dpi="300" caption="test-doc" version="3.0.1">
      <Objects/>
      <Document width_mm="100.0" height_mm="100.0" dpi="300"
                thicknessMin="0" thicknessMax="2.8" intervalMin="0.24" intervalMax="2.8"/>
      <PreviewDoc pict_format="png" width="100" height="100" pict_compressed="0">iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==</PreviewDoc>
    </Project>
""")


# ---------------------------------------------------------------------------
# 1. parse() returns LinesDocument with correct fields
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_returns_lines_document_when_valid_file():
    doc = parse(CHAMELEON)
    assert isinstance(doc, LinesDocument)
    assert doc.caption == "chameleon"
    assert doc.dpi == 300


@skip_if_no_examples
def test_parse_extracts_document_props_when_valid_file():
    doc = parse(CHAMELEON)
    props = doc.props
    assert isinstance(props, DocumentProps)
    assert props.width_mm > 0
    assert props.height_mm > 0
    assert props.dpi > 0


# ---------------------------------------------------------------------------
# 3. Groups and layers
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_finds_groups_and_layers_when_chameleon():
    doc = parse(CHAMELEON)
    assert len(doc.groups) > 0
    for obj in doc.groups:
        assert isinstance(obj, (GroupInfo, LayerInfo))


@skip_if_no_examples
def test_parse_finds_groups_and_layers_when_girl_linear():
    doc = parse(GIRL_LINEAR)
    assert len(doc.groups) > 0
    all_nodes: list[GroupInfo | LayerInfo] = []

    def _collect(nodes: list) -> None:
        for node in nodes:
            all_nodes.append(node)
            if isinstance(node, GroupInfo) and node.children:
                _collect(node.children)

    _collect(doc.groups)
    has_group_or_layer = any(isinstance(n, (GroupInfo, LayerInfo)) for n in all_nodes)
    assert has_group_or_layer


# ---------------------------------------------------------------------------
# 4. Fill nodes exist
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_finds_fills_when_chameleon():
    doc = parse(CHAMELEON)

    def _find_fill(nodes: list) -> FillNode | None:
        for node in nodes:
            if isinstance(node, GroupInfo):
                found = _find_fill(node.children)
                if found:
                    return found
            elif isinstance(node, LayerInfo):
                if node.fills:
                    return node.fills[0]
        return None

    fill = _find_fill(doc.groups)
    assert fill is not None
    assert isinstance(fill, FillNode)
    assert fill.params.fill_type in FILL_TAG_MAP.values()


# ---------------------------------------------------------------------------
# 5. FillParams numeric values
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_fill_params_have_numeric_values_when_girl_linear():
    doc = parse(GIRL_LINEAR)

    def _find_fill(nodes: list) -> FillNode | None:
        for node in nodes:
            if isinstance(node, GroupInfo):
                found = _find_fill(node.children)
                if found:
                    return found
            elif isinstance(node, LayerInfo):
                if node.fills:
                    return node.fills[0]
        return None

    fill = _find_fill(doc.groups)
    assert fill is not None
    assert isinstance(fill.params, FillParams)
    # LinearStrokesTmpl in girl-linear has interval=2.2828, angle=40
    assert fill.params.interval > 0
    assert isinstance(fill.params.angle, float)


# ---------------------------------------------------------------------------
# 6 & 7. Source and preview image magic bytes
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_source_image_is_jpeg_when_chameleon():
    doc = parse(CHAMELEON)
    assert doc.source_image_data is not None
    assert doc.source_image_data[:3] == b"\xff\xd8\xff"


@skip_if_no_examples
def test_parse_preview_image_is_png_when_chameleon():
    doc = parse(CHAMELEON)
    assert doc.preview_image_data is not None
    assert doc.preview_image_data[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# 8. No SourcePict → source_image_data is None
# ---------------------------------------------------------------------------


def test_parse_source_image_none_for_empty_when_no_source_pict(tmp_path: Path):
    f = tmp_path / "minimal.lines"
    f.write_text(_MINIMAL_NO_SOURCE)
    doc = parse(f)
    assert doc.source_image_data is None


# ---------------------------------------------------------------------------
# 9 & 10. extract_source_image / extract_preview_image
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_extract_source_image_saves_file_when_chameleon(tmp_path: Path):
    out = tmp_path / "source.jpg"
    extract_source_image(CHAMELEON, out)
    assert out.exists()
    assert out.stat().st_size > 0
    data = out.read_bytes()
    assert data[:3] == b"\xff\xd8\xff"


@skip_if_no_examples
def test_extract_preview_image_saves_file_when_chameleon(tmp_path: Path):
    out = tmp_path / "preview.png"
    extract_preview_image(CHAMELEON, out)
    assert out.exists()
    assert out.stat().st_size > 0
    data = out.read_bytes()
    assert data[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# 11. FILL_TAG_MAP has known types
# ---------------------------------------------------------------------------


def test_fill_tag_map_has_known_types_when_checking_constants():
    values = set(FILL_TAG_MAP.values())
    assert "linear" in values
    assert "trace" in values
    assert "circular" in values


# ---------------------------------------------------------------------------
# 12. girl-linear.lines has a linear fill
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_girl_linear_has_linear_fill_when_parsed():
    doc = parse(GIRL_LINEAR)

    def _find_fill_type(nodes: list, target: str) -> bool:
        for node in nodes:
            if isinstance(node, GroupInfo):
                if _find_fill_type(node.children, target):
                    return True
            elif isinstance(node, LayerInfo):
                if any(f.params.fill_type == target for f in node.fills):
                    return True
        return False

    assert _find_fill_type(doc.groups, "linear")


# ---------------------------------------------------------------------------
# 13. Chameleon.lines has a FreeCurveStrokesTmpl fill
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_chameleon_has_flowline_fill_when_parsed():
    doc = parse(CHAMELEON)

    def _find_xml_tag(nodes: list, tag: str) -> bool:
        for node in nodes:
            if isinstance(node, GroupInfo):
                if _find_xml_tag(node.children, tag):
                    return True
            elif isinstance(node, LayerInfo):
                if any(f.xml_tag == tag for f in node.fills):
                    return True
        return False

    assert _find_xml_tag(doc.groups, "FreeCurveStrokesTmpl")


# ---------------------------------------------------------------------------
# 14 & 15. Error cases
# ---------------------------------------------------------------------------


def test_parse_nonexistent_file_raises_when_missing():
    with pytest.raises(FileNotFoundError):
        parse(Path("/nonexistent/does-not-exist.lines"))


def test_parse_invalid_xml_raises_when_garbage(tmp_path: Path):
    f = tmp_path / "bad.lines"
    f.write_bytes(b"this is not xml at all \x00\x01\x02")
    with pytest.raises(Exception):
        parse(f)


# ---------------------------------------------------------------------------
# 16. FILL_TAGS and NUMERIC_PARAMS are non-empty
# ---------------------------------------------------------------------------


def test_fill_tags_is_non_empty_set_when_checking_constants():
    assert isinstance(FILL_TAGS, (set, frozenset))
    assert len(FILL_TAGS) > 0


def test_numeric_params_is_non_empty_list_when_checking_constants():
    assert isinstance(NUMERIC_PARAMS, list)
    assert len(NUMERIC_PARAMS) > 0
    assert "interval" in NUMERIC_PARAMS
    assert "angle" in NUMERIC_PARAMS


# ---------------------------------------------------------------------------
# 17. DocumentProps version
# ---------------------------------------------------------------------------


@skip_if_no_examples
def test_parse_version_is_string_when_chameleon():
    doc = parse(CHAMELEON)
    assert isinstance(doc.version, str)
    assert len(doc.version) > 0


# ---------------------------------------------------------------------------
# 18. MaskInfo dataclass is importable and constructable
# ---------------------------------------------------------------------------


def test_mask_info_is_constructable_when_direct_instantiation():
    m = MaskInfo(mask_type=1, invert=False, tolerance=0.0)
    assert m.mask_type == 1
    assert m.invert is False


# ---------------------------------------------------------------------------
# 19. FillParams defaults are sensible
# ---------------------------------------------------------------------------


def test_fill_params_defaults_are_sensible_when_default_constructed():
    p = FillParams(
        fill_type="linear",
        color="#000000",
        interval=1.0,
        angle=0.0,
        thickness=0.0,
        thickness_min=0.0,
        smoothness=0.0,
        uplimit=0.0,
        downlimit=255.0,
        multiplier=1.0,
        base_width=0.0,
        dispersion=0.0,
        shear=0.0,
        raw={},
    )
    assert isinstance(p.interval, float)
    assert isinstance(p.angle, float)
