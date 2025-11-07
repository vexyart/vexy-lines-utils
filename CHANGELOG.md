---
this_file: CHANGELOG.md
---

# Changelog

## [Unreleased] - 2025-11-07

### Added
- Comprehensive documentation of Vexy Lines application in README.md, including detailed explanation of all 12 fill algorithms
- Enhanced pyproject.toml with detailed classifiers, keywords, and inline documentation
- DEPENDENCIES.md with thorough explanation of each package choice and usage
- Python API documentation and examples in README
- Troubleshooting section with common issues and solutions
- Development workflow documentation and project structure guide

### Changed
- Expanded README.md from basic usage to comprehensive guide including:
  - Detailed Vexy Lines feature overview (12 fill types, layer system, mesh warping)
  - System requirements and installation instructions
  - Advanced usage examples and workflows
  - Python API documentation
  - Extensive troubleshooting guide
- Updated pyproject.toml metadata with more descriptive project information
- Enhanced package description to better communicate functionality

### Removed
- Deleted old/ folder containing legacy scripts (vexy-lines2pdf.py, vlbatch.md, vlum-*.md)
- Removed backup files (pyproject.toml.bak, vexy_lines_utils.py.backup)
- Cleaned up AI agent instruction files (AGENTS.md, GEMINI.md, LLXPRT.md, QWEN.md, AGENT.md)
- Removed macOS .DS_Store files

### Technical
- All 7 unit tests passing successfully
- Package structure follows modern Python standards
- Fire CLI implementation fully functional with dry-run mode
- PyXA bridge for macOS automation operational
- Window watcher state machine tested and working

## 2025-11-07

- replaced the placeholder module with a Fire-based CLI that automates Vexy Lines exports via PyXA and pyautogui, including dry-run support and structured logging
- added unit tests for discovery, window watching, stats tracking, and the dry-run exporter plus a pytest `conftest` to expose the `src` layout
- refreshed `pyproject.toml` dependencies/script entry, created proper package exports, and rewrote the README with detailed usage notes and background information
- recorded `uvx hatch test` run (7 tests passed) to validate the new functionality
