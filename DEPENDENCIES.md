---
this_file: DEPENDENCIES.md
---

# Dependencies

## Runtime Dependencies

### fire (>=0.6.0)
- **Purpose**: Command-line interface framework
- **Why chosen**: Google's Fire automatically generates CLIs from Python objects with minimal boilerplate. Maps class methods to shell commands without manual argparse configuration.
- **Usage**: Powers the `vexy-lines export` command and handles all argument parsing

### loguru (>=0.7.2)
- **Purpose**: Structured logging with automatic colors
- **Why chosen**: Zero-config logger that's cleaner than standard logging for CLI tools. Provides clear visual feedback during batch operations with colored output.
- **Usage**: All status messages, progress tracking, error reporting, and verbose mode output

### mac-pyxa (>=0.3.0)
- **Purpose**: macOS application automation via AppleScript bridges
- **Why chosen**: The only Python package providing direct access to macOS application scripting without subprocess calls. Essential for reliable menu automation.
- **Usage**: Launches Vexy Lines, clicks File menu items (Export/Close), reads window titles for state tracking

### pyautogui-ng (>=0.0.4)
- **Purpose**: Keyboard and mouse automation
- **Why chosen**: Fork of pyautogui with better macOS compatibility and active maintenance. Handles GUI interactions that PyXA can't reach (dialog boxes).
- **Usage**: Navigates save dialogs with keyboard shortcuts (Cmd+Shift+G), types filenames, presses Enter to confirm

### pyperclip (>=1.9.0)
- **Purpose**: Cross-platform clipboard operations
- **Why chosen**: Simple and reliable clipboard access. More robust than pyautogui's clipboard functions for path pasting on macOS.
- **Usage**: Copies folder paths and filenames to clipboard for pasting into save dialogs

## Development Dependencies

### Testing
- **pytest** (>=8.3.4): Test framework with fixtures and parametrization
- **pytest-cov** (>=6.0.0): Coverage reporting integration
- **pytest-xdist** (>=3.6.1): Parallel test execution for faster runs
- **coverage[toml]** (>=7.6.12): Code coverage measurement

### Code Quality
- **ruff** (>=0.9.7): Fast all-in-one Python linter/formatter (replaces black, isort, flake8, and more)
- **mypy** (>=1.15.0): Static type checking for early error detection
- **pre-commit** (>=4.1.0): Git hook framework for automated checks
- **pyupgrade** (>=3.19.1): Automatically modernizes Python syntax for newer versions
- **absolufy-imports** (>=0.3.1): Converts relative imports to absolute for clarity

### Documentation
- **sphinx** (>=7.2.6): Documentation generator from docstrings
- **sphinx-rtd-theme** (>=2.0.0): Clean ReadTheDocs theme
- **sphinx-autodoc-typehints** (>=2.0.0): Automatic type hint documentation
- **myst-parser** (>=3.0.0): Markdown support in Sphinx docs

## Build System

### hatchling (>=1.27.0)
- **Purpose**: Modern Python build backend
- **Why chosen**: PEP 517/518 compliant, simpler than setuptools, actively maintained

### hatch-vcs (>=0.4.0)
- **Purpose**: Automatic versioning from git tags
- **Why chosen**: Eliminates manual version bumping, single source of truth in git

## Platform Requirements

- **Python**: 3.10+ (for match statements and modern typing features)
- **macOS**: 10.14+ (required for PyXA compatibility)
- **Vexy Lines**: Desktop application must be installed and activated

## Removed Dependencies

The original `vexy-lines2pdf.py` script used **tenacity** for retry decorators, but the refactored version implements custom retry logic via `WindowWatcher` polling, making tenacity unnecessary and reducing dependencies.
