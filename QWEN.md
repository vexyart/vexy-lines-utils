# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`vexy-lines-utils` is a macOS-only CLI tool that batch-exports Vexy Lines `.lines` vector art documents to PDF or SVG. It drives the Vexy Lines app headlessly via AppleScript and macOS preference plist injection — no GUI dialog automation.

**Scope in one sentence:** Export `.lines` files to PDF/SVG from the command line via plist configuration and AppleScript automation.

## Commands

```bash
# Run tests (79 tests, ~1.2s)
uvx hatch test

# Run tests with coverage
uvx hatch run test:test-cov

# Lint + format
uvx hatch fmt

# Lint check + type check
uvx hatch run lint:style
uvx hatch run lint:typing

# Full /test pipeline (autoflake, pyupgrade, ruff, then tests)
fd -e py -x uvx autoflake -i {}; fd -e py -x uvx pyupgrade --py312-plus {}; fd -e py -x uvx ruff check --output-format=github --fix --unsafe-fixes {}; fd -e py -x uvx ruff format --respect-gitignore --target-version py312 {}; uvx hatch test;

# Build + publish (build.sh also generates llms.txt, bumps version via gitnextver)
./build.sh
```

## Architecture

The export pipeline has five stages, each owned by a distinct module:

```
Discovery → Plist Injection → App Activation → Per-File Export Loop → Cleanup
```

### Module Map

| Module | Class/Function | Role |
|--------|---------------|------|
| `exporter.py` | `VexyLinesExporter` | Top-level orchestrator. Owns the export loop and coordinates all other modules. |
| `core/config.py` | `ExportConfig` | Dataclass with format, timeouts, retry settings. Validates on init. `scale_timeout()` applies the multiplier. |
| `core/plist.py` | `PlistManager` | Context manager. Snapshots Vexy Lines prefs (`defaults export`), injects export settings (`defaults write` on `com.vexy-art.lines`), restores on exit. |
| `core/stats.py` | `ExportStats` | Accumulator for success/skip/failure counts, timing, and summary generation. |
| `core/errors.py` | `AutomationError` | Error with `error_code` string. `get_error_suggestion()` maps codes to recovery hints. |
| `automation/bridges.py` | `AppleScriptBridge` | Runs `osascript` commands: activate app, open file, click menu items, close windows, quit. Implements `ApplicationBridge` protocol. |
| `automation/window_watcher.py` | `WindowWatcher` | Polls window title list at intervals. `wait_for_any()` and `wait_for_contains()` with configurable timeout. |
| `utils/file_utils.py` | `find_lines_files`, `validate_*` | File discovery (recursive `.lines` search), input validation (extension/size/emptiness), output validation (PDF header/SVG tags). |
| `utils/interrupt.py` | `InterruptHandler` | SIGINT handler. First Ctrl+C flags graceful stop, second terminates. |
| `utils/system.py` | `speak()` | macOS `say` command wrapper for voice feedback. |
| `__main__.py` | `VexyLinesCLI` | Fire CLI entry point. Single `export` subcommand. |

### Key Design Decisions

- **Plist-driven, not dialog-driven.** v2.0 replaced PyXA/pyautogui GUI automation with `defaults write` on the app's preference domain. The app reads export prefs on launch, so we quit → inject → relaunch → trigger menu item. No save dialogs involved.
- **Progressive retry.** Export attempts use escalating delays (0.5s → 2.0s → 5.0s) because the app needs variable time to render before the menu export works.
- **File-size polling.** After triggering export, we poll the output file until its size stabilises across 2 consecutive checks (not just "file exists").
- **Preference snapshot/restore.** `PlistManager` is a context manager that always restores original prefs, even after exceptions or Ctrl+C.

## Testing

All tests live in `tests/test_package.py` (single file, 79 tests). Tests mock all macOS-specific APIs (`subprocess.run` for `osascript`/`defaults`, `Path.exists`, `Path.stat`) so they run on any platform.

Key fixtures are in `tests/fixtures/mock_pyxa.py`. The `conftest.py` just adds `src/` to `sys.path`.

Test naming convention: `test_function_name_when_condition_then_result`.

## Project Conventions

- **`this_file` tracking:** Every source file has a `# this_file: <relative-path>` comment near the top. Update when moving files.
- **Absolute imports only.** Ruff enforces `ban-relative-imports = 'all'`.
- **Version from git tags.** `hatch-vcs` generates `__version__.py` from git tags. No manual version bumps.
- **Line length:** 120 characters (Ruff config).
- **Target Python:** 3.10+ (type hints use `X | Y` union syntax, `from __future__ import annotations`).
- **Runtime deps are minimal:** only `fire` (CLI) and `loguru` (logging). Intentional — previous versions had heavy macOS GUI deps that were removed in v2.0.

## Entry Point

```
pyproject.toml [project.scripts] → vexy_lines_utils.__main__:main → fire.Fire(VexyLinesCLI)
```

The CLI has one subcommand: `vexy-lines-utils export INPUT [OPTIONS]`.

## Files to Maintain

| File | Purpose |
|------|---------|
| `WORK.md` | Current work progress and test results |
| `CHANGELOG.md` | Release notes (accumulative) |
| `PLAN.md` | Future goals and detailed plans |
| `TODO.md` | Flat `- []` task list mirroring PLAN.md |
| `DEPENDENCIES.md` | Package list with rationale |
