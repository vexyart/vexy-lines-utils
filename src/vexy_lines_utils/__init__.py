#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/__init__.py
"""vexy-lines-utils: batch export, MCP client, and style engine for Vexy Lines.

Five capabilities in one package:

1. **Batch export** — inject settings into macOS prefs, trigger ``File > Export``
   via AppleScript, and collect PDF/SVG output without touching any dialog.
   Pipeline: Discovery → Plist Injection → App Activation → Export Loop → Cleanup.

2. **MCP client** — TCP JSON-RPC 2.0 client for the server embedded in the
   Vexy Lines app (``localhost:47384``). 29 tools across 5 groups: Document,
   Structure, Fill Params, Visual, Control.

3. **Parser** — read ``.lines`` XML files and walk the group→layer→fill tree
   without launching the app. Works on any platform.

4. **Style engine** — extract a fill structure from a ``.lines`` file, apply it
   to any source image, or interpolate between two styles at an arbitrary ratio.

5. **GUI / CLI** — CustomTkinter desktop app and ``fire``-based CLI exposing all
   of the above as commands.

Quick export example::

    from vexy_lines_utils import VexyLinesExporter, ExportConfig

    config = ExportConfig(format="pdf")
    exporter = VexyLinesExporter(config)
    stats = exporter.export("./art/")
    print(stats.summary())
"""

from __future__ import annotations

from vexy_lines_utils.__main__ import VexyLinesCLI, main
from vexy_lines_utils.__version__ import __version__
from vexy_lines_utils.automation.bridges import AppleScriptBridge, ApplicationBridge
from vexy_lines_utils.automation.window_watcher import WindowWatcher
from vexy_lines_utils.core.config import ExportConfig
from vexy_lines_utils.core.errors import AutomationError, FileValidationError
from vexy_lines_utils.core.plist import PlistManager
from vexy_lines_utils.core.stats import ExportStats
from vexy_lines_utils.exporter import VexyLinesExporter
from vexy_lines_utils.mcp.client import MCPClient, MCPError
from vexy_lines_utils.parser import (
    extract_preview_image,
    extract_source_image,
)
from vexy_lines_utils.parser import (
    parse as parse_lines,
)
from vexy_lines_utils.style import (
    Style,
    apply_style,
    extract_style,
    interpolate_style,
    styles_compatible,
)
from vexy_lines_utils.utils.file_utils import find_lines_files, validate_lines_file, validate_pdf, validate_svg
from vexy_lines_utils.utils.interrupt import InterruptHandler
from vexy_lines_utils.utils.system import speak

__all__ = [
    "AppleScriptBridge",
    "ApplicationBridge",
    "AutomationError",
    "ExportConfig",
    "ExportStats",
    "FileValidationError",
    "InterruptHandler",
    "MCPClient",
    "MCPError",
    "PlistManager",
    "Style",
    "VexyLinesCLI",
    "VexyLinesExporter",
    "WindowWatcher",
    "__version__",
    "apply_style",
    "extract_preview_image",
    "extract_source_image",
    "extract_style",
    "find_lines_files",
    "interpolate_style",
    "main",
    "parse_lines",
    "speak",
    "styles_compatible",
    "validate_lines_file",
    "validate_pdf",
    "validate_svg",
]
