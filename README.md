---
this_file: README.md
---

# vexy-lines-utils

Batch-process Vexy Lines `.lines` vector art documents without the GUI. Parse files, extract styles, apply them to images or video, and export to PDF, SVG, PNG, JPG, MP4, or `.lines` format.

**Three quick examples:**

```bash
# Parse a .lines file and print its layer structure
vexy-lines-utils info drawing.lines

# Extract the source image from a .lines file
vexy-lines-utils extract-source style.lines --output style.jpg

# Apply one style to images, interpolating between two styles across frames
vexy-lines-utils style-transfer \
  --style start.lines \
  --end-style end.lines \
  --images img1.jpg img2.jpg img3.jpg \
  --output-dir ./out \
  --format png
```

---

## What Is Vexy Lines?

[Vexy Lines](https://www.vexy.art) is a macOS desktop application that transforms raster images into vector artwork. It reads pixel brightness and builds vector strokes: dark areas produce thick lines, bright areas thin ones (or the reverse).

Fourteen fill algorithms, each interpreting your image differently:

| Algorithm | What It Does |
|-----------|-------------|
| **Linear** | Parallel straight lines — copper-plate engravings |
| **Wave** | Flowing curves that undulate across the image |
| **Radial** | Lines exploding outward from a centre point |
| **Circular** | Concentric rings emanating from the centre |
| **Spiral** | Continuous winding from centre to edge |
| **Halftone** | Newspaper-style dots scaled by brightness |
| **Trace** | Edge detection — boundaries become paths |
| **Scribble** | Organic, hand-drawn randomness |
| **Fractal** | Recursive mathematical patterns |
| **Handmade** | Your own custom drawn strokes |
| **Wave** | Wavy line patterns |
| **Peano** | Space-filling curves |
| **Sigmoid** | S-curve adaptive fills |
| **Trace Area** | Fill interior regions from trace edges |

The app also has layers, groups, masks, dynamic colour, 3D mesh warping, multiple source images per composition, and overlap control for woven effects. Projects save as `.lines` files.

More at [vexy.art](https://www.vexy.art) and [help.vexy.art](https://help.vexy.art).

---

## System Requirements

| Requirement | Detail |
|-------------|--------|
| **OS** | macOS 10.14+ (Mojave or later) |
| **Application** | [Vexy Lines](https://www.vexy.art) installed (for MCP/export features) |
| **Python** | 3.10 or newer |
| **Accessibility** | Terminal needs accessibility permissions (for AppleScript export only). Parser and MCP commands do not require this. |

---

## Installation

### From PyPI

```bash
# Minimal: CLI tools, batch export, MCP API
pip install vexy-lines-utils

# With image support: source/preview extraction, style transfer
pip install vexy-lines-utils[images]

# With GUI: CustomTkinter desktop app
pip install vexy-lines-utils[gui]

# With video: frame-by-frame style transfer
pip install vexy-lines-utils[video]

# Everything
pip install vexy-lines-utils[all]
```

### From Source

```bash
git clone https://github.com/vexyart/vexy-lines-utils.git
cd vexy-lines-utils
uv sync
uvx hatch test
```

### Accessibility Permissions (Export Only)

The batch exporter drives Vexy Lines through AppleScript and needs accessibility access. Parser, MCP, and style-transfer commands skip this entirely.

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Add your terminal (Terminal.app, iTerm2, VS Code, etc.)
3. Restart the terminal

---

## v4.0 Features

### Parse .lines Files

No app required. Read the XML structure, extract metadata, images, and layer trees programmatically.

```python
from vexy_lines_utils.parser import parse, extract_source_image

# Parse file
doc = parse("drawing.lines")
print(f"Caption: {doc.caption}, DPI: {doc.dpi}, Size: {doc.props.width_mm}x{doc.props.height_mm}mm")

# Walk the layer tree
for group in doc.groups:
    print(f"Group: {group.caption}")
    for layer in group.children:
        if hasattr(layer, 'fills'):
            for fill in layer.fills:
                print(f"  Layer: {layer.caption}, Fill: {fill.params.fill_type}")

# Extract source image
extract_source_image("drawing.lines", "source.jpg")
```

**CLI:**

```bash
# Print metadata
vexy-lines-utils info drawing.lines
vexy-lines-utils info drawing.lines --json

# Print layer tree
vexy-lines-utils file-tree drawing.lines

# Extract embedded images
vexy-lines-utils extract-source drawing.lines --output source.jpg
vexy-lines-utils extract-preview drawing.lines --output preview.png
```

### Extract & Apply Styles

A "style" is the group→layer→fill structure from a `.lines` file. Extract it and apply to images via the Vexy Lines MCP API.

```python
from vexy_lines_utils.mcp import MCPClient
from vexy_lines_utils.style import extract_style, apply_style

# Extract style from a .lines file
style = extract_style("artistic_style.lines")

# Apply to an image
with MCPClient() as client:
    svg_result = apply_style(client, style, "photo.jpg")
    # SVG contains the styled rendering
```

**CLI:**

```bash
# Apply style to images
vexy-lines-utils style-transfer \
  --style artistic.lines \
  --images photo1.jpg photo2.jpg \
  --output-dir ./styled \
  --format svg
```

### Interpolate Between Two Styles

Smoothly blend numeric parameters between two compatible styles across a sequence of images or video frames.

```python
from vexy_lines_utils.style import extract_style, interpolate_style, apply_style

style_a = extract_style("style_a.lines")
style_b = extract_style("style_b.lines")

# Interpolate at t=0.5 (halfway between styles)
blended = interpolate_style(style_a, style_b, t=0.5)

# Apply blended style
with MCPClient() as client:
    svg = apply_style(client, blended, "photo.jpg")
```

**CLI:** Apply two styles to a sequence of images, automatically interpolating:

```bash
vexy-lines-utils style-transfer \
  --style start.lines \
  --end-style end.lines \
  --images frame_1.jpg frame_2.jpg frame_3.jpg \
  --output-dir ./frames \
  --format png

# Produces: frame_1_styled.png (100% start), frame_2_styled.png (50/50 blend), frame_3_styled.png (100% end)
```

### Video Frame-by-Frame Style Transfer

Process video one frame at a time, optionally interpolating between two styles.

```bash
# Apply single style to every frame
vexy-lines-utils style-video \
  --style sketch.lines \
  --input video.mp4 \
  --output styled.mp4

# Interpolate between two styles across all frames
vexy-lines-utils style-video \
  --style start.lines \
  --end-style end.lines \
  --input video.mp4 \
  --output styled.mp4 \
  --start-frame 1 \
  --end-frame 100
```

### Desktop GUI

Launch a drag-and-drop desktop app with three input modes: Lines files, Images, or Video.

```bash
# Launch the GUI
vexy-lines-utils gui

# Or use the dedicated entry point
vexy-lines-gui
```

**Features:**

- **Lines tab:** Drop `.lines` files to process directly. Style section disabled.
- **Images tab:** Drop images and pick a style to apply. Optionally pick a second style for interpolation.
- **Video tab:** Drop a video file with optional frame range. Apply single or blended style.
- **Output formats:** SVG, PNG, JPG, MP4, LINES (via MCP).
- **Drag-and-drop:** Works on all tab areas and respects the active tab's file type.
- **Menu integration:** File > Add Lines, Image > Add Images, Video > Add Video for quick tab switching.

### Batch Convert

Export all `.lines` files in a folder to SVG, PDF, PNG, or JPG without style transfer.

```bash
vexy-lines-utils batch-convert \
  --input-dir ./lines-collection \
  --output-dir ./exports \
  --format svg
```

---

## v3.0 & v2.0 Features

### Batch Export (v2.0)

Export `.lines` documents to PDF or SVG via plist injection and AppleScript. The workhorse for production pipelines.

```bash
vexy-lines-utils export INPUT [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `input` | path | *(required)* | A `.lines` file or directory (searched recursively) |
| `--output` | path | same as input | Output directory or file path |
| `--format` | string | `pdf` | Export format: `pdf` or `svg` |
| `--verbose` | flag | off | Show detailed progress |
| `--dry_run` | flag | off | List files without touching anything |
| `--force` | flag | off | Overwrite existing exports |
| `--say_summary` | flag | off | Announce completion via macOS text-to-speech |
| `--timeout_multiplier` | float | `1.0` | Scale all timeouts (0.1–10.0). Increase for slow machines. |
| `--max_retries` | int | `3` | Retry count per file (0–10) |

**Examples:**

```bash
# Single file to PDF
vexy-lines-utils export ~/Art/portrait.lines

# Entire folder to SVG with verbose output
vexy-lines-utils export ~/Projects/posters --format svg --verbose

# Dry run — see what would be processed
vexy-lines-utils export ~/Archive/2024 --dry_run --verbose

# Export to a specific directory, overwriting existing files
vexy-lines-utils export ~/Art/batch --output ~/Exports --force

# Slow machine — double all timeouts
vexy-lines-utils export ~/Art/heavy.lines --timeout_multiplier 2.0

# Voice announcement when a large batch finishes
vexy-lines-utils export ~/Projects --say_summary
```

**Exit behaviour:** the exporter continues past individual failures. On completion it returns a summary.

### MCP Client (v3.0)

Connect to the Vexy Lines embedded MCP server (`localhost:47384`) for programmatic document creation and manipulation.

```python
from vexy_lines_utils.mcp import MCPClient

with MCPClient() as client:
    # Create document
    result = client.new_document(width_px=800, height_px=600)
    doc_id = result.document_id

    # Add layers and fills
    client.add_fill(
        document_id=doc_id,
        fill_type="linear",
        color="#FF0000FF",
        interval=2.5,
        angle=45.0
    )

    # Render and export
    status = client.render_all(doc_id)
    client.export_document(doc_id, format="SVG", output_path="result.svg")
```

**25 MCP tools available:** document ops, layer structure, fill parameters, masks, transforms, and rendering. See `src/vexy_lines_utils/mcp/client.py` for the full API.

---

## Complete CLI Reference

All subcommands support `--verbose` for debug logging.

| Subcommand | Purpose |
|------------|---------|
| `export INPUT` | Batch-export `.lines` to PDF/SVG via AppleScript |
| `info FILE` | Print `.lines` metadata (caption, DPI, size, layer count) |
| `file-tree FILE` | Print layer tree from `.lines` file |
| `extract-source FILE` | Extract JPEG source image from `.lines` file |
| `extract-preview FILE` | Extract PNG preview image from `.lines` file |
| `style-transfer` | Apply style to images with optional interpolation |
| `style-video` | Apply style to video frames with optional interpolation |
| `batch-convert` | Batch-extract images from `.lines` files |
| `gui` | Launch CustomTkinter desktop GUI |
| `mcp_status` | Check if Vexy Lines MCP server is running |
| `tree DOCUMENT_ID` | Print layer tree from open document via MCP |
| `new_document` | Create new document via MCP |
| `open DOCUMENT_PATH` | Open document via MCP |
| `add_fill` | Add fill to layer via MCP |
| `render DOCUMENT_ID` | Trigger render via MCP |

---

## Python API

### Parser Module

```python
from vexy_lines_utils.parser import (
    parse,                    # Parse .lines file → LinesDocument
    extract_source_image,     # Extract JPEG from .lines
    extract_preview_image,    # Extract PNG from .lines
    LinesDocument,            # Full parsed document
    DocumentProps,            # Document-level properties
    GroupInfo,                # Group (container)
    LayerInfo,                # Layer (drawable)
    FillNode,                 # Single fill effect
    FillParams,               # Numeric + color params
    MaskInfo,                 # Layer mask info
    FILL_TAG_MAP,             # XML tag → fill type mapping
    NUMERIC_PARAMS,           # Interpolatable param names
)
```

**Key types:**

```python
@dataclass
class LinesDocument:
    caption: str
    version: str
    dpi: int
    props: DocumentProps
    groups: list[GroupInfo]
    source_image: bytes | None  # Raw JPEG bytes
    preview_image: bytes | None # Raw PNG bytes

@dataclass
class FillParams:
    fill_type: str             # "linear", "circular", "trace", etc.
    color: str                 # "#RRGGBBAA"
    interval: float            # Line spacing
    angle: float               # Stroke angle (degrees)
    thickness: float           # Stroke thickness
    smoothness: float
    uplimit: float             # Brightness upper limit (0–255)
    downlimit: float           # Brightness lower limit (0–255)
    multiplier: float          # Size multiplier
    base_width: float
    dispersion: float          # Random offset
    shear: float               # Shear distortion
    raw: dict[str, str]        # All XML attributes preserved
```

### Style Module

```python
from vexy_lines_utils.style import (
    extract_style,            # .lines → Style
    styles_compatible,        # Check if two styles can interpolate
    interpolate_style,        # Blend two styles at t ∈ [0, 1]
    apply_style,              # Style + image → SVG via MCP
    Style,                    # Style dataclass
)
```

**Key functions:**

```python
def extract_style(path: str | Path) -> Style:
    """Parse .lines file and extract style structure."""

def styles_compatible(a: Style, b: Style) -> bool:
    """True if styles have matching group/layer/fill tree."""

def interpolate_style(a: Style, b: Style, t: float) -> Style:
    """Blend all numeric FillParams: result = a + (b - a) * t.
    String params (color) use step-function: a if t < 0.5 else b.
    Hex colors lerp as RGB.
    """

async def apply_style(client: MCPClient, style: Style, source_image: str | Path) -> str:
    """Create document via MCP, replicate structure, set all fill params,
    render, and export as SVG. Returns SVG string."""
```

### MCP Client Module

```python
from vexy_lines_utils.mcp import MCPClient, MCPError

with MCPClient(host="localhost", port=47384) as client:
    # Document ops
    doc_info = client.get_document_info(doc_id)
    new_doc = client.new_document(width_px=800, height_px=600)
    client.open_document("path/to/file.lines")
    client.save_document(doc_id, "output.lines")
    client.export_document(doc_id, format="SVG", output_path="out.svg")

    # Layer tree
    tree = client.get_layer_tree(doc_id)

    # Fills (14 types: linear, circular, trace, spiral, wave, radial, halftone, scribble, fractals, handmade, peano, sigmoid, trace_area, source_strokes)
    client.add_fill(doc_id, fill_type="linear", color="#FF0000FF", interval=2.5, angle=45.0)
    params = client.get_fill_params(doc_id, fill_id)
    client.set_fill_params(doc_id, fill_id, interval=3.0, angle=90.0)

    # Rendering
    status = client.render_all(doc_id)
    is_done = client.get_render_status(doc_id)

    # Undo/redo
    client.undo(doc_id)
    client.redo(doc_id)
```

### Batch Export API

For scripting batch exports without the CLI:

```python
from pathlib import Path
from vexy_lines_utils import ExportConfig, VexyLinesExporter

config = ExportConfig(
    format="pdf",              # "pdf" or "svg"
    poll_interval=0.2,         # window-check frequency (seconds)
    wait_for_app=20.0,         # app launch timeout
    wait_for_file=20.0,        # file open timeout
    post_action_delay=0.4,     # pause after UI actions
    timeout_multiplier=1.0,    # scale all timeouts
    max_retries=3,             # export attempts per file
)

exporter = VexyLinesExporter(config=config, dry_run=False, force=True)
stats = exporter.export(
    input_path=Path("~/Documents/vexy-projects"),
    output_path=Path("~/Exports"),
)

print(stats.human_summary())
print(f"Success rate: {stats.success}/{stats.processed}")

for path, reason in stats.failures:
    print(f"  Failed: {path} — {reason}")
```

---

## Examples

Working examples are in the `examples/` folder:

- `parse_lines.py` — Parse a .lines file and print structure
- `extract_images.py` — Extract source and preview images
- `style_transfer.py` — Apply one style to an image
- `style_interpolation.py` — Interpolate between two styles
- `batch_export.py` — Batch-export via CLI
- `mcp_hello.py` — Connect via MCP and inspect documents
- `mcp_create_artwork.py` — Create artwork from scratch via MCP

Run any example:

```bash
cd examples
python parse_lines.py ../drawing.lines
```

---

## Troubleshooting

**"Parser fails on .lines file":** Ensure the file is valid XML. Use `file-tree` subcommand to diagnose.

**"MCP server not running":** Launch Vexy Lines app first. The embedded MCP server runs on `localhost:47384`.

**"Style transfer produces blank output":** Check that the source image path is correct and that the Vexy Lines app is running with MCP enabled.

**"GUI won't launch":** Ensure `customtkinter` is installed. Try `pip install vexy-lines-utils[gui]`.

**"Export fails with permission error":** Check System Settings > Privacy & Security > Accessibility. Terminal needs to be listed there.

---

## Development

```bash
# Setup
uv venv --python 3.12 --clear
uv sync

# Tests (170+ tests)
uvx hatch test

# Lint + format
uvx hatch fmt

# Type check
uvx hatch run lint:typing

# Full pipeline (autoflake, pyupgrade, ruff, tests)
fd -e py -x uvx autoflake -i {}; fd -e py -x uvx pyupgrade --py312-plus {}; fd -e py -x uvx ruff check --output-format=github --fix --unsafe-fixes {}; fd -e py -x uvx ruff format --respect-gitignore --target-version py312 {}; uvx hatch test;
```

---

## Architecture

**Core modules:**

- `parser.py` — Parse `.lines` XML → typed dataclasses (v4.0)
- `style.py` — Extract, apply, interpolate styles (v4.0)
- `gui/` — CustomTkinter desktop app (v4.0)
- `mcp/` — Vexy Lines MCP client (v3.0)
- `exporter.py` — Batch export pipeline (v2.0)
- `core/` — Config, errors, stats, plist manager
- `automation/` — AppleScript bridges and window watching

**Five-stage export pipeline:**

```
Discovery → Plist Injection → App Activation → Per-File Export Loop → Cleanup
```

For details, see `CLAUDE.md` in the repository.

---

## License

See LICENSE file.
