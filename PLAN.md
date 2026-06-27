---
this_file: PLAN.md
---

# PLAN: vexy-lines-utils Maintenance

## Current State

`vexy-lines-utils` is a Python 3.11+ utility package for Vexy Lines. The implemented surface is:

- Pure-Python `.lines` parsing, metadata inspection, layer tree reporting, and source/preview extraction.
- Style extraction, compatibility checks, interpolation, and MCP-driven style application.
- TCP JSON-RPC MCP client for the Vexy Lines app.
- CustomTkinter GUI for lines/images/video workflows.
- Fire CLI covering parser, style, video, MCP, export, and GUI commands.
- Legacy macOS plist/AppleScript export pipeline for PDF/SVG batch export.

## Maintenance Priorities

1. Keep public docs aligned with `src/vexy_lines_utils/__main__.py`, `pyproject.toml`, and the exported symbols in `src/vexy_lines_utils/__init__.py`.
2. Keep parser/style behavior aligned with upstream `.lines` format changes, especially fill tags, source images, masks, mesh data, and image-filter chains.
3. Keep generated build artifacts and runtime caches out of the repo.
4. Prefer focused fixes and tests over broad rewrites.

## Verification Baseline

```bash
uvx hatch test
uvx hatch run lint:style
uvx hatch run lint:typing
```

For release-adjacent cleanup, also check:

```bash
git status --short --ignored
find . -type d \( -name dist -o -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) -print
```

## Future Work

- Split deprecated plist export docs from the newer MCP/style workflow docs if the package remains broad.
- Add CLI coverage for MCP image-filter commands if those are intended to be user-facing in this package.
- Decide whether `style-video --start-frame` should become functional or be removed from the public CLI.
- Consider consolidating this package with the newer split packages (`vexy-lines-py`, `vexy-lines-apy`, `vexy-lines-cli`, `vexy-lines-run`) if it is now legacy.
