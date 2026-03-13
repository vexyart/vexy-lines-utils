#!/usr/bin/env python3
# this_file: src/vexy_lines_utils/core/plist.py

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

from loguru import logger

from vexy_lines_utils.core.errors import AutomationError

APP_DOMAIN = "com.vexy-art.lines"

FORMAT_CODES: dict[str, str] = {
    "pdf": "pdf",
    "svg": "svg",
}

EXPORT_PREFERENCES: dict[str, int] = {
    "export_strokes_mode": 0,
    "export\u00b7dlg\u00b7antialising": 1,
    "export\u00b7dlg\u00b7checkLayers": 0,
    "export\u00b7dlg\u00b7checkMergeColor": 0,
    "export\u00b7dlg\u00b7exportMode": 1,
    "export\u00b7dlg\u00b7imageFormat": 0,
    "export\u00b7dlg\u00b7radioColor": 0,
    "export\u00b7dlg\u00b7radioTransparent": 1,
    "export\u00b7dlg\u00b7scale": 1,
    "not_show_intro": 1,
    "not_show_wizard": 1,
}

_TYPE_FLAGS: dict[type, str] = {
    int: "-integer",
    str: "-string",
}


def _defaults(*args: str, input: bytes | None = None) -> subprocess.CompletedProcess[bytes]:  # noqa: A002
    """Run `defaults` with the given arguments."""
    return subprocess.run(  # noqa: S603
        ["defaults", *args],  # noqa: S607
        capture_output=True,
        input=input,
        timeout=10,
        check=False,
    )


class PlistManager:
    """Context manager that writes export preferences via `defaults` and restores them on exit.

    Uses macOS `defaults` CLI to read/write the app preferences domain without
    requiring any third-party Python packages.
    """

    def __init__(self, fmt: str, app_name: str = "Vexy Lines") -> None:
        self.fmt = fmt
        self.app_name = app_name
        self._snapshot: bytes | None = None

    def __enter__(self) -> Self:
        self._quit_app()
        self._snapshot = self._export_domain()
        self._apply_export_prefs()
        return self

    def __exit__(self, *exc_info: object) -> None:
        try:
            self._restore_originals()
        except Exception:
            logger.warning("Failed to restore preferences — manual cleanup may be needed")

    def _quit_app(self) -> None:
        script = f'tell application "{self.app_name}" to quit'
        try:
            subprocess.run(  # noqa: S603
                ["osascript", "-e", script],  # noqa: S607
                capture_output=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout quitting {self.app_name} (may not be running)")

    def _export_domain(self) -> bytes | None:
        result = _defaults("export", APP_DOMAIN, "-")
        if result.returncode != 0:
            logger.debug(f"Domain {APP_DOMAIN!r} not yet in defaults (will be created)")
            return None
        return result.stdout

    def _apply_export_prefs(self) -> None:
        prefs: dict[str, int | str] = dict(EXPORT_PREFERENCES)
        prefs["export\u00b7dlg\u00b7format"] = FORMAT_CODES.get(self.fmt, self.fmt)
        for key, value in prefs.items():
            self._write_one(key, value)
        logger.debug(f"Applied export preferences for format={self.fmt!r}")

    def _write_one(self, key: str, value: int | str) -> None:
        type_flag = _TYPE_FLAGS.get(type(value))
        if type_flag is None:
            msg = f"Unsupported pref type {type(value).__name__!r} for key {key!r}"
            raise AutomationError(msg, "PLIST_ERROR")
        result = _defaults("write", APP_DOMAIN, key, type_flag, str(value))
        if result.returncode != 0:
            msg = f"defaults write failed for {key!r}: {result.stderr.decode()}"
            raise AutomationError(msg, "PLIST_ERROR")

    def _restore_originals(self) -> None:
        if self._snapshot is None:
            # Domain didn't exist before — delete it entirely
            _defaults("delete", APP_DOMAIN)
            logger.debug(f"Deleted {APP_DOMAIN!r} (did not exist before export)")
        else:
            result = _defaults("import", APP_DOMAIN, "-", input=self._snapshot)
            if result.returncode != 0:
                logger.warning(f"defaults import failed: {result.stderr.decode()}")
            logger.debug("Restored original plist values")
