# QWEN.md

This repository uses `AGENTS.md` as the canonical agent guide. Read that file before editing.

Current summary: `vexy-lines-utils` is a Python 3.11+ package for parsing `.lines` files, extracting embedded images, applying/interpolating Vexy Lines styles, controlling the app through MCP, running a CustomTkinter GUI, and batch-exporting PDF/SVG on macOS through plist injection and AppleScript.

Use `uvx hatch test` for the default verification pass. Keep generated artifacts (`dist/`, caches, `__pycache__/`, generated version files) out of commits.
