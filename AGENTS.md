# AGENTS.md

Guidance for agents working in `vexy-lines-utils`.

## Current Scope

`vexy-lines-utils` is no longer an exporter-only package. It contains:

- A pure-Python `.lines` XML parser and embedded image extractors.
- A style engine for extracting, applying, and interpolating `.lines` fill structures.
- A TCP JSON-RPC MCP client for the Vexy Lines app.
- A macOS plist/AppleScript batch exporter for PDF/SVG output.
- A CustomTkinter GUI and Fire-based CLI.

Parser commands work without the app. MCP, style transfer, GUI processing, and plist export require the Vexy Lines desktop app. The plist export pipeline is macOS-only.

## Commands

```bash
uv sync
uvx hatch test
uvx hatch run lint:style
uvx hatch run lint:typing
uvx hatch fmt
./build.sh
```

The full cleanup/test pipeline used in this workspace is:

```bash
fd -e py -x uvx autoflake -i {}; fd -e py -x uvx pyupgrade --py312-plus {}; fd -e py -x uvx ruff check --output-format=github --fix --unsafe-fixes {}; fd -e py -x uvx ruff format --respect-gitignore --target-version py312 {}; uvx hatch test
```

## CLI Surface

Installed scripts:

- `vexy-lines-utils` -> `vexy_lines_utils.__main__:main`
- `vexy-lines-run` -> `vexy_lines_utils.gui:launch`

Main Fire commands:

- Parser, no app: `info`, `file-tree`, `extract-source`, `extract-preview`, `batch-convert`
- Style/MCP: `style-transfer`, `style-video`, `mcp-status`, `tree`, `new-document`, `open`, `add-fill`, `render`
- macOS export: `export`
- GUI: `gui`

Running `vexy-lines-utils` without a subcommand launches the GUI if GUI dependencies are installed.

## Module Map

| Module | Role |
|---|---|
| `parser.py` | `.lines` XML parsing, source/preview extraction, image-filter chain parsing |
| `style.py` | Style extraction, compatibility checks, interpolation, MCP application |
| `mcp/` | MCP TCP client and typed response dataclasses |
| `exporter.py` | PDF/SVG export loop |
| `core/config.py` | Export format, timeout, and retry validation |
| `core/plist.py` | Preference snapshot, injection, and restore |
| `automation/` | AppleScript bridge and window title polling |
| `gui/` | CustomTkinter desktop workflow |
| `video.py` | Video probing, frame extraction/rasterization/assembly |
| `__main__.py` | Fire CLI entry point |

## Conventions

- `this_file` comments are relative to this package root.
- Keep public docs aligned with `pyproject.toml` and the actual Fire methods in `src/vexy_lines_utils/__main__.py`.
- The project requires Python 3.11 or newer.
- `hatch-vcs` generates `src/vexy_lines_utils/__version__.py`; do not edit generated version files.
- Keep generated artifacts out of commits: `dist/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `.coverage`, and generated `_version.py`/`__version__.py`.

## Export Pipeline Notes

The legacy `export` command supports `pdf` and `svg` here. It quits the app, writes export preferences with `defaults`, relaunches the app, opens each `.lines` file, triggers the app's export menu item through AppleScript, waits for output, and restores preferences.

Do not document PNG support for this package's plist exporter unless `core/config.py` is updated. PNG export is supported in the newer `vexy-lines-cli` package.
