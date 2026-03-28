---
this_file: CHANGELOG.md
---

# Changelog

## [3.0.0-dev] - 2026-03-27

### Added

- **MCP client module** (`mcp/`): TCP JSON-RPC 2.0 client for the Vexy Lines embedded MCP server
  - `MCPClient` context manager with automatic connect/handshake/disconnect
  - Typed Python methods for all 25 MCP tools (document ops, structure, fills, masks, transforms, rendering)
  - Dataclass responses: `DocumentInfo`, `LayerNode`, `NewDocumentResult`, `RenderStatus`
  - Zero new runtime dependencies (stdlib `socket` + `json`)
- **6 new CLI subcommands**: `mcp_status`, `tree`, `new_document`, `open`, `add_fill`, `render`
  - `--json_output` flag for machine-readable tree output
  - Graceful error handling when MCP server is unreachable
- **4 example scripts** in `examples/`:
  - `batch_export.py` — existing export pipeline demo
  - `mcp_hello.py` — connect and print document info / layer tree
  - `mcp_create_artwork.py` — full workflow: create document, add fills, render, export
  - `mcp_masks.py` — SVG path masks on fill layers
- **Integration test** (`_private/mcp/test_integration.py`): interactive MCPClient test against running app
- 42 new unit tests (34 MCP client + 8 CLI subcommands)

### Changed (breaking)

- **Preference domain** updated from `com.vexy-art.lines` to `com.fontlab.vexy-lines` to match current Vexy Lines app

### Fixed

- Test assertion in `test_applies_export_prefs_for_pdf`: expected `"true"` but `EXPORT_PREFERENCES` values are integers

### Technical

- **Test count:** 124 tests passing (82 existing + 42 new)
- **Test duration:** ~3.3s
- **New files:** `src/vexy_lines_utils/mcp/{__init__,client,types}.py`, `tests/test_mcp_client.py`, `examples/{batch_export,mcp_hello,mcp_create_artwork,mcp_masks}.py`

## [2.0.0] - 2026-03-13

### Changed (breaking)

- **Complete rewrite** using Vexy Lines' new dialog-less plist-driven export
- CLI: `export TARGET` replaces old positional + `--format`/`--output` flags; removed `--enhanced`
- Default format is `pdf`; pass `--format svg` for SVG export
- Minimum retry count is now `0` (no retries); was `1`

### Added

- `core/plist.py`: `PlistManager` context manager — quits app, edits plist atomically, restores on exit
- `core/config.py`: `ExportConfig` with validated format, timeout, and retry constants
- `exporter.py`: `VexyLinesExporter` with file-polling export detection and folder iteration
- `automation/bridges.py`: `AppleScriptBridge` (PyXA removed)

### Removed

- Dependencies: `mac-pyxa`, `pyautogui-ng`, `pyperclip` — no longer needed
- `automation/ui_actions.py`, `strategies/`, `exporters/enhanced.py`, `exporters/standard.py`

### Fixed

- `FORMAT_CODES` values are strings (`"pdf"`, `"svg"`) not integers
- `PlistManager.__enter__` annotated as `Self` (PYI034)
- `plist.py`: `Path.replace`/`Path.unlink` instead of `os.*`; `import os` removed
- `bridges.py`: `# noqa: S603/S607` placement corrected
- Test suite: all ruff violations resolved — PT012, ARG001, SIM117, S108, RUF100

### Technical

- **Test count:** 79/79 passing
- **Code quality:** ruff 0 errors across `src/` and `tests/`

## [2.0.0] - 2026-03-13

### Breaking Changes — Dialog-less Export Architecture

Complete rewrite from GUI dialog automation to plist-driven export.

- **Removed** `mac-pyxa`, `pyautogui-ng`, `pyperclip` dependencies entirely
- **Removed** `AutomationConfig`, `EnhancedAutomationConfig`, `UIActions`, `PyXABridge`, `MenuStrategy`, `DialogStrategy`, `BaseExporter` classes
- **Removed** `strategies/` and `exporters/` module directories
- **Removed** `--enhanced` CLI flag and `test-strategies` command
- **Renamed** CLI positional arg `target` → `input`
- **Changed** `VexyLinesExporter` constructor from `(dry_run, ui_actions)` to `(config, *, dry_run)`
- **Changed** `WindowWatcher` error codes: `"TIMEOUT"` → `"WINDOW_TIMEOUT"`, `"APP_NOT_READY"` → `"APP_NOT_FOUND"`

### Added

- `ExportConfig` dataclass replaces `AutomationConfig` — validates format, timeout_multiplier, max_retries, app_name
- `PlistManager` context manager — quits app, writes export preferences to plist atomically, restores on exit
- `AppleScriptBridge` methods: `quit_app()`, `is_running()`, `open_file()`, `close_front_window()`
- `validate_svg()` function — checks SVG content header (`<?xml` or `<svg`)
- `validate_export()` dispatcher for pdf/svg validation
- `expected_export_path()` and `resolve_output_path()` utilities
- `PLIST_ERROR` error code with recovery suggestion
- SVG export format support (`--format svg`)
- File polling for export completion (stable size detection)
- `InterruptHandler` signal handling preserved throughout retry loop

### Technical

- **Test count:** 79 tests passing (up from 42)
- **Test duration:** 1.15s (down from 4.09s — no subprocess calls in tests)
- **Dependencies removed:** mac-pyxa, pyautogui-ng, pyperclip
- **Code quality:** ruff compliant

## [1.0.7] - 2025-11-07

### UX & Quality Improvements
- **Progress indicators**: Real-time batch export progress with `[X/Y] Processing filename` format
- **ETA calculation**: Estimates time remaining based on average export time
- **Batch summary**: Final report with total time and success rate
- **Error suggestions**: Contextual recovery tips for all 10 error codes with actionable steps
- **Better error messages**: `get_error_suggestion()` and `format_error_with_context()` helpers

### Added
- Progress counter shows current file number out of total (e.g., "[3/10]")
- Total file count logged at batch start: "Found X .lines file(s) to process"
- ETA displayed after first file completes (shows minutes and seconds)
- Final summary log: "Batch complete: summary, total time Xs"
- Error recovery suggestions for: APP_NOT_FOUND, OPEN_FAILED, WINDOW_TIMEOUT, EXPORT_MENU_TIMEOUT, SAVE_DIALOG_TIMEOUT, EXPORT_TIMEOUT, INVALID_PDF, FILE_INVALID, NO_FILES, USER_INTERRUPT
- Each error suggestion includes 3 numbered troubleshooting steps
- Exported `get_error_suggestion()` and `format_error_with_context()` from core package

### Technical
- **Test count:** 42 tests passing (up from 40)
- **New tests:**
  - `test_progress_indicators_in_export()` - Verifies progress tracking
  - `test_error_suggestions()` - Validates error suggestion helpers
- **Test duration:** 4.09s (stable performance)
- **Code quality:** 100% ruff compliance maintained

## [1.0.6] - 2025-11-07

### New Features
- **Auto-close final document**: After batch export completes and summary is printed, automatically close the last open .lines file in Vexy Lines
- **Smart close detection**: Checks if any document is open before attempting to close, avoiding unnecessary operations
- **Graceful error handling**: Final document close failures log warnings but don't fail the batch export

### Implementation Details
- Added `close_final_document()` method to `BaseExporter` class
- Integrated into CLI export workflow after summary printing/speaking
- Handles unsaved changes dialogs with proper keyboard navigation (Tab Tab Enter to "Don't Save")
- Respects dry-run mode (skips close operation)

### Technical
- **Test count:** 41 tests passing
- **Test duration:** ~4.87s
- **Code quality:** 100% ruff compliance maintained

## [1.0.5] - 2025-11-07

### Code Quality & Linting Improvements
- **Zero ruff warnings achieved**: Fixed all 11 remaining linting issues
- **Magic number extraction**: Added module-level validation constants (`MIN_TIMEOUT_MULTIPLIER`, `MAX_TIMEOUT_MULTIPLIER`, `MIN_RETRIES`, `MAX_RETRIES`)
- **Improved maintainability**: Configuration validation now uses named constants instead of magic values
- **Line length compliance**: Refactored long error messages for better readability

### Fixed
- PLC0415: Added proper noqa comments for intentional function-level imports in tests (5 locations)
- S603: Added noqa for legitimate subprocess.run() security exceptions (2 locations)
- S607: Added noqa for partial executable path in osascript calls
- PLR2004: Extracted all magic numbers in config validation to named constants
- E501: Fixed line-too-long error by splitting error messages across multiple lines

### Technical
- **Test count:** 40 tests passing (up from 39)
- **Test duration:** 4.10s (within acceptable range)
- **Code quality:** 100% ruff compliance with appropriate noqa annotations
- **Maintainability score:** Improved with constant extraction and better formatting

## [1.0.3] - 2025-11-07

### Critical Bug Fixes
- **Fixed AttributeError** in `EnhancedVexyLinesExporter` initialization caused by read-only property override
- **Smart unsaved changes handling**: Automatically detects `*` in window title after export and handles "Unsaved Changes" dialog with proper Tab navigation to Discard button
- **Zero ruff warnings**: Fixed all 38 linting issues including security, code quality, and style warnings

### Major Refactoring: Modular Architecture
- **Complete restructuring** from 2 monolithic files (~1,162 lines) into 15+ focused modules
- **New module organization:**
  - `core/`: Configuration classes, errors, and statistics
  - `utils/`: File operations, interrupt handling, system utilities
  - `automation/`: Application bridges (PyXA, AppleScript), UI actions, window watching
  - `strategies/`: Smart menu triggering and dialog handling with multiple fallbacks
  - `exporters/`: Base, standard, and enhanced exporters
  - `cli.py`: Command-line interface with Fire
- **100% backward compatibility** - all existing APIs preserved
- **Enhanced exporter** (`EnhancedVexyLinesExporter`) with multiple automation strategies
- **Strategy pattern implementation** for flexible fallback handling
- **AppleScript bridge** as alternative to PyXA for broader compatibility
- **Interrupt handler** for graceful shutdown on Ctrl+C
- **Smart strategies** for menu triggering (keyboard/AppleScript/PyXA)
- **Smart dialog handling** with 4 navigation strategies
- **CLI enhancements:**
  - `--enhanced` flag to use new smart strategies
  - `test-strategies` command to check system capabilities
- **Test expansion:** 39 tests now passing (up from 23)

### Added
- Comprehensive documentation of Vexy Lines application in README.md, including detailed explanation of all 12 fill algorithms
- Enhanced pyproject.toml with detailed classifiers, keywords, and inline documentation
- DEPENDENCIES.md with thorough explanation of each package choice and usage
- Python API documentation and examples in README
- Troubleshooting section with common issues and solutions
- Development workflow documentation and project structure guide
- Smart skip logic: exporter now skips .lines files that already have corresponding .pdf files
- Three-tiered folder navigation strategy with automatic fallback for robustness
- UI state diagnostics in WindowWatcher for better error debugging
- Detailed error logging with current window state on timeouts
- **PDF Validation:** `validate_pdf()` function with three-tier validation:
  - Size validation (>1KB minimum, <500MB warning)
  - PDF magic bytes verification (`%PDF-` header)
  - File accessibility and integrity checks
- 8 new unit tests covering navigation strategies and PDF validation

### Changed
- Expanded README.md from basic usage to comprehensive guide including:
  - Detailed Vexy Lines feature overview (12 fill types, layer system, mesh warping)
  - System requirements and installation instructions
  - Advanced usage examples and workflows
  - Python API documentation
  - Extensive troubleshooting guide
- Updated pyproject.toml metadata with more descriptive project information
- Enhanced package description to better communicate functionality
- Exporter now checks for existing PDF files before processing, avoiding redundant conversions
- Removed unnecessary PDF deletion logic in `_process_file` method

### Fixed
- **Critical:** Logging format strings now properly interpolate values (f-strings instead of % formatting)
- Proper exception chaining with `from e` for better error tracebacks
- Extracted magic numbers to named constants for code quality

### Improved
- **Retry Logic Intelligence:** Save dialog navigation now tries three strategies sequentially:
  1. Command-Shift-G (Go to Folder) - primary method
  2. Direct path input - alternative when navigation fails
  3. Filename-only - fallback for recovery
- Enhanced retry diagnostics with UI state logging before/after failures
- Better error messages including current window titles for debugging
- Improved code quality: eliminated all Ruff linting warnings

### Removed
- Deleted old/ folder containing legacy scripts (vexy-lines2pdf.py, vlbatch.md, vlum-*.md)
- Removed backup files (pyproject.toml.bak, vexy_lines_utils.py.backup)
- Cleaned up AI agent instruction files (AGENTS.md, GEMINI.md, LLXPRT.md, QWEN.md, AGENT.md)
- Removed macOS .DS_Store files

### Technical
- **All 23 unit tests passing successfully** (up from 15)
  - 3 new tests for UI state diagnostics and navigation strategies
  - 5 new tests for PDF validation (valid, missing, too small, invalid header, large file)
- Test coverage: 50% (reasonable for UI automation code)
- Zero Ruff linting warnings
- Package structure follows modern Python standards
- Fire CLI implementation fully functional with dry-run mode
- PyXA bridge for macOS automation operational
- Window watcher state machine tested and working with enhanced diagnostics
- PDF validation catches corrupted/incomplete exports automatically

## 2025-11-07

- replaced the placeholder module with a Fire-based CLI that automates Vexy Lines exports via PyXA and pyautogui, including dry-run support and structured logging
- added unit tests for discovery, window watching, stats tracking, and the dry-run exporter plus a pytest `conftest` to expose the `src` layout
- refreshed `pyproject.toml` dependencies/script entry, created proper package exports, and rewrote the README with detailed usage notes and background information
- recorded `uvx hatch test` run (7 tests passed) to validate the new functionality
