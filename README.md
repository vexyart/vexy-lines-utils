---
this_file: README.md
---

# vexy-lines-utils

Python utilities for [Vexy Lines](https://vexy.art): parse `.lines` files, extract embedded images, apply `.lines` styles to images or video, control the app through MCP, and batch-export documents.

The parser and image-extraction commands work without the Vexy Lines app. MCP, style transfer, GUI rendering, and plist-driven export require the desktop app.

## Install

```bash
pip install vexy-lines-utils
```

Optional feature groups:

```bash
pip install "vexy-lines-utils[images]"  # Pillow image conversion
pip install "vexy-lines-utils[video]"   # video frame processing
pip install "vexy-lines-utils[gui]"     # CustomTkinter desktop app
pip install "vexy-lines-utils[all]"     # all optional runtime features
```

Requires Python 3.11 or newer. The parser is cross-platform; the legacy `export` command is macOS-only because it uses AppleScript and `defaults`.

## Quick Start

```bash
# Inspect a .lines file without opening the app
vexy-lines-utils info drawing.lines
vexy-lines-utils file-tree drawing.lines

# Extract embedded images without opening the app
vexy-lines-utils extract-source drawing.lines --output source.jpg
vexy-lines-utils extract-preview drawing.lines --output preview.png

# Apply a style through the app's MCP API
vexy-lines-utils style-transfer \
  --style look.lines \
  --input-dir ./photos \
  --output-dir ./styled \
  --format svg

# Launch the GUI
vexy-lines-utils gui
```

Running `vexy-lines-utils` without a subcommand launches the GUI when GUI dependencies are installed.

## CLI Reference

| Command | App needed | Purpose |
|---|---:|---|
| `info FILE` | No | Parse metadata, dimensions, object counts, and embedded image flags |
| `file-tree FILE` | No | Print the group/layer/fill tree from the `.lines` XML |
| `extract-source FILE` | No | Write the document source image to disk |
| `extract-preview FILE` | No | Write the embedded preview PNG to disk |
| `batch-convert` | No | Batch-extract previews or source images from `.lines` files |
| `style-transfer` | Yes | Apply one style, or interpolate two compatible styles, across images |
| `style-video` | Yes | Apply style parameters across video frames |
| `export INPUT` | Yes, macOS | Batch-export `.lines` files to PDF or SVG through plist injection |
| `gui` | Yes for processing | Launch the CustomTkinter desktop app |
| `mcp-status` | Yes | Check MCP connectivity |
| `tree` | Yes | Print the live document tree |
| `new-document` | Yes | Create a new document via MCP |
| `open FILE` | Yes | Open a document via MCP |
| `add-fill LAYER_ID TYPE` | Yes | Add a fill through MCP |
| `render` | Yes | Trigger a full render |

### Parser Commands

```bash
vexy-lines-utils info artwork.lines --json-output
vexy-lines-utils file-tree artwork.lines
vexy-lines-utils batch-convert --input-dir ./art --output-dir ./thumbs --what preview --format png
```

The parser recognizes Vexy Lines groups, layers, fills, masks, mesh data, source images, preview images, and per-fill image-filter chains.

### Style Transfer

```bash
# Single style
vexy-lines-utils style-transfer --style look.lines --input-dir ./frames --format svg

# Interpolate between two compatible styles across the image sequence
vexy-lines-utils style-transfer \
  --style start.lines \
  --end-style end.lines \
  --input-dir ./frames \
  --output-dir ./out \
  --format png
```

Style extraction preserves the group/layer/fill tree, numeric fill parameters, colors, masks, document properties, and matching image-filter chains. If two styles are structurally compatible, numeric values and colors are interpolated.

### Video

```bash
vexy-lines-utils style-video \
  --style start.lines \
  --end-style end.lines \
  --input clip.mp4 \
  --output styled.mp4
```

Install the `[video]` extra for video processing dependencies.

### Legacy Batch Export

```bash
vexy-lines-utils export ./art --format pdf --output ./pdf-out
vexy-lines-utils export ./art --format svg --dry-run
```

`export` uses the Vexy Lines macOS app, writes export preferences through `defaults`, triggers `File > Export` through AppleScript, then restores the previous preferences. Supported formats in this package are `pdf` and `svg`.

## Python API

```python
from vexy_lines_utils import (
    ExportConfig,
    MCPClient,
    VexyLinesExporter,
    apply_style,
    extract_source_image,
    extract_style,
    interpolate_style,
    parse_lines,
)

doc = parse_lines("drawing.lines")
extract_source_image("drawing.lines", "source.jpg")

style = extract_style("look.lines")
with MCPClient() as client:
    svg = apply_style(client, style, "photo.jpg")

config = ExportConfig(format="pdf")
stats = VexyLinesExporter(config).export("./art")
print(stats.human_summary())
```

## Architecture

| Module | Role |
|---|---|
| `parser.py` | `.lines` XML parser and embedded image extraction |
| `style.py` | Style extraction, compatibility checks, interpolation, and MCP application |
| `mcp/` | TCP JSON-RPC client for the Vexy Lines MCP server |
| `exporter.py` | macOS plist-driven PDF/SVG batch export |
| `core/` | Export config, stats, errors, and plist management |
| `automation/` | AppleScript bridge and window polling |
| `gui/` | CustomTkinter desktop workflow |
| `video.py` | Video probing, frame extraction, rasterization, and assembly helpers |
| `__main__.py` | Fire-based CLI |

## Development

```bash
uv sync
uvx hatch test
uvx hatch fmt
uvx hatch run lint:typing
```

Generated build outputs and caches are not source: remove `dist/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, and generated version files before packaging or release validation.

## License

MIT
