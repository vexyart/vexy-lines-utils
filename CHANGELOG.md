---
this_file: CHANGELOG.md
---

# Changelog

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
