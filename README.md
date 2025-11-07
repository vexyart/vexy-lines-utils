---
this_file: README.md
---

# Vexy Lines Utils

Export Vexy Lines `.lines` documents to crisp PDFs without pointing and clicking. This package provides a command-line interface for batch automation of [Vexy Lines](https://www.vexy.art) on macOS, wrapping the exact workflow described in the original `vexy-lines2pdf.py` script with a Fire-powered CLI.

## About Vexy Lines

Vexy Lines is a creative desktop application that transforms photos, illustrations, AI-generated images and other bitmaps into expressive vector art. It reads the color value of every pixel and intelligently builds vector artwork from it.

### Core Concept

Feed it a portrait, get back an engraving. Drop in a landscape, receive flowing wave patterns. The software offers twelve different ways to interpret your images, each method responding to the light and dark areas of your source image differently. Dark areas generate thick strokes, bright areas create thin ones—or reverse it for dramatic effects.

### The 12 Fill Algorithms

- **Linear**: Classic copper-plate engravings with parallel straight lines
- **Wave**: Flowing parallel curves that undulate across your image
- **Radial**: Lines exploding from a center point like sun rays
- **Circular**: Concentric rings emanating outward
- **Spiral**: Continuous winding patterns from center to edge
- **Halftone**: Newspaper-style dots that scale with brightness
- **Trace**: Clean edge detection that converts boundaries to paths
- **Wireframe**: 3D-looking dimensional lattices
- **Scribble**: Hand-drawn energy with organic randomness
- **Fractal**: Intricate mathematical recursive patterns
- **Text**: Paint with letters and typography
- **Handmade**: Draw your own custom strokes for full control

### Professional Features

- **Layer System**: Stack multiple fills, organize with groups, control visibility with masks
- **Dynamic Color**: Strokes pull actual colors from source images segment by segment
- **3D Mesh Warping**: Wrap patterns around cylinders, drape over waves, add perspective
- **Multiple Sources**: Each group can reference different images for complex compositions
- **Production Export**: SVG, PDF, EPS for infinite scaling; PNG, JPEG for quick sharing
- **Overlap Control**: Fills can cut through each other creating woven effects

Files save as `.lines` projects that preserve every layer, fill, mask, mesh, and parameter—allowing iterative refinement.

## What This Package Provides

This automation tool helps power users and studios process large batches of Vexy Lines artwork efficiently:

- **Fire CLI**: A `vexy-lines` command implemented with Google's `fire` framework for intuitive command-line usage
- **Batch Processing**: Recursive discovery and processing of `.lines` files in folders or single-file operations
- **macOS Automation**: PyXA-powered menu control for **File → Export…** and **File → Close** operations
- **Smart Dialog Navigation**: `pyautogui-ng` keyboard automation to navigate save dialogs and set proper filenames
- **Voice Feedback**: Optional macOS text-to-speech announcements for accessibility
- **Dry-Run Mode**: Preview operations without touching the UI—perfect for CI tests or validating large batches
- **Robust Error Handling**: Continues processing remaining files even if individual exports fail

## System Requirements

- **macOS 10.14+** (required for PyXA automation framework)
- **Vexy Lines** desktop application installed
- **Python 3.10+**
- **4GB RAM** minimum (same as Vexy Lines)

## Installation

### From PyPI (Recommended)

```bash
pip install vexy-lines-utils
```

### From Source

```bash
git clone https://github.com/vexyart/vexy-lines-utils.git
cd vexy-lines-utils
pip install -e .
```

### Required Permissions

Grant accessibility permissions to your Terminal/IDE for UI automation:
1. Open **System Preferences** → **Security & Privacy**
2. Navigate to **Privacy** → **Accessibility**
3. Add your Terminal app or IDE
4. Restart Terminal/IDE after granting permissions

## Usage Examples

### Basic Export Operations

```bash
# Export a single document
vexy-lines export ~/Art/portrait.lines

# Export everything in a folder (recursive)
vexy-lines export ~/Projects/posters

# Process specific project with verbose output
vexy-lines export ~/Clients/BigCorp/logos --verbose

# Preview what would be processed without running
vexy-lines export ~/batch --dry_run --verbose

# Get voice confirmation when batch completes
vexy-lines export ~/batch --say_summary
```

### Advanced Workflows

```bash
# Process today's work
vexy-lines export ~/Desktop/vexy-today/ --verbose --say_summary

# Validate large batch before running
vexy-lines export ~/Archive/2024 --dry_run | grep "processed"

# Export with detailed logging for troubleshooting
vexy-lines export ~/problem-files/ --verbose 2>&1 | tee export.log
```

### Command-Line Arguments

**Required:**
- `target`: Path to a `.lines` file or folder containing them (searched recursively)

**Optional Flags:**
- `--verbose`: Show detailed progress including each file being processed
- `--dry_run`: Preview files that would be processed without UI automation
- `--say_summary`: Announce completion summary via macOS text-to-speech

### Output Format

The command returns a structured dictionary with export statistics:

```json
{
  "processed": 10,
  "success": 9,
  "failed": 1,
  "failures": [
    ["path/to/broken.lines", "Failed to open file"]
  ],
  "dry_run": false
}
```

## How It Works

1. **Discovery** – `find_lines_files` resolves the target path, supports single files, and sorts recursive directory walks for deterministic runs.
2. **App bridge** – `PyXABridge` launches/activates Vexy Lines via macOS scripting bridges and exposes a minimal interface (`window_titles`, `click_menu_item`).
3. **Window watching** – `WindowWatcher` polls the live window list so we wait for the expected document title, the Export dialog, and the Save dialog instead of relying on coarse `sleep()` delays.
4. **Keyboard automation** – `UIActions` wraps `pyautogui-ng` + `pyperclip` to press Command-Shift-G, paste the folder path, select the filename, and confirm overwrites.
5. **Verification** – the exporter waits for the Save window to close, then checks that the new PDF exists and is non-empty before moving on.

If any step fails (missing dialog, file cannot open, permissions issue, etc.), the run continues with the next `.lines` document and reports the failure reason in the final summary.

## Python API

For integration into larger workflows:

```python
from pathlib import Path
from vexy_lines_utils import VexyLinesExporter, AutomationConfig

# Create custom configuration
config = AutomationConfig(
    poll_interval=0.2,        # Window check frequency (seconds)
    wait_for_app=20.0,        # App launch timeout
    wait_for_file=20.0,       # File open timeout
    wait_for_dialog=25.0,     # Dialog appearance timeout
    post_action_delay=0.4     # Pause after UI actions
)

# Initialize exporter
exporter = VexyLinesExporter(config=config)

# Process files
stats = exporter.export(Path("~/Documents/vexy-projects"))

# Check results
print(f"Success rate: {stats.success}/{stats.processed}")
for path, reason in stats.failures:
    print(f"Failed: {path} - {reason}")
```

## Development

### Project Structure

```
vexy-lines-utils/
├── src/vexy_lines_utils/
│   ├── __init__.py           # Package exports
│   ├── vexy_lines_utils.py   # Main implementation
│   └── py.typed               # PEP 561 type marker
├── tests/
│   ├── test_package.py       # Unit tests
│   └── fixtures/              # Test data
├── pyproject.toml             # Package configuration
└── README.md                  # This file
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/vexyart/vexy-lines-utils.git
cd vexy-lines-utils

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev,test]"

# Run tests
uvx hatch test

# Format code
uvx hatch fmt

# Type checking
uvx hatch run lint:typing
```

### Testing Philosophy

Tests focus on the automation logic rather than UI interaction:
- Discovery logic for finding `.lines` files
- Stats tracking and error reporting
- Window watching state machines
- Dry-run mode for CI environments

### Contributing

When adding features:
1. Keep scope focused on `.lines` → PDF export automation
2. Add unit tests for new functionality
3. Update this README with new options
4. Follow existing code style (Ruff-formatted)

## Troubleshooting

### Common Issues

**"PyXA is not available"**
- Ensure you're on macOS
- Install with: `pip install mac-pyxa`
- Check Python architecture matches system

**"Failed to launch Vexy Lines"**
- Verify Vexy Lines.app is in /Applications
- Try launching manually first
- Check for trial/license expiration

**Export dialogs timing out**
- Increase timeout values in AutomationConfig
- Check if Vexy Lines has modal dialogs open
- Verify no system dialogs blocking

**"Accessibility permissions required"**
- Grant Terminal.app accessibility permissions
- If using VS Code/PyCharm, grant IDE permissions too
- Log out and back in after permission changes

**PDFs not appearing**
- Check source `.lines` files aren't corrupted
- Verify write permissions in target directory
- Look for hidden error dialogs in Vexy Lines

## About

**vexy-lines-utils** is developed by [FontLab Ltd.](https://www.fontlab.com), creators of Vexy Lines and industry-standard font editing software.

### Links

- [Vexy Lines Homepage](https://www.vexy.art)
- [Vexy Lines Documentation](https://help.vexy.art)
- [FontLab Support](https://support.vexy.art)
- [Package Issues](https://github.com/vexyart/vexy-lines-utils/issues)

### License

MIT License - see [LICENSE](LICENSE) file for details.

### Credits

Based on the original `vexy-lines2pdf.py` automation script. The package structure follows modern Python packaging standards with Fire CLI, comprehensive testing, and robust error handling.
