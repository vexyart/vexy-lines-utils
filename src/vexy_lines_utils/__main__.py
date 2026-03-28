#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/__main__.py
"""Command-line interface for Vexy Lines utils."""

from __future__ import annotations

import json as _json
from dataclasses import asdict
from pathlib import Path

import fire
from loguru import logger

from vexy_lines_utils.core.config import ExportConfig
from vexy_lines_utils.exporter import VexyLinesExporter
from vexy_lines_utils.mcp import MCPClient, MCPError
from vexy_lines_utils.mcp.types import LayerNode
from vexy_lines_utils.utils.system import speak


def _format_tree(node: LayerNode, indent: int = 0) -> str:
    """Recursively format a LayerNode tree with indentation.

    Each node is rendered as:
        {indent}{type}: {caption} (id={id})
    Fills append [{fill_type}].  Hidden nodes append [hidden].
    """
    prefix = "  " * indent
    line = f"{prefix}{node.type}: {node.caption} (id={node.id})"
    if node.fill_type:
        line += f" [{node.fill_type}]"
    if not node.visible:
        line += " [hidden]"
    lines = [line]
    for child in node.children:
        lines.append(_format_tree(child, indent + 1))
    return "\n".join(lines)


class VexyLinesCLI:
    """Fire CLI surface."""

    MIN_TIMEOUT_MULTIPLIER = 0.1
    MAX_TIMEOUT_MULTIPLIER = 10
    MAX_RETRY_LIMIT = 10

    def export(
        self,
        input: str,  # noqa: A002
        *,
        output: str | None = None,
        format: str = "pdf",  # noqa: A002
        verbose: bool = False,
        dry_run: bool = False,
        force: bool = False,
        say_summary: bool = False,
        timeout_multiplier: float = 1.0,
        max_retries: int = 3,
    ) -> dict[str, object]:
        """Export .lines documents to PDF or SVG.

        Uses dialog-less export via plist configuration: quits the app, sets
        export preferences, launches the app, opens each file, triggers the
        File > Export menu item, then restores original preferences on exit.

        Args:
            input: Path to a .lines file or directory to search for .lines files.
            output: Destination file (when input is a file) or directory (when
                input is a directory).  Defaults to the same folder as each
                input file.
            format: Export format — 'pdf' (default) or 'svg'.
            verbose: Show detailed progress messages.
            dry_run: Preview files that would be processed without exporting.
            force: Re-export even if the output file already exists.
            say_summary: Announce completion via text-to-speech.
            timeout_multiplier: Scale all timeouts (2.0 = double all timeouts).
            max_retries: Maximum retry attempts for transient failures (0-10).
        """
        if verbose:
            logger.enable("vexy_lines_utils")

        if timeout_multiplier < self.MIN_TIMEOUT_MULTIPLIER or timeout_multiplier > self.MAX_TIMEOUT_MULTIPLIER:
            msg = f"timeout_multiplier must be between {self.MIN_TIMEOUT_MULTIPLIER} and {self.MAX_TIMEOUT_MULTIPLIER}"
            raise ValueError(msg)
        if max_retries < 0 or max_retries > self.MAX_RETRY_LIMIT:
            msg = f"max_retries must be between 0 and {self.MAX_RETRY_LIMIT}"
            raise ValueError(msg)

        config = ExportConfig(
            format=format,
            timeout_multiplier=timeout_multiplier,
            max_retries=max_retries,
        )
        exporter = VexyLinesExporter(config, dry_run=dry_run, force=force)
        stats = exporter.export(
            Path(input),
            Path(output) if output else None,
        )

        if say_summary:
            speak(stats.human_summary())

        return stats.as_dict()

    # -- MCP subcommands --------------------------------------------------

    def mcp_status(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 47384,
    ) -> dict[str, object]:
        """Check if the MCP server is reachable.

        Args:
            host: Server address.
            port: Server port.
        """
        try:
            with MCPClient(host=host, port=port) as client:
                info = client.get_document_info()
            print(f"MCP server at {host}:{port} is reachable.")
            return {"status": "ok", "server_info": asdict(info)}
        except MCPError as exc:
            print(f"MCP server unreachable: {exc}")
            return {"error": str(exc)}

    def tree(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 47384,
        json_output: bool = False,
    ) -> dict[str, object] | str:
        """Print the layer tree of the current document.

        Args:
            host: Server address.
            port: Server port.
            json_output: Output the tree as JSON instead of indented text.
        """
        try:
            with MCPClient(host=host, port=port) as client:
                root = client.get_layer_tree()
        except MCPError as exc:
            print(f"Error: {exc}")
            return {"error": str(exc)}

        if json_output:
            text = _json.dumps(asdict(root), indent=2)
            print(text)
            return text

        text = _format_tree(root)
        print(text)
        return text

    def new_document(
        self,
        *,
        width: float | None = None,
        height: float | None = None,
        dpi: float = 300,
        source_image: str | None = None,
        host: str = "127.0.0.1",
        port: int = 47384,
    ) -> dict[str, object]:
        """Create a new document via MCP.

        Args:
            width: Document width in mm.
            height: Document height in mm.
            dpi: Resolution (default 300).
            source_image: Optional path to a source image.
            host: Server address.
            port: Server port.
        """
        try:
            with MCPClient(host=host, port=port) as client:
                result = client.new_document(
                    width=width,
                    height=height,
                    dpi=dpi,
                    source_image=source_image,
                )
            return asdict(result)
        except MCPError as exc:
            print(f"Error: {exc}")
            return {"error": str(exc)}

    def open(
        self,
        input: str,  # noqa: A002
        *,
        host: str = "127.0.0.1",
        port: int = 47384,
    ) -> dict[str, object]:
        """Open a .lines file via MCP.

        Args:
            input: Path to the .lines file.
            host: Server address.
            port: Server port.
        """
        try:
            with MCPClient(host=host, port=port) as client:
                result = client.open_document(input)
            print(result)
            return {"status": "ok", "result": result}
        except MCPError as exc:
            print(f"Error: {exc}")
            return {"error": str(exc)}

    def add_fill(
        self,
        layer_id: int,
        fill_type: str,
        *,
        color: str | None = None,
        host: str = "127.0.0.1",
        port: int = 47384,
    ) -> dict[str, object]:
        """Add a fill to a layer.

        Args:
            layer_id: Target layer ID.
            fill_type: Fill type (e.g. 'solid', 'gradient').
            color: Optional colour value.
            host: Server address.
            port: Server port.
        """
        try:
            with MCPClient(host=host, port=port) as client:
                result = client.add_fill(
                    layer_id=layer_id,
                    fill_type=fill_type,
                    color=color,
                )
            return result
        except MCPError as exc:
            print(f"Error: {exc}")
            return {"error": str(exc)}

    def render(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 47384,
    ) -> dict[str, object]:
        """Trigger a full render of the current document.

        Args:
            host: Server address.
            port: Server port.
        """
        try:
            with MCPClient(host=host, port=port) as client:
                result = client.render_all()
            print(result)
            return {"status": "ok", "result": result}
        except MCPError as exc:
            print(f"Error: {exc}")
            return {"error": str(exc)}


def main() -> None:
    fire.Fire(VexyLinesCLI)


if __name__ == "__main__":
    main()
