---
this_file: README.md
---

# Vexy Lines Utils

Turn photos into vector art from the command line. No pointing, no clicking.

```bash
# Export a portrait to PDF
vexy-lines-utils export ~/Art/portrait.lines

# Export a folder tree to SVG
vexy-lines-utils export ~/Projects/posters --format svg --verbose

# Create vector art from a photo via the MCP API
python -c "
from vexy_lines_utils.mcp import MCPClient
with MCPClient() as vl:
    vl.new_document(dpi=300, source_image='photo.jpg')
    tree = vl.get_layer_tree()
    layer = vl.add_layer(group_id=tree.id)
    vl.add_fill(layer['id'], 'linear', '#000000', {'interval': 20, 'angle': 45})
    vl.render()
    vl.export_pdf('output.pdf')
"
```

This package does three things:

1. **Batch export** `.lines` documents to PDF or SVG via plist injection and AppleScript
2. **Programmatic control** of Vexy Lines through its embedded MCP server — create documents, add fills, render, export
3. **Video processing** — run every frame of a video through Vexy Lines and reassemble into an animated vector art video

Built for studios, power users, and anyone who'd rather type a command than click through menus.

---

## What Is Vexy Lines?

[Vexy Lines](https://www.vexy.art) is a macOS desktop application that transforms raster images into vector artwork. It reads pixel brightness and builds vector strokes: dark areas produce thick lines, bright areas thin ones (or the reverse).

Twelve fill algorithms, each interpreting your image differently:

| Algorithm | What It Does |
|-----------|-------------|
| **Linear** | Parallel straight lines — copper-plate engravings |
| **Wave** | Flowing curves that undulate across the image |
| **Radial** | Lines exploding outward from a centre point |
| **Circular** | Concentric rings emanating from the centre |
| **Spiral** | Continuous winding from centre to edge |
| **Halftone** | Newspaper-style dots scaled by brightness |
| **Trace** | Edge detection — boundaries become paths |
| **Wireframe** | 3D-looking dimensional lattices |
| **Scribble** | Organic, hand-drawn randomness |
| **Fractal** | Recursive mathematical patterns |
| **Text** | Typography-based painting |
| **Handmade** | Your own custom drawn strokes |

The app also has layers, groups, masks, dynamic colour, 3D mesh warping, multiple source images per composition, and overlap control for woven effects. Projects save as `.lines` files.

More at [vexy.art](https://www.vexy.art) and [help.vexy.art](https://help.vexy.art).

---

## System Requirements

| Requirement | Detail |
|-------------|--------|
| **OS** | macOS 10.14+ (Mojave or later) |
| **Application** | [Vexy Lines](https://www.vexy.art) installed |
| **Python** | 3.10 or newer |
| **Accessibility** | Terminal needs accessibility permissions (for AppleScript). MCP commands do not require this. |

---

## Installation

### From PyPI

```bash
pip install vexy-lines-utils
```

With [uv](https://github.com/astral-sh/uv):

```bash
uv pip install vexy-lines-utils
```

### Optional Dependencies

```bash
# SVG parsing and manipulation (svglab)
pip install vexy-lines-utils[svg]

# Video processing (PyAV, resvg-py, Pillow, svglab)
pip install vexy-lines-utils[video]

# Everything
pip install vexy-lines-utils[all]
```

### From Source

```bash
git clone https://github.com/vexyart/vexy-lines-utils.git
cd vexy-lines-utils
pip install -e ".[dev,test]"
```

### Accessibility Permissions (Export Only)

The batch exporter drives Vexy Lines through AppleScript and needs accessibility access. MCP commands skip this entirely.

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Add your terminal (Terminal.app, iTerm2, VS Code, etc.)
3. Restart the terminal

---

## CLI Reference

The package installs a `vexy-lines-utils` command with seven subcommands.

### `export` — Batch Export

Export `.lines` documents to PDF or SVG. The workhorse.

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

# Pipe verbose output to a log file
vexy-lines-utils export ~/problem-files/ --verbose 2>&1 | tee export.log
```

**Exit behaviour:** the exporter continues past individual failures. On completion it returns a summary:

```json
{
  "processed": 10,
  "success": 9,
  "skipped": 0,
  "failed": 1,
  "failures": [["path/to/broken.lines", "Failed to open file"]],
  "validation_failures": [],
  "dry_run": false,
  "total_time": 42.3,
  "average_time": 4.7
}
```

### `mcp_status` — Check MCP Server

```bash
vexy-lines-utils mcp_status
vexy-lines-utils mcp_status --port 47384
```

Checks if the Vexy Lines MCP server is reachable. Returns document info on success.

### `tree` — Print Layer Tree

```bash
vexy-lines-utils tree
vexy-lines-utils tree --json_output
```

Prints the full layer tree of the current document. With `--json_output`, returns machine-readable JSON.

```
document: My Artwork (id=1)
  group: Background (id=2)
    layer: Layer 1 (id=3)
      fill: Fill 1 (id=4) [linear]
```

### `new_document` — Create Document

```bash
vexy-lines-utils new_document --source_image ~/Art/portrait.jpg --dpi 300
vexy-lines-utils new_document --width 800 --height 600 --dpi 150
```

Creates a new document via MCP. When a source image is provided, the document dimensions match the image.

### `open` — Open Document

```bash
vexy-lines-utils open ~/Art/project.lines
```

Opens an existing `.lines` file via MCP.

### `add_fill` — Add Fill to Layer

```bash
vexy-lines-utils add_fill --layer_id 5 --fill_type linear --color "#ff0000"
```

Adds a fill to a layer. Get layer IDs from the `tree` command.

### `render` — Trigger Render

```bash
vexy-lines-utils render
```

Triggers a full render of the current document.

**All MCP subcommands** accept `--host` and `--port` options (default `127.0.0.1:47384`).

---

## Python API

### Batch Export

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

### ExportConfig

Controls every aspect of the export pipeline:

```python
from vexy_lines_utils import ExportConfig

config = ExportConfig(
    app_name="Vexy Lines",     # application name
    format="pdf",              # "pdf" or "svg"
    poll_interval=0.2,         # seconds between window checks
    wait_for_app=20.0,         # app launch timeout
    wait_for_file=20.0,        # file open timeout
    post_action_delay=0.4,     # pause after close actions
    timeout_multiplier=1.0,    # scale all timeouts (0.1–10.0)
    max_retries=3,             # retry attempts per file (0–10)
)

# Scale a timeout by the multiplier
actual = config.scale_timeout(20.0)  # → 20.0 with default multiplier

# Properties
config.export_menu_item  # → "Export PDF File" or "Export SVG File"
config.export_extension  # → ".pdf" or ".svg"
```

### ExportStats

Tracks batch results:

```python
stats.processed          # total files attempted
stats.success            # successful exports
stats.skipped            # already existed (no --force)
stats.failures           # list of (path, reason) tuples
stats.validation_failures # exports that failed validation
stats.get_total_time()   # seconds since start
stats.get_average_time() # seconds per file
stats.human_summary()    # formatted text summary
stats.as_dict()          # JSON-serialisable dict
```

---

## MCP Client

The MCP client connects directly to Vexy Lines' embedded JSON-RPC 2.0 server on `localhost:47384`. No AppleScript, no accessibility permissions, no plist injection. Just TCP.

### Connecting

```python
from vexy_lines_utils.mcp import MCPClient

# Auto-launches Vexy Lines if not running
with MCPClient() as vl:
    info = vl.get_document_info()
    print(f"{info.width_mm:.1f} x {info.height_mm:.1f} mm @ {info.resolution} DPI")
```

```python
# Disable auto-launch, custom timeout
with MCPClient(host="127.0.0.1", port=47384, timeout=60.0, auto_launch=False) as vl:
    ...
```

The client handles the MCP handshake automatically on entry and cleans up on exit. If the app isn't running and `auto_launch=True` (the default), it starts the app and waits for the server.

### Document Operations

```python
with MCPClient() as vl:
    # Create a new document from a source image
    doc = vl.new_document(dpi=300, source_image="/path/to/photo.jpg")
    # doc.width, doc.height, doc.dpi, doc.root_id, doc.status

    # Or create a blank canvas
    doc = vl.new_document(width=800, height=600, dpi=150)

    # Open an existing project
    vl.open_document("~/Art/project.lines")

    # Get document metadata
    info = vl.get_document_info()
    # info.width_mm, info.height_mm, info.resolution, info.units, info.has_changes

    # Save (to current path or a new one)
    vl.save_document()
    vl.save_document("/path/to/save.lines")

    # Export via the generic method
    vl.export_document("/path/to/output.pdf")
    vl.export_document("/path/to/output.svg", format="svg")
    vl.export_document("/path/to/output.png", format="png", dpi=150)
```

### Layer Structure

Documents have a tree structure: **Document → Groups → Layers → Fills**.

```python
with MCPClient() as vl:
    # Get the full layer tree
    tree = vl.get_layer_tree()
    # tree.id, tree.type, tree.caption, tree.visible, tree.children

    # Walk the tree
    for group in tree.children:
        print(f"Group: {group.caption} (id={group.id})")
        for layer in group.children:
            print(f"  Layer: {layer.caption} (id={layer.id})")
            for fill in layer.children:
                print(f"    Fill: {fill.fill_type} (id={fill.id})")

    # Add a group
    group = vl.add_group(caption="Eyes", source_image_path="/path/to/eyes.jpg")

    # Add a layer to a group
    layer = vl.add_layer(group_id=tree.id)

    # Delete any object by ID
    vl.delete_object(object_id=42)

    # Rename an object
    vl.set_caption(object_id=layer["id"], caption="Main Fill")

    # Toggle visibility
    vl.set_visible(object_id=layer["id"], visible=False)
```

### Fill Operations

Fills are where the vector art happens. Each fill algorithm interprets the source image differently.

```python
with MCPClient() as vl:
    doc = vl.new_document(dpi=300, source_image="photo.jpg")
    tree = vl.get_layer_tree()
    layer = vl.add_layer(group_id=tree.id)

    # Add a fill with type, colour, and parameters
    fill = vl.add_fill(
        layer_id=layer["id"],
        fill_type="linear",
        color="#000000",
        params={
            "interval": 20,      # spacing between strokes (px)
            "thickness": 15,     # max stroke thickness (px)
            "thickness_min": 0,  # min stroke thickness (px)
            "angle": 45,         # line angle in degrees
        },
    )

    # Read fill parameters
    params = vl.get_fill_params(fill_id=fill["id"])

    # Update fill parameters (keyword arguments)
    vl.set_fill_params(fill["id"], interval=30, angle=90, color="#cc0000")
```

**Fill types:** `linear`, `wave`, `circular`, `radial`, `spiral`, `scribble`, `halftone`, `handmade`, `fractals`, `trace`, `text`, `wireframe`

**Common fill parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `interval` | float | Spacing between strokes in pixels |
| `thickness` | float | Maximum stroke thickness in pixels |
| `thickness_min` | float | Minimum stroke thickness in pixels |
| `angle` | float | Line angle in degrees (fill-type dependent) |
| `color` | string | Stroke colour as hex (e.g. `"#ff0000"`) |

Parameters vary by fill type. Use `get_fill_params()` to see what a specific fill accepts.

### Masks and Transforms

Masks restrict fills to specific regions. Transforms move, rotate, and scale layers.

```python
with MCPClient() as vl:
    # Apply an SVG path mask (pixel coordinates, top-left origin)
    eye_left = "M 680 410 C 720 360 820 360 860 410 C 900 460 900 530 860 570 C 820 610 720 610 680 570 C 640 530 640 460 680 410 Z"
    eye_right = "M 1180 410 C 1220 360 1320 360 1360 410 C 1400 460 1400 530 1360 570 C 1320 610 1220 610 1180 570 C 1140 530 1140 460 1180 410 Z"

    vl.set_layer_mask(
        layer_id=5,
        paths=[eye_left, eye_right],
        mode="create",  # "create" (replace), "add" (union), "sub" (subtract)
    )

    # Read a mask back
    mask = vl.get_layer_mask(layer_id=5)

    # 2D transform
    vl.transform_layer(
        layer_id=5,
        translate_x=100, translate_y=50,
        rotate_deg=15,
        scale_x=1.2, scale_y=1.2,
    )

    # Perspective warp (four corners as [x, y] pairs)
    vl.set_layer_warp(
        layer_id=5,
        top_left=[0, 0],
        top_right=[800, 50],
        bottom_right=[750, 600],
        bottom_left=[50, 580],
    )
```

### Rendering and Export

Vexy Lines renders asynchronously. You trigger a render, then wait for it to finish before exporting.

```python
with MCPClient() as vl:
    # Trigger render and wait (the easy way)
    vl.render(timeout=120.0)

    # Or do it manually for more control
    vl.render_all()
    status = vl.get_render_status()  # status.rendering → True/False
    done = vl.wait_for_render(timeout=120.0, poll_interval=0.5)
```

### High-Level Export

Typed convenience methods that return the resolved output path:

```python
with MCPClient() as vl:
    vl.render()

    # Each returns a Path object
    pdf_path  = vl.export_pdf("output.pdf", dpi=300)
    svg_path  = vl.export_svg("output.svg")
    png_path  = vl.export_png("output.png", dpi=150)
    jpeg_path = vl.export_jpeg("output.jpg", dpi=150)
    eps_path  = vl.export_eps("output.eps")
```

Raster exports (PNG, JPEG) require a full pixel render and can be slow at high DPI. Vector exports (PDF, SVG, EPS) are fast regardless of DPI.

### SVG Operations

Get SVG content as a string or as a parsed object for manipulation:

```python
with MCPClient() as vl:
    vl.render()

    # SVG as a string
    svg_string = vl.svg()

    # SVG as a parsed svglab object (requires: pip install vexy-lines-utils[svg])
    svg_obj = vl.svg_parsed()
    svg_obj.width = 1920
    svg_obj.height = 1080
    img = svg_obj.render()  # → PIL Image
```

### Edit Operations

```python
with MCPClient() as vl:
    vl.undo()
    vl.redo()

    selection = vl.get_selection()
    vl.select_object(object_id=5)
```

### Complete Workflow

Putting it all together — create a multi-fill artwork from a photo:

```python
from vexy_lines_utils.mcp import MCPClient

with MCPClient() as vl:
    # Load a photo
    doc = vl.new_document(dpi=300, source_image="portrait.jpg")
    tree = vl.get_layer_tree()
    root = tree.id

    # Layer 1: linear engraving at 45 degrees
    layer1 = vl.add_layer(group_id=root)
    vl.add_fill(
        layer_id=layer1["id"],
        fill_type="linear",
        color="#000000",
        params={"interval": 20, "angle": 45, "thickness": 15},
    )

    # Layer 2: circular overlay in red
    layer2 = vl.add_layer(group_id=root)
    vl.add_fill(
        layer_id=layer2["id"],
        fill_type="circular",
        color="#cc0000",
        params={"interval": 30, "thickness": 10},
    )

    # Render and export
    vl.render(timeout=120.0)
    vl.export_pdf("portrait_engraved.pdf")
    vl.export_svg("portrait_engraved.svg")
    vl.export_png("portrait_engraved.png", dpi=150)
```

---

## Video Processing

Transform videos frame-by-frame through Vexy Lines fills. Each frame becomes vector art, then gets reassembled into a video with the original audio.

Requires optional dependencies:

```bash
pip install vexy-lines-utils[video]
```

### Quick Start

```python
from vexy_lines_utils.video import process_video

process_video(
    "input.mp4",
    "output.mp4",
    fill_type="linear",
    color="#000000",
    interval=20,
    thickness=15,
    dpi=72,          # lower DPI = faster processing
)
```

By default, the fill angle rotates smoothly from 0 to 180 degrees across the video, creating an animated engraving effect.

### Custom Per-Frame Parameters

```python
from vexy_lines_utils.video import process_video

def frame_params(frame_index: int, total_frames: int) -> dict:
    """Rotate angle and vary thickness across the video."""
    progress = frame_index / max(total_frames - 1, 1)
    return {
        "angle": progress * 360,
        "thickness": 10 + progress * 20,
    }

process_video(
    "input.mp4",
    "output.mp4",
    fill_type="wave",
    color="#003366",
    frame_params=frame_params,
    on_progress=lambda i, n: print(f"  [{i}/{n}]"),
)
```

### Probe Video Metadata

```python
from vexy_lines_utils.video import probe

info = probe("input.mp4")
print(f"{info.width}x{info.height} @ {info.fps:.1f} fps")
print(f"{info.total_frames} frames, {info.duration:.1f}s")
print(f"Audio: {'yes' if info.has_audio else 'no'}")
```

### process_video Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_path` | path | *(required)* | Input video (MP4, MOV, AVI, WebM, etc.) |
| `output_path` | path | *(required)* | Output video path |
| `fill_type` | str | `"linear"` | Fill algorithm |
| `color` | str | `"#000000"` | Stroke colour (hex) |
| `interval` | float | `20` | Spacing between strokes (px) |
| `thickness` | float | `15` | Max stroke thickness (px) |
| `thickness_min` | float | `0` | Min stroke thickness (px) |
| `dpi` | int | `72` | Document DPI. Lower = faster. 72 is good for video. |
| `frame_params` | callable | angle rotation | `(frame_index, total) → dict` of fill param overrides |
| `max_frames` | int | all | Process only first N frames (for testing) |
| `on_progress` | callable | none | `(frame_index, total) → None` callback |
| `host` | str | `"127.0.0.1"` | MCP server address |
| `port` | int | `47384` | MCP server port |
| `timeout` | float | `60.0` | Render timeout per frame (seconds) |

### Pipeline

Each frame goes through:

```
Video Frame → temp PNG → Vexy Lines (load, fill, render) → SVG → resvg (PNG) → PyAV → Output Video
```

Audio is preserved via a second-pass ffmpeg merge.

### Command-Line

```bash
python examples/mcp_create_video.py input.mp4 output.mp4
python examples/mcp_create_video.py input.mp4 output.mp4 --fill_type wave
python examples/mcp_create_video.py input.mp4 output.mp4 --max_frames 10
python examples/mcp_create_video.py input.mp4 output.mp4 --interval 30 --thickness 25
```

---

## MCP Protocol Details

Vexy Lines embeds a JSON-RPC 2.0 server on TCP port **47384**. Messages are newline-delimited JSON.

A bridge binary (`vexylines-mcp`) converts stdio↔TCP for integration with Claude Desktop, Cursor, and other MCP hosts. The Python client connects directly via TCP.

**25 tools** in five groups:

| Group | Tools |
|-------|-------|
| **Document** | `new_document`, `open_document`, `save_document`, `export_document`, `get_document_info` |
| **Structure** | `get_layer_tree`, `add_group`, `add_layer`, `add_fill`, `delete_object` |
| **Fill params** | `get_fill_params`, `set_fill_params` |
| **Visual** | `set_source_image`, `set_caption`, `set_visible`, `set_layer_mask`, `get_layer_mask`, `transform_layer`, `set_layer_warp` |
| **Control** | `render_all`, `get_render_status`, `undo`, `redo`, `get_selection`, `select_object` |

**Coordinates:** All spatial parameters are in pixels at document DPI. Origin is top-left.

**Protocol version:** `2024-11-05`

### Low-Level Access

If the typed wrappers don't cover your use case, call tools directly:

```python
with MCPClient() as vl:
    # Call any MCP tool by name
    result = vl.call_tool("get_document_info")
    # Returns parsed JSON dict or plain string
```

---

## Response Types

The MCP client returns typed dataclasses, not raw dicts.

### DocumentInfo

```python
@dataclass
class DocumentInfo:
    width_mm: float      # document width in millimetres
    height_mm: float     # document height in millimetres
    resolution: float    # DPI
    units: str           # unit system
    has_changes: bool    # unsaved changes?
```

### LayerNode

```python
@dataclass
class LayerNode:
    id: int              # unique object ID
    type: str            # "document", "group", "layer", or "fill"
    caption: str         # display name
    visible: bool        # visibility flag
    fill_type: str | None  # fill algorithm (only for type=="fill")
    children: list[LayerNode]  # child nodes
```

### NewDocumentResult

```python
@dataclass
class NewDocumentResult:
    status: str          # "ok" or error
    width: float         # canvas width in pixels
    height: float        # canvas height in pixels
    dpi: float           # resolution
    root_id: int         # ID of the root group
```

### RenderStatus

```python
@dataclass
class RenderStatus:
    rendering: bool      # True while rendering is in progress
```

### VideoInfo

```python
@dataclass
class VideoInfo:
    width: int           # frame width in pixels
    height: int          # frame height in pixels
    fps: float           # frames per second
    total_frames: int    # total frame count
    duration: float      # duration in seconds
    has_audio: bool      # whether audio stream exists
```

---

## Error Handling

### Export Errors

`AutomationError` carries an `error_code` string. Each code maps to a recovery suggestion:

| Code | Meaning | What to Do |
|------|---------|------------|
| `APP_NOT_FOUND` | Vexy Lines not in `/Applications` | Install it, or check the name |
| `OPEN_FAILED` | Could not open the `.lines` file | Check permissions, try opening manually |
| `WINDOW_TIMEOUT` | Expected window did not appear | Increase `--timeout_multiplier`, close modal dialogs |
| `EXPORT_MENU_TIMEOUT` | Export menu item could not be clicked | Ensure document is open and active |
| `SAVE_DIALOG_TIMEOUT` | Save dialog did not appear | Check for blocking dialogs |
| `EXPORT_TIMEOUT` | Exported file never appeared | Increase timeout, check disk space |
| `INVALID_PDF` | Output failed PDF validation | Try manual export, check disk space |
| `FILE_INVALID` | Input `.lines` file is malformed | Try opening manually, check file size |
| `NO_FILES` | No `.lines` files found at path | Check the path and file extensions |
| `USER_INTERRUPT` | Cancelled by Ctrl+C | Preferences were restored automatically |
| `PLIST_ERROR` | Failed to read/write preferences | Check plist permissions |

```python
from vexy_lines_utils import AutomationError
from vexy_lines_utils.core.errors import get_error_suggestion

try:
    stats = exporter.export(Path("~/Art"))
except AutomationError as e:
    print(f"Error [{e.error_code}]: {e}")
    print(f"Suggestion: {get_error_suggestion(e.error_code)}")
```

### MCP Errors

`MCPError` is raised when the server is unreachable, returns an error, or sends invalid data.

```python
from vexy_lines_utils.mcp import MCPClient, MCPError

try:
    with MCPClient() as vl:
        vl.render_all()
except MCPError as e:
    print(f"MCP error: {e.message}")
```

Common MCP failures:
- **Connection refused** — Vexy Lines isn't running or MCP server isn't active
- **Protocol mismatch** — client and server protocol versions differ
- **Timeout** — render or export took too long
- **Tool error** — invalid parameters or missing document

---

## Architecture

### Export Pipeline

```
Discovery → Plist Injection → App Activation → Per-File Export Loop → Cleanup
```

1. **Discovery** — `find_lines_files()` resolves input. Single file or recursive directory search.
2. **Plist injection** — `PlistManager` quits the app, snapshots its preferences, writes export settings via `defaults write` on the `com.fontlab.vexy-lines` domain.
3. **App activation** — `AppleScriptBridge` launches Vexy Lines. `WindowWatcher` polls until a window appears.
4. **Per-file processing** — For each `.lines` file: validate → open → wait for window → trigger `File → Export` menu → poll for stable output file → validate output → close window.
5. **Cleanup** — `PlistManager` restores original preferences, even after exceptions or Ctrl+C.

### MCP Pipeline

```
MCPClient → TCP Socket → JSON-RPC 2.0 → Vexy Lines MCP Server
```

Direct. No OS automation, no plist manipulation, no accessibility permissions.

### Module Map

```
src/vexy_lines_utils/
├── __init__.py              # public API exports
├── __main__.py              # Fire CLI (VexyLinesCLI)
├── __version__.py           # git-tag version (hatch-vcs)
├── exporter.py              # VexyLinesExporter — batch export orchestrator
├── video.py                 # video-to-video processing pipeline
├── core/
│   ├── config.py            # ExportConfig dataclass
│   ├── errors.py            # AutomationError, error codes, suggestions
│   ├── plist.py             # PlistManager — preference injection/restore
│   └── stats.py             # ExportStats — result tracking
├── automation/
│   ├── bridges.py           # AppleScriptBridge, ApplicationBridge protocol
│   └── window_watcher.py    # poll-based window title matching
├── mcp/
│   ├── __init__.py          # MCPClient, MCPError
│   ├── client.py            # TCP JSON-RPC 2.0 client with all tool methods
│   └── types.py             # DocumentInfo, LayerNode, NewDocumentResult, RenderStatus
└── utils/
    ├── file_utils.py        # file discovery and validation (PDF/SVG/.lines)
    ├── interrupt.py         # SIGINT handler for graceful Ctrl+C
    └── system.py            # macOS text-to-speech wrapper
```

### Key Design Decisions

- **Plist-driven export, not dialog-driven.** v2.0 replaced GUI automation (PyXA, pyautogui) with `defaults write` on the app's preference domain. Faster, more reliable, fewer dependencies.
- **Progressive retry.** Export attempts use escalating delays (0.5s → 2.0s → 5.0s) because render time varies.
- **File-size polling.** After triggering export, we poll until the output file size stabilises across 2 consecutive checks — not just "file exists."
- **Preference snapshot/restore.** `PlistManager` is a context manager. It always restores, even after Ctrl+C.
- **Zero new runtime deps for MCP.** The client uses stdlib `socket` + `json`. Intentional.
- **Auto-launch.** `MCPClient` starts Vexy Lines automatically if it's not running, with gentle backoff polling until the server is ready.

---

## Interrupt Handling

Press **Ctrl+C** once during a batch export to finish the current file and stop cleanly. Press again to terminate immediately. Preferences are always restored — `PlistManager` runs in a context manager, so Vexy Lines settings are never left in a modified state.

---

## Examples

The `examples/` directory contains ready-to-run scripts:

| Script | What It Does |
|--------|-------------|
| [`batch_export.py`](examples/batch_export.py) | Batch export `.lines` files to PDF/SVG |
| [`mcp_hello.py`](examples/mcp_hello.py) | Connect to MCP, print document info and layer tree |
| [`mcp_create_artwork.py`](examples/mcp_create_artwork.py) | Full workflow: load photo → add fill → render → export |
| [`mcp_masks.py`](examples/mcp_masks.py) | Apply SVG path masks to restrict fills to regions |
| [`mcp_create_video.py`](examples/mcp_create_video.py) | Transform a video frame-by-frame through vector art fills |

Each example is a standalone script that works with `uv run`:

```bash
uv run examples/mcp_create_artwork.py photo.jpg output.pdf
uv run examples/mcp_create_video.py input.mp4 output.mp4 --fill_type wave
```

---

## Dependencies

**Runtime** — intentionally minimal:

| Package | Purpose |
|---------|---------|
| [fire](https://github.com/google/python-fire) ≥ 0.6.0 | CLI framework — zero-boilerplate commands |
| [loguru](https://github.com/Delgan/loguru) ≥ 0.7.2 | Structured logging with colour |

**MCP client** — no additional dependencies (stdlib `socket` + `json`).

**Optional:**

| Extra | Packages | Purpose |
|-------|----------|---------|
| `[svg]` | svglab | SVG parsing and manipulation |
| `[video]` | av, resvg-py, Pillow, svglab | Video frame processing pipeline |
| `[all]` | all of the above | Everything |

**Removed in v2.0:** `mac-pyxa`, `pyautogui-ng`, `pyperclip` — replaced by native `osascript` + plist manipulation.

---

## Troubleshooting

### "Vexy Lines is not installed"

- Check that `Vexy Lines.app` is in `/Applications`
- Try opening it manually first
- Check for license or trial expiration

### Export timing out

- Increase timeouts: `--timeout_multiplier 2.0` or `3.0`
- Check for modal dialogs blocking Vexy Lines
- Try a single file first to isolate the issue

### "Accessibility permissions required"

- **System Settings** → **Privacy & Security** → **Accessibility** → add your terminal
- Restart the terminal after granting permissions
- IDEs (VS Code, PyCharm) need permission too

### MCP server unreachable

- Make sure Vexy Lines is running
- Check port 47384 isn't in use by something else
- The MCP server activates when a document is open
- Try: `vexy-lines-utils mcp_status`

### Preferences left in a modified state

This shouldn't happen — `PlistManager` restores on exit regardless of how the process ends. If it does:

```bash
# Remove injected preferences
defaults delete com.fontlab.vexy-lines

# Or just relaunch Vexy Lines — it recreates defaults on start
```

### Video processing errors

- Install all video deps: `pip install vexy-lines-utils[video]`
- `ffmpeg` must be on your PATH for audio merging
- Use `--max_frames 5` for quick testing
- Lower DPI (`--dpi 72`) speeds up processing

---

## Development

### Setup

```bash
git clone https://github.com/vexyart/vexy-lines-utils.git
cd vexy-lines-utils

# uv (recommended)
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev,test]"

# or pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,test]"
```

### Commands

```bash
# Run tests (124 tests, ~3s)
uvx hatch test

# Run tests with coverage
uvx hatch run test:test-cov

# Format code
uvx hatch fmt

# Lint and type-check
uvx hatch run lint:style
uvx hatch run lint:typing
```

### Testing

124 tests across two files:

- `tests/test_package.py` — 82 tests covering config, plist, stats, exporter, file utils, CLI
- `tests/test_mcp_client.py` — 42 tests covering connection, framing, handshake, tool wrappers, error handling

All tests mock macOS-specific APIs so they run on any platform in CI.

Test naming convention: `test_function_name_when_condition_then_result`.

### Project Conventions

- **`this_file` tracking** — every source file has `# this_file: <path>` near the top
- **Absolute imports only** — Ruff enforces `ban-relative-imports = 'all'`
- **Version from git tags** — `hatch-vcs` generates `__version__.py` automatically
- **Line length** — 120 characters
- **Target Python** — 3.10+ (type hints use `X | Y` union syntax)
- **Minimal runtime deps** — only `fire` and `loguru`

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full release history.

### v3.0 Highlights

- MCP client module with 25+ typed tool methods
- 6 new CLI subcommands for MCP operations
- Auto-launch: MCPClient starts Vexy Lines if not running
- High-level export API: `export_pdf()`, `export_svg()`, `export_png()`, `export_jpeg()`, `export_eps()`
- SVG string and parsed object access
- Video-to-video processing pipeline
- 124 tests (up from 79)

### v2.0 Highlights

- Complete rewrite from GUI dialog automation to plist-driven export
- Removed three macOS GUI dependencies
- Added SVG export, preference snapshot/restore, progressive retry
- 79 tests in 1.2 seconds

---

## About

**vexy-lines-utils** is developed by [FontLab Ltd.](https://www.fontlab.com), creators of [Vexy Lines](https://www.vexy.art) and industry-standard font editing software.

- [Vexy Lines](https://www.vexy.art) — the application
- [Documentation](https://help.vexy.art) — user guide
- [Support](https://support.vexy.art) — FontLab support
- [Issues](https://github.com/vexyart/vexy-lines-utils/issues) — bug reports and feature requests

## License

MIT — see [LICENSE](LICENSE) for details.
