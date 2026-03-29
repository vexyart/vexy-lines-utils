---
this_file: WORK.md
---

# Work Progress: v4.0 — .lines Parser, Style Engine, GUI & CLI

## Session: 2026-03-30

### Completed

**Phase 1: .lines Parser** — `src/vexy_lines_utils/parser.py` (691 lines)
- 14 fill types mapped from XML tags to human-readable names
- Full recursive parsing of Objects tree (groups, layers, fills)
- Source image extraction (base64 → zlib → JPEG) and preview (base64 → PNG)
- Typed dataclasses: LinesDocument, GroupInfo, LayerInfo, FillNode, FillParams, DocumentProps, MaskInfo
- 21 unit tests passing

**Phase 2: App-less Image Extraction CLI**
- `info` — shows .lines metadata (caption, DPI, dimensions, layers, fills)
- `file_tree` — prints layer tree from file (no MCP needed)
- `extract_source` / `extract_preview` — saves embedded images
- `batch_convert` — batch extract from directory

**Phase 3: Style Engine** — `src/vexy_lines_utils/style.py` (493 lines)
- `extract_style()` — pulls group→layer→fill structure
- `styles_compatible()` — checks matching tree structures
- `interpolate_style()` — linear interpolation of numeric params + color lerp
- `apply_style()` — applies style via MCP
- 19 unit tests passing

**Phase 4: GUI** — `src/vexy_lines_utils/gui/` (3 files, ~2400 lines)
- Lines / Images / Video input tabs with drag-and-drop
- Style / End Style picker panels with .lines preview
- Lines tab disables style panels
- Output bar: SVG/PNG/JPG/MP4/LINES format, size, audio toggle, Export button
- `vexy-lines-gui` entry point

**Phase 5: Enhanced CLI** — `src/vexy_lines_utils/__main__.py` (720 lines)
- 8 new subcommands added (info, file_tree, extract_source, extract_preview, style_transfer, style_video, batch_convert, gui)
- Total 15 CLI subcommands

**Phase 6: Testing & Documentation**
- 174 tests passing (124 original + 21 parser + 19 style + 10 CLI)
- 4 functional examples created
- test.sh script created
- CHANGELOG, DEPENDENCIES, CLAUDE.md, TODO.md updated
- pyproject.toml updated with [gui] and [images] optional extras

### Test Results

```
174 passed in 3.70s
```

### Remaining

- Wire up GUI export to actual style engine processing
- Update video.py to use style engine for per-frame parameters
- Update README.md with v4.0 features
