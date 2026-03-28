#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/mcp/types.py
"""Typed response dataclasses for MCP tool results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentInfo:
    """Document metadata returned by get_document_info."""

    width_mm: float
    height_mm: float
    resolution: float
    units: str
    has_changes: bool


@dataclass
class LayerNode:
    """Recursive tree node representing a document/group/layer/fill.

    Used by get_layer_tree to return the full document structure.
    """

    id: int
    type: str  # "document", "group", "layer", "fill"
    caption: str
    visible: bool
    fill_type: str | None = None  # only present for type=="fill"
    children: list[LayerNode] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> LayerNode:
        """Build a LayerNode tree from a nested dict."""
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(
            id=d["id"],
            type=d["type"],
            caption=d.get("caption", ""),
            visible=d.get("visible", True),
            fill_type=d.get("fill_type"),
            children=children,
        )


@dataclass
class NewDocumentResult:
    """Result of creating a new document."""

    status: str
    width: float
    height: float
    dpi: float
    root_id: int


@dataclass
class RenderStatus:
    """Current render state."""

    rendering: bool
