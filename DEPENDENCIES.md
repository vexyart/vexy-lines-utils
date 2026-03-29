---
this_file: DEPENDENCIES.md
---

# Dependencies

## Runtime Dependencies

### fire (>=0.6.0)
- **Purpose**: Command-line interface framework
- **Why chosen**: Automatically generates CLIs from Python objects with no argparse boilerplate
- **Usage**: Powers `vexy-lines export` command and all argument parsing

### loguru (>=0.7.2)
- **Purpose**: Structured logging with automatic colors
- **Why chosen**: Zero-config logger; cleaner than stdlib logging for CLI tools
- **Usage**: All status messages, progress tracking, error reporting, verbose mode

## Development Dependencies

### Testing
- **pytest** (>=8.3.4): Test framework
- **pytest-mock** (>=3.0.0): Mock fixtures for subprocess and filesystem
- **pytest-xdist** (>=3.6.1): Parallel test execution
- **pytest-rerunfailures** (>=14.0): Flaky test retry

### Code Quality
- **ruff**: All-in-one linter/formatter

## Build System

### hatchling
- **Purpose**: Modern PEP 517/518 build backend
- **Why chosen**: Simpler than setuptools, actively maintained

### hatch-vcs
- **Purpose**: Automatic versioning from git tags
- **Why chosen**: Single source of truth — no manual version bumping

## Platform Requirements

- **Python**: 3.10+
- **macOS**: required (plist files, AppleScript, `osascript`, `open -a`)
- **Vexy Lines**: Desktop application must be installed

## Removed Dependencies (v2.0.0)

- **mac-pyxa**: Replaced by pure AppleScript subprocess calls via `osascript`
- **pyautogui-ng**: No longer needed — export triggered via plist preferences, not GUI dialogs
- **pyperclip**: No longer needed — clipboard paste into save dialog eliminated

## MCP Client (v3.0)

The MCP client module (`vexy_lines_utils.mcp`) uses only Python standard library:
- `socket` — TCP connection to the embedded MCP server
- `json` — JSON-RPC 2.0 message serialization

No additional runtime dependencies were added.

## .lines Parser & Style Engine (v4.0)

The parser (`vexy_lines_utils.parser`) and style engine (`vexy_lines_utils.style`) use only Python standard library:
- `xml.etree.ElementTree` — XML parsing of .lines files
- `base64`, `zlib`, `struct` — decoding embedded source/preview images
- `dataclasses` — typed result structures
- `copy` — deep-copying styles for interpolation

No additional runtime dependencies were added.

## Optional: Image Extraction [images]

- **Pillow** (>=10.0.0): Image format conversion when extracting source/preview from .lines files

## Optional: Video Processing [video]

- **av** (>=12.0.0): PyAV for video frame extraction and assembly
- **resvg-py** (>=0.2.0): Fast SVG-to-PNG rasterisation
- **Pillow** (>=10.0.0): Image format bridging
- **svglab** (>=0.1.0): SVG parsing with native mm dimension handling

## Optional: GUI [gui]

- **customtkinter** (>=5.2.0): Modern themed tkinter widgets
- **tkinterdnd2** (>=0.4.0): Drag-and-drop file support
- **CTkMenuBarPlus** (>=0.1.0): Menu bar widget for customtkinter
- **Pillow** (>=10.0.0): Image preview display
- **opencv-python** (>=4.8.0): Video frame extraction for GUI previews
