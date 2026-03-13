---
this_file: README.md
---

# Vexy Lines Utils

Export [Vexy Lines](https://www.vexy.art) `.lines` documents to PDF or SVG from the command line. No pointing, no clicking — just one command for a single file or an entire folder tree.

```bash
vexy-lines-utils export ~/Art/portrait.lines
vexy-lines-utils export ~/Projects/posters --format svg --verbose
```

Built for power users and studios who process artwork in bulk. The tool configures Vexy Lines through its preference plist, opens each document via AppleScript, triggers the native export, validates the output, and restores original preferences when done.

## About Vexy Lines

Vexy Lines is a macOS desktop application that transforms raster images — photos, illustrations, AI-generated art — into expressive vector artwork. It reads every pixel's brightness and builds vector strokes from it: dark areas produce thick lines, bright areas thin ones (or the reverse).

The application offers twelve fill algorithms, each interpreting your source image differently:

| Algorithm | Style |
|-----------|-------|
| **Linear** | Copper-plate engravings with parallel straight lines |
| **Wave** | Flowing curves that undulate across the image |
| **Radial** | Lines exploding outward from a centre point |
| **Circular** | Concentric rings emanating from the centre |
| **Spiral** | Continuous winding from centre to edge |
| **Halftone** | Newspaper-style dots scaled by brightness |
| **Trace** | Edge detection converting boundaries to paths |
| **Wireframe** | 3D-looking dimensional lattices |
| **Scribble** | Organic hand-drawn randomness |
| **Fractal** | Recursive mathematical patterns |
| **Text** | Typography-based painting |
| **Handmade** | Your own custom drawn strokes |

Professional features include a layer system with groups and masks, dynamic colour pulled from source images, 3D mesh warping, multiple source images per composition, and overlap control for woven effects. Projects save as `.lines` files that preserve the complete editing state.

More at [vexy.art](https://www.vexy.art) and [help.vexy.art](https://help.vexy.art).

## System Requirements

| Requirement | Detail |
|-------------|--------|
| **OS** | macOS 10.14+ (Mojave or later) |
| **Application** | [Vexy Lines](https://www.vexy.art) installed in `/Applications` |
| **Python** | 3.10 or newer |
| **Accessibility** | Terminal must have accessibility permissions (for AppleScript UI control) |

## Installation

### From PyPI

```bash
pip install vexy-lines-utils
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install vexy-lines-utils
```

### From Source

```bash
git clone https://github.com/vexyart/vexy-lines-utils.git
cd vexy-lines-utils
pip install -e .
```

### Accessibility Permissions

The tool drives Vexy Lines through AppleScript and needs accessibility access:

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Add your terminal application (Terminal.app, iTerm2, VS Code, etc.)
3. Restart the terminal after granting permissions

## Command-Line Interface

The package installs a `vexy-lines-utils` command with a single `export` subcommand:

```
vexy-lines-utils export INPUT [OPTIONS]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `input` | path | yes | Path to a `.lines` file or a folder (searched recursively) |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output` | path | — | Output directory or file path. Defaults to same directory as input. |
| `--format` | string | `pdf` | Export format: `pdf` or `svg` |
| `--verbose` | bool | `False` | Show detailed progress for each file |
| `--dry_run` | bool | `False` | List files that would be processed without touching anything |
| `--force` | bool | `False` | Overwrite existing exports instead of skipping them |
| `--say_summary` | bool | `False` | Announce completion summary via macOS text-to-speech |
| `--timeout_multiplier` | float | `1.0` | Scale all timeouts (range 0.1–10.0). Useful for slow machines. |
| `--max_retries` | int | `3` | Retry count for export attempts per file (range 0–10) |

### Examples

```bash
# Export a single file to PDF (default)
vexy-lines-utils export ~/Art/portrait.lines

# Export an entire folder to SVG
vexy-lines-utils export ~/Projects/posters --format svg

# Export with verbose output and overwrite existing files
vexy-lines-utils export ~/Clients/logos --verbose --force

# Dry run: see what would be processed
vexy-lines-utils export ~/Archive/2024 --dry_run --verbose

# Export to a specific output directory
vexy-lines-utils export ~/Art/batch --output ~/Exports/batch

# Slower machine — double all timeouts
vexy-lines-utils export ~/Art/heavy.lines --timeout_multiplier 2.0

# Voice announcement when a large batch finishes
vexy-lines-utils export ~/Projects --say_summary --verbose

# Export with detailed logging piped to a file
vexy-lines-utils export ~/problem-files/ --verbose 2>&1 | tee export.log
```

### Exit Behaviour

The exporter continues processing remaining files when an individual export fails. On completion, it prints (or returns) a summary:

```json
{
  "processed": 10,
  "success": 9,
  "skipped": 0,
  "failed": 1,
  "failures": [
    ["path/to/broken.lines", "Failed to open file"]
  ],
  "validation_failures": [],
  "dry_run": false,
  "total_time": 42.3,
  "average_time": 4.7
}
```

## How It Works

The v2.0.0 architecture replaced GUI dialog automation (PyXA, pyautogui-ng) with a plist-driven approach — faster, more reliable, and with fewer dependencies.

### Export Pipeline

```
┌────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Discovery  │────▶│ Plist Config │────▶│  App Automation   │
│             │     │              │     │                   │
│ find_lines_ │     │ PlistManager │     │ AppleScriptBridge │
│ files()     │     │ sets export  │     │ opens, triggers   │
│             │     │ preferences  │     │ export, closes    │
└────────────┘     └──────────────┘     └──────────────────┘
                                                │
                          ┌─────────────────────┘
                          ▼
                   ┌──────────────┐     ┌────────────┐
                   │  File Polling │────▶│ Validation  │
                   │              │     │             │
                   │ Wait for     │     │ validate_   │
                   │ stable size  │     │ pdf / svg   │
                   └──────────────┘     └────────────┘
```

**Step by step:**

1. **Discovery** — `find_lines_files()` resolves the input path. A single `.lines` file is taken directly; a directory is searched recursively with results sorted for deterministic ordering.

2. **Preference injection** — `PlistManager` (a context manager) quits Vexy Lines, snapshots its current preferences (`defaults export`), then writes export-specific settings via `defaults write` on the `com.vexy-art.lines` domain. This configures format, scale, antialiasing, and layer merging without any UI interaction.

3. **App activation** — `AppleScriptBridge` launches or activates Vexy Lines and waits for a window to appear via `WindowWatcher`, which polls the window title list at a configurable interval.

4. **Per-file processing** — For each `.lines` file:
   - Validate the file (exists, non-empty, < 500 MB, correct extension)
   - Skip if output already exists (unless `--force`)
   - Open the file via `open -a "Vexy Lines"`
   - Wait for a window containing the document name
   - Trigger `File → Export PDF File` (or `Export SVG File`) through AppleScript menu clicks, with progressive retry delays (0.5s → 2.0s → 5.0s)
   - Poll for the exported file to appear and reach a stable size
   - Validate the output (PDF header check or SVG tag check)
   - Optionally move to the output directory
   - Close the document window (Cmd+W)

5. **Cleanup** — `PlistManager.__exit__` restores the original preference snapshot (or removes the domain entirely if none existed). `InterruptHandler` allows graceful Ctrl+C: a first interrupt flags a stop, a second terminates immediately.

### Interrupt Handling

Press **Ctrl+C** once during a batch to finish the current file and stop cleanly. Press it again to terminate immediately. The preference snapshot is always restored via the context manager, so Vexy Lines settings are never left in a modified state.

## Python API

For integration into scripts or larger pipelines:

```python
from pathlib import Path
from vexy_lines_utils import VexyLinesExporter, ExportConfig

# Configure export behaviour
config = ExportConfig(
    format="pdf",              # "pdf" or "svg"
    poll_interval=0.2,         # Window-check frequency (seconds)
    wait_for_app=20.0,         # App launch timeout
    wait_for_file=20.0,        # File open timeout
    post_action_delay=0.4,     # Pause after UI actions
    timeout_multiplier=1.0,    # Scale all timeouts
    max_retries=3,             # Export attempts per file
)

# Create exporter
exporter = VexyLinesExporter(config=config, dry_run=False, force=True)

# Run export — returns ExportStats
stats = exporter.export(
    input_path=Path("~/Documents/vexy-projects"),
    output_path=Path("~/Exports"),
)

# Inspect results
print(stats.human_summary())
print(f"Success rate: {stats.success}/{stats.processed}")

for path, reason in stats.failures:
    print(f"  Failed: {path} — {reason}")
```

### Key Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `VexyLinesExporter` | `exporter` | Top-level orchestrator. Drives the full export pipeline. |
| `ExportConfig` | `core.config` | Dataclass holding format, timeouts, retry settings. Validates on init. |
| `ExportStats` | `core.stats` | Accumulates per-file results: success, skip, failure, timing. |
| `PlistManager` | `core.plist` | Context manager. Injects and restores Vexy Lines preferences. |
| `AppleScriptBridge` | `automation.bridges` | Runs `osascript` to activate, open, click menus, close windows. |
| `WindowWatcher` | `automation.window_watcher` | Polls window titles with configurable timeout and interval. |
| `InterruptHandler` | `utils.interrupt` | Catches SIGINT for graceful shutdown mid-batch. |
| `AutomationError` | `core.errors` | Base error with error codes and recovery suggestions. |

### Public Functions

| Function | Module | Purpose |
|----------|--------|---------|
| `find_lines_files(path)` | `utils.file_utils` | Returns sorted list of `.lines` files from a file or directory |
| `validate_lines_file(path)` | `utils.file_utils` | Checks file exists, has `.lines` extension, non-empty, < 500 MB |
| `validate_pdf(path)` | `utils.file_utils` | Checks file exists, ≥ 1 KB, starts with `%PDF-` |
| `validate_svg(path)` | `utils.file_utils` | Checks file exists, non-empty, starts with `<?xml` or `<svg` |
| `validate_export(path, fmt)` | `utils.file_utils` | Dispatches to `validate_pdf` or `validate_svg` |
| `speak(text)` | `utils.system` | macOS `say` command for voice feedback |

### Error Codes

`AutomationError` carries an `error_code` string. Each code maps to a human-readable recovery suggestion via `get_error_suggestion()`:

| Code | Meaning |
|------|---------|
| `APP_NOT_FOUND` | Vexy Lines is not installed or not in `/Applications` |
| `OPEN_FAILED` | Could not open the `.lines` file |
| `WINDOW_TIMEOUT` | Expected window did not appear in time |
| `EXPORT_MENU_TIMEOUT` | Export menu item could not be clicked |
| `SAVE_DIALOG_TIMEOUT` | Save dialog did not appear |
| `EXPORT_TIMEOUT` | Exported file did not materialise |
| `INVALID_PDF` | Output file failed PDF validation |
| `FILE_INVALID` | Input `.lines` file is malformed or too large |
| `NO_FILES` | No `.lines` files found at the given path |
| `USER_INTERRUPT` | Export cancelled by Ctrl+C |
| `PLIST_ERROR` | Failed to read or write preference plist |

## Development

### Project Structure

```
vexy-lines-utils/
├── src/vexy_lines_utils/
│   ├── __init__.py              # Public API exports
│   ├── __main__.py              # Fire CLI entry point (VexyLinesCLI)
│   ├── __version__.py           # Auto-generated version (hatch-vcs)
│   ├── py.typed                 # PEP 561 type marker
│   ├── exporter.py              # VexyLinesExporter — main orchestrator
│   ├── core/
│   │   ├── config.py            # ExportConfig dataclass
│   │   ├── errors.py            # AutomationError, error codes, suggestions
│   │   ├── plist.py             # PlistManager — preference injection
│   │   └── stats.py             # ExportStats — result tracking
│   ├── automation/
│   │   ├── bridges.py           # AppleScriptBridge, ApplicationBridge protocol
│   │   └── window_watcher.py    # WindowWatcher — poll-based title matching
│   └── utils/
│       ├── file_utils.py        # File discovery and validation
│       ├── interrupt.py         # SIGINT handler for graceful shutdown
│       └── system.py            # macOS text-to-speech wrapper
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_package.py          # 79 tests covering all modules
│   └── fixtures/
│       └── mock_pyxa.py         # Mock for macOS-specific dependencies
├── pyproject.toml               # Hatch build config, Ruff, mypy, pytest
└── README.md
```

### Setup

```bash
git clone https://github.com/vexyart/vexy-lines-utils.git
cd vexy-lines-utils

# Option A: uv (recommended)
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev,test]"

# Option B: pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,test]"
```

### Common Commands

```bash
# Run tests
uvx hatch test

# Run tests with coverage
uvx hatch run test:test-cov

# Format code
uvx hatch fmt

# Lint and type-check
uvx hatch run lint:style
uvx hatch run lint:typing
```

### Dependencies

**Runtime** (intentionally minimal):

| Package | Purpose |
|---------|---------|
| [fire](https://github.com/google/python-fire) ≥ 0.6.0 | CLI framework — zero-boilerplate command generation |
| [loguru](https://github.com/Delgan/loguru) ≥ 0.7.2 | Structured logging with colour output |

**Removed in v2.0.0**: `mac-pyxa`, `pyautogui-ng`, `pyperclip` — replaced by native `osascript` + plist manipulation.

### Testing

79 tests run in ~1.2 seconds, covering:

- File discovery and recursive `.lines` search
- Input validation (extension, size, emptiness)
- Output validation (PDF header, SVG tags)
- `ExportConfig` validation and edge cases
- `ExportStats` tracking and summary generation
- `PlistManager` snapshot/restore lifecycle
- `WindowWatcher` polling and timeout behaviour
- `InterruptHandler` SIGINT flow
- Error code → suggestion mapping
- Dry-run mode (no UI interaction)
- CLI argument parsing

Tests mock macOS-specific APIs so they run on any platform in CI.

## Troubleshooting

### "Vexy Lines is not installed"

- Verify `Vexy Lines.app` is in `/Applications`
- Try opening it manually first
- Check for license or trial expiration

### Export timing out

- Increase timeouts: `--timeout_multiplier 2.0` or `3.0`
- Check that Vexy Lines has no modal dialogs blocking
- Ensure no other system dialogs are in the way
- Try with a single file first to isolate the issue

### "Accessibility permissions required"

- Open **System Settings** → **Privacy & Security** → **Accessibility**
- Add your terminal application
- Restart the terminal after granting permissions
- If using an IDE (VS Code, PyCharm), the IDE itself needs permission

### Exported files not appearing

- Check write permissions in the output directory
- Verify the source `.lines` files are not corrupted (try opening manually)
- Run with `--verbose` to see exactly where the process stalls
- Check Console.app for `osascript` errors

### Preferences left in a modified state

This should not happen — `PlistManager` always restores on exit, including after Ctrl+C or exceptions. If it does happen:

```bash
# Remove the injected preferences entirely
defaults delete com.vexy-art.lines

# Or re-launch Vexy Lines normally — it recreates defaults on start
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full release history.

### v2.0.0 Highlights

Complete rewrite from GUI dialog automation to plist-driven export. Removed three macOS GUI dependencies (`mac-pyxa`, `pyautogui-ng`, `pyperclip`), added SVG export support, preference snapshot/restore, progressive retry, file-size polling, and comprehensive output validation. 79 tests in 1.2 seconds.

## About

**vexy-lines-utils** is developed by [FontLab Ltd.](https://www.fontlab.com), creators of [Vexy Lines](https://www.vexy.art) and industry-standard font editing software.

- [Vexy Lines](https://www.vexy.art) — the application
- [Documentation](https://help.vexy.art) — Vexy Lines user guide
- [Support](https://support.vexy.art) — FontLab support
- [Issues](https://github.com/vexyart/vexy-lines-utils/issues) — bug reports and feature requests

## License

MIT — see [LICENSE](LICENSE) for details.
