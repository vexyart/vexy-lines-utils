---
this_file: TODO.md
---

# TODO: vexy-lines-utils v4.0

## Phase 1: .lines Parser Module
- [x] Define dataclasses: FillParams, MaskInfo, FillNode, LayerInfo, GroupInfo, DocumentProps, LinesDocument
- [x] Implement XML fill tag → MCP fill_type mapping (LinearStrokesTmpl→linear, FreeCurveStrokesTmpl→trace, etc.)
- [x] Implement XML fill attribute → FillParams field mapping (interval, angle, color_name, etc.)
- [x] Implement recursive Objects parser: LrSection→GroupInfo, FreeMesh→LayerInfo, *StrokesTmpl→FillNode
- [x] Implement _decode_source_pict(): base64 → strip 4-byte header → zlib decompress → JPEG bytes
- [x] Implement _decode_preview_doc(): base64 → PNG bytes
- [x] Implement parse(path) → LinesDocument top-level function
- [x] Implement extract_source_image(path, output) → saves JPEG
- [x] Implement extract_preview_image(path, output) → saves PNG
- [x] Write unit tests for parser with real .lines fixtures (21 tests)

## Phase 2: App-less Image Extraction CLI
- [x] Add extract_source CLI subcommand
- [x] Add extract_preview CLI subcommand
- [x] Add info CLI subcommand (caption, DPI, dimensions, layers, fills)
- [x] Add file_tree CLI subcommand (layer tree from parsed file, no MCP)
- [x] Add Pillow to optional dependencies [images] extra
- [x] Write tests for new CLI subcommands (10 tests)

## Phase 3: Style Engine
- [x] Define Style dataclass (groups + document props)
- [x] Implement extract_style(path) → Style
- [x] Implement styles_compatible(a, b) → bool (compare structure trees)
- [x] Implement interpolate_style(a, b, t) → Style (lerp numeric params)
- [x] Implement color interpolation (hex RGB lerp)
- [x] Implement apply_style(client, style, source_image) → SVG string
- [x] Write unit tests for style extraction (19 tests)
- [x] Write unit tests for interpolation (numeric lerp, color lerp, edge cases)
- [x] Write unit tests for compatibility checking

## Phase 4: CustomTkinter GUI
- [x] Add gui optional dependency group (customtkinter, tkinterdnd2, CTkMenuBarPlus, Pillow, opencv-python)
- [x] Create gui/ package with __init__.py
- [x] Copy and adapt CTkRangeSlider widget into gui/widgets.py
- [x] Implement main App window with menu bar (File, Lines, Image, Video, Style, Export)
- [x] Implement Lines input tab (file list, drag-drop, +/−/✕ buttons)
- [x] Implement Images input tab (file list, preview, drag-drop)
- [x] Implement Video input tab (frame previews, range slider, frame count)
- [x] Implement Style/End Style picker panel (preview, file picker, clear)
- [x] Implement output bar (format dropdown, size dropdown, audio toggle, Export button)
- [x] Implement drag-drop registration for all tab areas
- [x] Implement menu→tab switching (File>Add Lines→Lines tab, Image>Add Images→Images tab, etc.)
- [x] Implement Lines tab disabling Style/End Style section
- [x] Implement export dialog (folder picker for SVG/PNG/JPG/LINES, file picker for MP4)
- [ ] Implement background processing thread with progress
- [ ] Wire up style engine for actual processing
- [x] Add vexy-lines-gui script entry point in pyproject.toml

## Phase 5: Enhanced CLI
- [x] Add style_transfer subcommand (--style, --end-style, --images, --output-dir, --format)
- [x] Add style_video subcommand (--style, --end-style, --input, --output, --start-frame, --end-frame)
- [x] Add batch_convert subcommand (--input-dir, --output-dir, --format for .lines→SVG/PNG/JPG)
- [x] Add gui subcommand (launches the CustomTkinter GUI)
- [x] Support --verbose and --json across all new subcommands
- [ ] Update video.py to use style engine instead of hardcoded fill params

## Phase 6: Testing & Documentation
- [x] Write tests/test_parser.py (parse, dataclasses, image extraction, fill mapping)
- [x] Write tests/test_style.py (extract, interpolate, compatible, apply)
- [x] Write tests/test_cli_new.py (info, extract, file-tree, batch-convert)
- [x] Write examples/parse_lines.py
- [x] Write examples/extract_images.py
- [x] Write examples/style_transfer.py
- [x] Write examples/style_interpolation.py
- [x] Create test.sh script
- [ ] Update README.md
- [x] Update CLAUDE.md (architecture section)
- [x] Update DEPENDENCIES.md
- [x] Update CHANGELOG.md for v4.0
- [x] Run full test suite, verify all pass (174 passing)
