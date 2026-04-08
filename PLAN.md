---
this_file: PLAN.md
---

# PLAN: vexy-lines-utils v4.0 — .lines Parser, Style Engine, GUI & CLI

## Project Scope

Transform vexy-lines-utils from an export/MCP tool into a complete style-transfer workstation. Users load `.lines` style references, apply them to images or video frames via the Vexy Lines MCP API, and export as SVG/PNG/JPG/MP4/LINES. Two styles can be interpolated across a sequence of frames.

The package gains four new capabilities:
1. **`.lines` parser** — read the XML format without the app
2. **Style engine** — extract, apply, and interpolate fill structures
3. **CustomTkinter GUI** — drag-and-drop desktop app with Lines/Images/Video input tabs
4. **Enhanced CLI** — Fire-based CLI mirroring all GUI operations

## Architecture Overview

```
vexy_lines_utils/
  parser.py          # .lines XML parser → LinesDocument dataclass tree
  style.py           # Style extraction, application (via MCP), interpolation
  gui/
    __init__.py      # GUI entry point
    app.py           # Main App window (CustomTkinter + TkinterDnD)
    widgets.py       # CTkRangeSlider and custom widgets
    panels.py        # Input tabs, style pickers, output bar
  __main__.py        # Enhanced Fire CLI (existing + new subcommands)
  video.py           # Existing video processing (updated to use style engine)
  mcp/               # Existing MCP client (unchanged)
  core/              # Existing export core (unchanged)
  ...
```

## .lines File Format (Reference)

`.lines` files are XML. Root element: `<Project app="vexylines" version="3.0.1" caption="..." dpi="300">`.

### Top-level children

| Element | Content |
|---------|---------|
| `<form_data>` | UI state (ignored by parser) |
| `<Objects>` | Layer tree: groups (`LrSection`), layers (`FreeMesh`), fills (`*StrokesTmpl`) |
| `<SourcePict>` | Source image — `<ImageData>` is base64 → 4-byte BE size + zlib → JPEG |
| `<Document>` | Document properties (thickness ranges, DPI, intervals, colors) |
| `<Workspace>` | Viewport state (ignored) |
| `<PreviewDoc>` | Preview image — base64 → raw PNG |

### Object types in `<Objects>`

| XML Tag | Role | Key Attributes |
|---------|------|---------------|
| `LrSection` | Group | `caption`, `type=16777602`, `expanded` |
| `FreeMesh` | Layer | `caption`, `type=16793857`, `mask_enabled`, grid edges |
| `LinearStrokesTmpl` | Fill: linear | `type=16781569`, `interval`, `angle`, `color_name`, ... |
| `FreeCurveStrokesTmpl` | Fill: flowlines/trace | `type=16781578`, `type_conv`, `interval`, `angle`, ... |
| `CircularStrokesTmpl` | Fill: circular | Similar params |
| `RadialStrokesTmpl` | Fill: radial | Similar params |
| `SpiralStrokesTmpl` | Fill: spiral | Similar params |
| `HalftoneStrokesTmpl` | Fill: halftone | Similar params |
| `MaskData` | Layer mask | `mask_type`, `invert_mask`, `tolerance` |
| `row_grid_edge` / `col_grid_edge` | Mesh warp grid | Node data |

### Fill parameter mapping

Fill XML attributes map to MCP `set_fill_params` keys. Common numeric params that can be interpolated:

- `interval` — stroke spacing
- `angle` — rotation angle (degrees)
- `uplimit` / `downlimit` — brightness thresholds (0–255)
- `smoothness` — curve smoothness
- `multiplier` — size multiplier
- `base_width` — base stroke width
- `thickness` / `thick_gap` — stroke thickness
- `dispersion` — random displacement
- `vert_disp` — vertical displacement
- `shear` — shear angle

### Fill type tag → MCP fill_type mapping

| XML Tag | `type_conv` | MCP `fill_type` |
|---------|-------------|-----------------|
| `LinearStrokesTmpl` | — | `linear` |
| `FreeCurveStrokesTmpl` | 9 | `trace` / `scribble` |
| `CircularStrokesTmpl` | — | `circular` |
| `RadialStrokesTmpl` | — | `radial` |
| `SpiralStrokesTmpl` | — | `spiral` |
| `HalftoneStrokesTmpl` | — | `halftone` |

---

## Phase 1: .lines Parser Module

**Goal:** Parse `.lines` XML into a typed Python object tree. No app required.

### New file: `src/vexy_lines_utils/parser.py`

#### Dataclasses

```python
@dataclass
class FillParams:
    """All numeric and string parameters of a fill."""
    fill_type: str          # "linear", "circular", "trace", etc.
    color: str              # "#rrggbbaa"
    interval: float
    angle: float
    thickness: float
    thickness_min: float
    smoothness: float
    # ... all other numeric params as float | None
    raw: dict[str, str]     # All XML attributes preserved

@dataclass
class MaskInfo:
    mask_type: int
    invert: bool
    tolerance: float

@dataclass
class FillNode:
    xml_tag: str            # e.g. "LinearStrokesTmpl"
    caption: str
    params: FillParams
    object_id: int | None

@dataclass
class LayerInfo:
    caption: str
    object_id: int | None
    visible: bool
    mask: MaskInfo | None
    fills: list[FillNode]
    grid_edges: list[dict]  # Raw grid data for mesh warp

@dataclass
class GroupInfo:
    caption: str
    object_id: int | None
    expanded: bool
    children: list[GroupInfo | LayerInfo]

@dataclass
class DocumentProps:
    width_mm: float
    height_mm: float
    dpi: int
    thickness_min: float
    thickness_max: float
    interval_min: float
    interval_max: float

@dataclass
class LinesDocument:
    """Complete parsed representation of a .lines file."""
    caption: str
    version: str
    dpi: int
    props: DocumentProps
    groups: list[GroupInfo]   # Top-level structure from <Objects>
    source_image: bytes | None  # Decoded JPEG bytes
    preview_image: bytes | None # Decoded PNG bytes
    raw_xml: ET.Element         # Preserved for round-trip
```

#### Functions

```python
def parse(path: str | Path) -> LinesDocument
def extract_source_image(path: str | Path, output: str | Path) -> Path
def extract_preview_image(path: str | Path, output: str | Path) -> Path
def get_style(doc: LinesDocument) -> list[GroupInfo]  # Just the structure
```

### Tasks
- Define all dataclasses in `parser.py`
- Implement XML parsing: `<Objects>` → recursive `GroupInfo`/`LayerInfo`/`FillNode` tree
- Implement `_decode_source_pict()` and `_decode_preview_doc()` (from `lines2img.py`)
- Implement `parse()` top-level function
- Implement `extract_source_image()` and `extract_preview_image()`
- Map XML fill tags to MCP fill types
- Map XML fill attributes to `FillParams` fields
- Unit tests with real `.lines` files from `_private/lines-examples/`

---

## Phase 2: App-less Image Extraction

**Goal:** Integrate `lines2img.py` functionality into the package CLI.

### New CLI subcommands

```bash
# Extract source image
vexy-lines-utils extract-source input.lines --output source.jpg

# Extract preview image
vexy-lines-utils extract-preview input.lines --output preview.png

# Query .lines file metadata
vexy-lines-utils info input.lines
vexy-lines-utils info input.lines --json

# List layer tree from file (no MCP needed)
vexy-lines-utils file-tree input.lines
```

### Tasks
- Add `extract_source` CLI subcommand
- Add `extract_preview` CLI subcommand
- Add `info` CLI subcommand (prints caption, DPI, dimensions, layer count, fill count)
- Add `file_tree` CLI subcommand (prints layer tree from parsed file)
- Add Pillow to optional dependencies for image conversion
- Tests for each CLI subcommand

---

## Phase 3: Style Engine

**Goal:** Extract style from a `.lines` file and apply it to images/video via MCP. Interpolate between two styles.

### New file: `src/vexy_lines_utils/style.py`

#### Core concepts

- **Style** = the `list[GroupInfo]` extracted from a `.lines` file (groups → layers → fills with params)
- **Apply style** = create a new MCP document, replicate the group/layer/fill structure, set all params
- **Interpolate** = given Style A and Style B with compatible structures, produce Style C where all numeric `FillParams` are `lerp(a, b, t)` for `t ∈ [0, 1]`

#### Functions

```python
@dataclass
class Style:
    groups: list[GroupInfo]
    props: DocumentProps

def extract_style(path: str | Path) -> Style
def styles_compatible(a: Style, b: Style) -> bool
def interpolate_style(a: Style, b: Style, t: float) -> Style
def apply_style(client: MCPClient, style: Style, source_image: str | Path) -> str
    """Apply style via MCP. Returns SVG string of rendered result."""
```

#### Interpolation rules
- Two styles are "compatible" if they have the same group→layer→fill structure (same count and types at each level)
- Numeric params interpolate linearly: `result = a + (b - a) * t`
- String params (like color) use style A's value for `t < 0.5`, style B's for `t >= 0.5` (or hex color lerp)
- If structures differ, fall back to style A only (no interpolation)

### Tasks
- Implement `Style` dataclass and `extract_style()`
- Implement `styles_compatible()` — compare structure trees
- Implement `interpolate_style()` — lerp all numeric FillParams
- Implement color interpolation (hex RGB lerp)
- Implement `apply_style()` — create MCP document, replicate structure, set params
- Unit tests for extraction, compatibility check, interpolation
- Integration test: extract style → apply to image → export SVG

---

## Phase 4: CustomTkinter GUI

**Goal:** Port `_private/gui/style_with_vexy_lines.py` into the package with a Lines tab added.

### New directory: `src/vexy_lines_utils/gui/`

### Dependencies (optional `[gui]` extra)

```toml
gui = [
    "customtkinter>=5.2.0",
    "tkinterdnd2>=0.4.0",
    "Pillow>=10.0.0",
    "opencv-python>=4.8.0",
    "CTkMenuBarPlus>=0.1.0",
]
```

### GUI Layout (from reference + additions)

```
┌─────────────────────────────────────────────────┐
│ Menu: File | Lines | Image | Video | Style | Export │
├──────────────────────────┬──────────────────────┤
│ Inputs                   │ Styles               │
│ ┌──────┬───────┬───────┐ │ ┌───────┬──────────┐ │
│ │Lines │Images │ Video │ │ │ Style │End Style │ │
│ ├──────┴───────┴───────┤ │ ├───────┴──────────┤ │
│ │                      │ │ │                  │ │
│ │ (tab content)        │ │ │ Preview + picker │ │
│ │                      │ │ │                  │ │
│ │ [+] [−] [✕]         │ │ │ [+] label  [✕]  │ │
│ └──────────────────────┘ │ └──────────────────┘ │
├──────────────────────────┴──────────────────────┤
│ Export as [SVG▾] [1x▾] [♪]          [Export ▶] │
└─────────────────────────────────────────────────┘
```

### Tabs

1. **Lines tab** — Drop/add `.lines` files. Style section disabled (grayed out). Export processes each `.lines` file directly.
2. **Images tab** — Drop/add images. Style applied to each image. Preview of selected image.
3. **Video tab** — Drop/add video. Range slider for frame selection. Style applied to each frame.

### Key behaviors (from issue #201)

- Lines tab active → Style/End Style section disabled (grayed out)
- Drag-drop to tab areas works for the active tab's file type
- Menu "File > Add Lines" → switch to Lines tab
- Menu "Image > Add Images" → switch to Images tab
- Menu "Video > Add Video" → switch to Video tab
- Export button → folder picker for SVG/PNG/JPG/LINES, file picker for MP4
- File naming automatic for folder exports

### Files

| File | Content |
|------|---------|
| `gui/__init__.py` | `launch()` function |
| `gui/app.py` | Main `App` class (CTk + TkinterDnD) |
| `gui/widgets.py` | `CTkRangeSlider` (copied from `ctkrangeslider.py`) |
| `gui/panels.py` | `InputsPanel`, `StylesPanel`, `OutputsBar` |
| `gui/processing.py` | Background export thread, progress callbacks |

### Tasks
- Copy and adapt `CTkRangeSlider` widget
- Implement main `App` window with menu bar
- Implement Lines input tab (file list + drag-drop)
- Implement Images input tab (from reference)
- Implement Video input tab (from reference)
- Implement Style/End Style picker panel
- Implement output bar (format, size, audio, export button)
- Implement drag-drop for all tab areas
- Implement menu→tab switching
- Implement Lines tab disabling styles
- Implement export logic (folder picker vs file picker)
- Implement background processing thread
- Add `gui` optional dependency group
- Add `vexy-lines-run` script entry point
- Wire up style engine for actual processing

---

## Phase 5: Enhanced CLI

**Goal:** Fire CLI mirrors all GUI operations plus file querying.

### New subcommands

```bash
# Style transfer: apply style to images
vexy-lines-utils style-transfer \
  --style style.lines \
  --images img1.jpg img2.jpg \
  --output-dir ./out \
  --format png

# Style transfer with interpolation between two styles
vexy-lines-utils style-transfer \
  --style start.lines \
  --end-style end.lines \
  --images img1.jpg img2.jpg img3.jpg \
  --output-dir ./out \
  --format png

# Style transfer to video
vexy-lines-utils style-video \
  --style style.lines \
  --input video.mp4 \
  --output styled.mp4

# Style video with interpolation
vexy-lines-utils style-video \
  --style start.lines \
  --end-style end.lines \
  --input video.mp4 \
  --output styled.mp4 \
  --start-frame 1 \
  --end-frame 100

# Batch export .lines files (no style needed)
vexy-lines-utils batch-convert \
  --input-dir ./lines-files \
  --output-dir ./out \
  --format svg

# Query file info
vexy-lines-utils info file.lines
vexy-lines-utils info file.lines --json

# Extract images
vexy-lines-utils extract-source file.lines --output source.jpg
vexy-lines-utils extract-preview file.lines --output preview.png

# File tree
vexy-lines-utils file-tree file.lines
```

### Tasks
- Add `style_transfer` subcommand (images → styled images)
- Add `style_video` subcommand (video → styled video)
- Add `batch_convert` subcommand (.lines → SVG/PNG/JPG)
- Add `info` subcommand
- Add `extract_source` / `extract_preview` subcommands
- Add `file_tree` subcommand
- Add `gui` subcommand (launches the GUI)
- Support `--verbose` across all subcommands
- Support `--json` for machine-readable output where applicable
- Update existing `export` subcommand to support SVG/PNG/JPG (not just PDF/SVG)

---

## Phase 6: Testing & Documentation

### Unit tests

| Test file | Coverage |
|-----------|----------|
| `tests/test_parser.py` | `parse()`, all dataclasses, image extraction, fill mapping |
| `tests/test_style.py` | `extract_style()`, `interpolate_style()`, `styles_compatible()` |
| `tests/test_cli_new.py` | New CLI subcommands (info, extract, file-tree, style-transfer) |
| `tests/test_gui.py` | GUI widget instantiation (headless where possible) |

### Functional examples

| Example | Purpose |
|---------|---------|
| `examples/parse_lines.py` | Parse and print structure of a .lines file |
| `examples/extract_images.py` | Extract source + preview images |
| `examples/style_transfer.py` | Apply style from one .lines to an image |
| `examples/style_interpolation.py` | Interpolate between two styles across images |
| `examples/style_video.py` | Style-transfer a video with interpolation |

### Documentation
- Update README.md with new capabilities
- Update CLAUDE.md with new architecture
- Update DEPENDENCIES.md with new packages
- Update CHANGELOG.md for v4.0
- Create `test.sh` script to run all tests + examples

### Tasks
- Write parser unit tests (with real .lines fixtures)
- Write style engine unit tests
- Write CLI subcommand tests
- Write functional examples
- Update all documentation files
- Create test.sh
- Run full test suite, fix any failures

---

## Dependencies

### New runtime dependencies (in optional extras)

| Package | Extra | Purpose |
|---------|-------|---------|
| `customtkinter` | `gui` | Modern tkinter widgets |
| `tkinterdnd2` | `gui` | Drag-and-drop support |
| `CTkMenuBarPlus` | `gui` | Menu bar widget |
| `Pillow` | `gui`, `video` | Image handling |
| `opencv-python` | `gui` | Video frame extraction (GUI preview) |

### Existing dependencies (unchanged)
- `fire` — CLI
- `loguru` — logging

### Existing optional dependencies (unchanged)
- `av` — video processing
- `resvg-py` — SVG rasterisation
- `svglab` — SVG parsing

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| XML fill tag mapping incomplete | High | Parse all attributes into `raw` dict; map known ones to typed fields |
| Style interpolation with incompatible structures | Medium | Fall back to single style; warn user |
| tkinterdnd2 installation issues on some platforms | Medium | GUI is optional; CLI works without it |
| MCP server not running for style application | Medium | Clear error messages; `--dry-run` mode |
| Large .lines files (>5MB) parse slowly | Low | XML parsing is fast; images are lazy-decoded |

## Success Criteria

1. `uvx hatch test` passes with all new + existing tests
2. `vexy-lines-utils info *.lines` prints correct metadata
3. `vexy-lines-utils extract-source *.lines` extracts JPEG
4. Style extracted from file A, applied via MCP, produces rendered SVG
5. Two-style interpolation produces smooth parameter transitions
6. GUI launches, accepts drag-drop, triggers export
7. `vexy-lines-utils style-transfer` works end-to-end
8. All existing 124 tests still pass
