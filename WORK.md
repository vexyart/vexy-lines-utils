---
this_file: WORK.md
---

# Work Progress — v2.0.0 Dialog-less Export Rewrite

## Completed

### Phase 1 — Structural cleanup
- Deleted `automation/ui_actions.py`, `strategies/`, `exporters/` directories
- Removed `mac-pyxa`, `pyautogui-ng`, `pyperclip` from `pyproject.toml`

### Phase 2 — Core contract rewrite
- `core/config.py`: New `ExportConfig` dataclass with format/timeout/retry validation
- `core/plist.py`: New `PlistManager` context manager with `_MISSING` sentinel and atomic writes
- `core/errors.py`: Added `PLIST_ERROR` suggestion

### Phase 3 — Automation simplification
- `automation/bridges.py`: Replaced `PyXABridge` with enhanced `AppleScriptBridge` (quit, is_running, open_file, close_front_window)
- `automation/window_watcher.py`: Removed `wait_for_patterns`, updated error codes to `WINDOW_TIMEOUT`/`APP_NOT_FOUND`

### Phase 4 — File utilities and exporter
- `utils/file_utils.py`: Added `validate_svg`, `validate_export`, `expected_export_path`, `resolve_output_path`
- `exporter.py`: New `VexyLinesExporter(config, dry_run)` with file-polling export detection

### Phase 5 — CLI and init files
- `__main__.py`: New CLI — `export(input, *, output, format, verbose, dry_run, say_summary, timeout_multiplier, max_retries)`
- All `__init__.py` files updated

### Phase 6 — Tests
- Rewrote `tests/test_package.py` — 79 tests, all passing in 1.15s

### Phase 7 — Documentation
- `CHANGELOG.md` updated with v2.0.0 entry
- `WORK.md` rewritten
- `TODO.md` updated
- `DEPENDENCIES.md` updated

## Test Results

```
79 passed in 1.15s
```

## Session 2 — Ruff cleanup (2026-03-13)

### Fixed

- `FORMAT_CODES` in `core/plist.py`: was `{pdf: 0, svg: 1}` → `{pdf: "pdf", svg: "svg"}` (plist stores strings)
- `MIN_RETRIES` in `core/config.py`: `1` → `0` so `--max_retries 0` is valid
- CLI validation in `__main__.py`: `< 1` → `< 0`
- `PlistManager.__enter__` return type: `PlistManager` → `Self`
- `plist.py`: dropped `import os`, used `Path.replace`/`Path.unlink`
- `bridges.py`: `# noqa: S603/S607` on correct lines
- `tests/test_package.py`: fixed PT012, ARG001, SIM117, S108 (all `/tmp` paths), RUF100

### Test Results

```
79 passed in ~1.2s — ruff 0 errors
```

## Next Steps

- Monitor real-world usage with the new plist-driven export
- Consider adding `--output-dir` shorthand

