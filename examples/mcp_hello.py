#!/usr/bin/env -S uv run
# /// script
# dependencies = ["vexy-lines-utils", "fire"]
# ///
# this_file: examples/mcp_hello.py
"""Connect to Vexy Lines MCP server and print document info.

Requires Vexy Lines to be running with a document open.

Usage:
    python mcp_hello.py
    python mcp_hello.py --port 47384
"""

import fire

from vexy_lines_utils.mcp import MCPClient, MCPError
from vexy_lines_utils.mcp.types import LayerNode


def _print_tree(node: LayerNode, indent: int = 0) -> None:
    """Recursively print the layer tree."""
    "  " * indent
    label = f"{node.type}: {node.caption} (id={node.id})"
    if node.fill_type:
        label += f" [{node.fill_type}]"
    if not node.visible:
        label += " [hidden]"
    for child in node.children:
        _print_tree(child, indent + 1)


def hello(*, host: str = "127.0.0.1", port: int = 47384) -> None:
    """Connect to Vexy Lines and print document info and layer tree."""
    try:
        with MCPClient(host=host, port=port) as vl:
            vl.get_document_info()
            tree = vl.get_layer_tree()
            _print_tree(tree)
    except MCPError:
        pass


if __name__ == "__main__":
    fire.Fire(hello)
